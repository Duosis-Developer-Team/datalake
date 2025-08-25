import requests
import statistics
import time
import json 

#################################################################
# Konfigürasyon dosyasını oku
json_file_path = "/Datalake_Project/configuration_file.json"
with open(json_file_path, "r") as file:
    config = json.load(file)

# Nutanix Prism API erişim bilgileri
nutanix_config = config["Nutanix"]

# PRISM_IP değeri birden fazla IP içerebileceği için virgül ile ayrılmış string'i listeye dönüştürüyoruz.
prism_ip_string = nutanix_config['PRISM_IP']
if prism_ip_string:
    prism_ips = [ip.strip() for ip in prism_ip_string.split(",") if ip.strip()]
else:
    prism_ips = []

USERNAME = nutanix_config["USERNAME"]
PASSWORD = nutanix_config["PASSWORD"]

# SSL Sertifika uyarısını atlamak için
requests.packages.urllib3.disable_warnings()

# Headers
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Kimlik doğrulama
AUTH = (USERNAME, PASSWORD)

def fetch_clusters(base_url):
    """Cluster verilerini almak için clusters endpoint'ine gider."""
    response = requests.get(f"{base_url}/clusters/", headers=HEADERS, auth=AUTH, verify=False)
    response.raise_for_status()
    clusters = response.json()["entities"]

    cluster_data = []
    for cluster in clusters:
        datacenter_name = cluster["name"].split("-")[0]
        cluster_name = cluster["name"]
        cluster_uuid = cluster["uuid"]
        num_nodes = cluster["num_nodes"]
        cluster_data.append({
            "datacenter_name": datacenter_name,
            "cluster_name": cluster_name,
            "cluster_uuid": cluster_uuid,
            "num_nodes": num_nodes
        })

    return cluster_data

def fetch_hosts(base_url, cluster_uuid):
    """Cluster UUID ile host bilgilerini alır."""
    response = requests.get(f"{base_url}/hosts/", headers=HEADERS, auth=AUTH, verify=False)
    response.raise_for_status()
    return response.json()["entities"]

def fetch_host_stats(base_url, host_uuid, memory_capacity, cpu_capacity):
    """Belirli bir host için historical stats verilerini alır."""
    end_time = int(time.time() * 1e6)  # Şu anki zaman (mikroseconds)
    start_time = end_time - (15 * 60 * 1e6)  # 15 dakika önce

    # Metrics'i gruplara ayırıyoruz (API 5'ten fazla metrik kabul etmiyor)
    metrics_groups = [
        [
            "hypervisor_memory_usage_ppm",
            "hypervisor_cpu_usage_ppm",
            "hypervisor_num_transmitted_bytes",
            "hypervisor_num_received_bytes"
        ],
        [
            "hypervisor_read_io_bandwidth_kBps",
            "hypervisor_write_io_bandwidth_kBps",
            "storage.usage_bytes",
            "storage.capacity_bytes"
        ]
    ]

    results = {}
    for metrics in metrics_groups:
        metrics_query = "&".join([f"metrics={metric}" for metric in metrics])
        stats_url = f"{base_url}/hosts/{host_uuid}/stats/?{metrics_query}&start_time_in_usecs={int(start_time)}&interval_in_secs=60"

        response = requests.get(stats_url, headers=HEADERS, auth=AUTH, verify=False)
        response.raise_for_status()
        stats_data = response.json()["stats_specific_responses"]

        for stat in stats_data:
            if stat["successful"]:
                metric = stat["metric"]
                values = stat["values"]
                # PPM değerlerini toplam kapasiteye göre dönüştür
                if metric == "hypervisor_memory_usage_ppm":
                    converted_values = [(value / 1)  for value in values]
                elif metric == "hypervisor_cpu_usage_ppm":
                    converted_values = [(value / 1 ) for value in values]
                else:
                    converted_values = values  # Dönüştürme gerekmeyen değerler

                results[metric] = {
                    "min": min(converted_values),
                    "max": max(converted_values),
                    "avg": statistics.mean(converted_values)
                }
            else:
                results[stat["metric"]] = {
                    "min": None,
                    "max": None,
                    "avg": None,
                    "error": stat["message"]
                }

    return results

def generate_insert_queries(data):
    """Veriyi INSERT sorgusu şeklinde hazırlar."""
    insert_queries = []
    for cluster_data in data:
        query = f"""
        INSERT INTO nutanix_cluster_metrics (
            datacenter_name,
            cluster_name,
            cluster_uuid,
            num_nodes,
            total_memory_capacity,
            total_cpu_capacity,
            total_vms,
            network_transmitted_avg,
            network_received_avg,
            storage_capacity,
            storage_usage,
            memory_usage_min,
            memory_usage_max,
            memory_usage_avg,
            cpu_usage_min,
            cpu_usage_max,
            cpu_usage_avg,
            read_io_bandwidth_min,
            read_io_bandwidth_max,
            read_io_bandwidth_avg,
            write_io_bandwidth_min,
            write_io_bandwidth_max,
            write_io_bandwidth_avg
        ) VALUES (
            '{cluster_data["datacenter_name"]}',
            '{cluster_data["cluster_name"]}',
            '{cluster_data["cluster_uuid"]}',
            {cluster_data["num_nodes"]},
            {cluster_data["total_memory_capacity"]},
            {cluster_data["total_cpu_capacity"]},
            {cluster_data["total_vms"]},
            {cluster_data["network_transmitted_avg"] if cluster_data["network_transmitted_avg"] is not None else 'NULL'},
            {cluster_data["network_received_avg"] if cluster_data["network_received_avg"] is not None else 'NULL'},
            {cluster_data["storage_capacity"] if cluster_data["storage_capacity"] is not None else 'NULL'},
            {cluster_data["storage_usage"] if cluster_data["storage_usage"] is not None else 'NULL'},
            {cluster_data["memory_usage_min"] if cluster_data["memory_usage_min"] is not None else 'NULL'},
            {cluster_data["memory_usage_max"] if cluster_data["memory_usage_max"] is not None else 'NULL'},
            {cluster_data["memory_usage_avg"] if cluster_data["memory_usage_avg"] is not None else 'NULL'},
            {cluster_data["cpu_usage_min"] if cluster_data["cpu_usage_min"] is not None else 'NULL'},
            {cluster_data["cpu_usage_max"] if cluster_data["cpu_usage_max"] is not None else 'NULL'},
            {cluster_data["cpu_usage_avg"] if cluster_data["cpu_usage_avg"] is not None else 'NULL'},
            {cluster_data["read_io_bandwidth_min"] if cluster_data["read_io_bandwidth_min"] is not None else 'NULL'},
            {cluster_data["read_io_bandwidth_max"] if cluster_data["read_io_bandwidth_max"] is not None else 'NULL'},
            {cluster_data["read_io_bandwidth_avg"] if cluster_data["read_io_bandwidth_avg"] is not None else 'NULL'},
            {cluster_data["write_io_bandwidth_min"] if cluster_data["write_io_bandwidth_min"] is not None else 'NULL'},
            {cluster_data["write_io_bandwidth_max"] if cluster_data["write_io_bandwidth_max"] is not None else 'NULL'},
            {cluster_data["write_io_bandwidth_avg"] if cluster_data["write_io_bandwidth_avg"] is not None else 'NULL'}
        );
        """
        insert_queries.append(query.strip())

    return insert_queries

def main():
    all_data = []
    # Konfigürasyonda tanımlı her bir PRISM_IP için döngü kuruyoruz.
    for prism_ip in prism_ips:
        # Her PRISM_IP için BASE_URL dinamik olarak oluşturuluyor.
        base_url = f"https://{prism_ip}:9440/PrismGateway/services/rest/v2.0"

        # Tüm cluster bilgilerini çek
        clusters = fetch_clusters(base_url)

        for cluster in clusters:
            cluster_uuid = cluster["cluster_uuid"]

            # Host bilgilerini çek
            hosts = fetch_hosts(base_url, cluster_uuid)

            cluster_memory_capacity = 0
            cluster_cpu_capacity = 0
            cluster_num_vms = 0
            cluster_storage_capacity = 0
            cluster_storage_usage = 0
            network_transmitted = []
            network_received = []
            memory_usage = []
            cpu_usage = []
            read_io_bandwidth = []
            write_io_bandwidth = []

            for host in hosts:
                host_stats = fetch_host_stats(
                    base_url,
                    host["uuid"],
                    host["memory_capacity_in_bytes"],
                    host["cpu_capacity_in_hz"]
                )

                cluster_memory_capacity += host["memory_capacity_in_bytes"]
                cluster_cpu_capacity += host["cpu_capacity_in_hz"]
                cluster_num_vms += host["num_vms"]

                if "hypervisor_num_transmitted_bytes" in host_stats:
                    avg_transmitted = host_stats["hypervisor_num_transmitted_bytes"]["avg"]
                    if avg_transmitted is not None:
                        network_transmitted.append(avg_transmitted)
                if "hypervisor_num_received_bytes" in host_stats:
                    avg_received = host_stats["hypervisor_num_received_bytes"]["avg"]
                    if avg_received is not None:
                        network_received.append(avg_received)

                if "hypervisor_memory_usage_ppm" in host_stats:
                    memory_usage.append(host_stats["hypervisor_memory_usage_ppm"]["avg"])
                if "hypervisor_cpu_usage_ppm" in host_stats:
                    cpu_usage.append(host_stats["hypervisor_cpu_usage_ppm"]["avg"])

                if "hypervisor_read_io_bandwidth_kBps" in host_stats:
                    read_io_bandwidth.append(host_stats["hypervisor_read_io_bandwidth_kBps"]["avg"])
                if "hypervisor_write_io_bandwidth_kBps" in host_stats:
                    write_io_bandwidth.append(host_stats["hypervisor_write_io_bandwidth_kBps"]["avg"])

                cluster_storage_capacity += int(host["usage_stats"]["storage.capacity_bytes"])
                cluster_storage_usage += int(host["usage_stats"]["storage.usage_bytes"])

            cluster_data = {
                "datacenter_name": cluster["datacenter_name"],
                "cluster_name": cluster["cluster_name"],
                "cluster_uuid": cluster_uuid,
                "num_nodes": cluster["num_nodes"],
                "total_memory_capacity": cluster_memory_capacity,
                "total_cpu_capacity": cluster_cpu_capacity,
                "total_vms": cluster_num_vms,
                "network_transmitted_avg": statistics.mean(network_transmitted) if network_transmitted else None,
                "network_received_avg": statistics.mean(network_received) if network_received else None,
                "storage_capacity": cluster_storage_capacity,
                "storage_usage": cluster_storage_usage,
                "memory_usage_min": min(memory_usage) if memory_usage else None,
                "memory_usage_max": max(memory_usage) if memory_usage else None,
                "memory_usage_avg": statistics.mean(memory_usage) if memory_usage else None,
                "cpu_usage_min": min(cpu_usage) if cpu_usage else None,
                "cpu_usage_max": max(cpu_usage) if cpu_usage else None,
                "cpu_usage_avg": statistics.mean(cpu_usage) if cpu_usage else None,
                "read_io_bandwidth_min": min([v for v in read_io_bandwidth if v is not None]) if read_io_bandwidth and any(v is not None for v in read_io_bandwidth) else None,
                "read_io_bandwidth_max": max([v for v in read_io_bandwidth if v is not None]) if read_io_bandwidth and any(v is not None for v in read_io_bandwidth) else None,
                "read_io_bandwidth_avg": statistics.mean([v for v in read_io_bandwidth if v is not None]) if read_io_bandwidth and any(v is not None for v in read_io_bandwidth) else None,
                "write_io_bandwidth_min": min([v for v in write_io_bandwidth if v is not None]) if write_io_bandwidth and any(v is not None for v in write_io_bandwidth) else None,
                "write_io_bandwidth_max": max([v for v in write_io_bandwidth if v is not None]) if write_io_bandwidth and any(v is not None for v in write_io_bandwidth) else None,
                "write_io_bandwidth_avg": statistics.mean([v for v in write_io_bandwidth if v is not None]) if write_io_bandwidth and any(v is not None for v in write_io_bandwidth) else None,
                "prism_ip": prism_ip
            }
            all_data.append(cluster_data)

    # INSERT sorgularını oluştur ve yazdır
    insert_queries = generate_insert_queries(all_data)
    for query in insert_queries:
        print(query)

if __name__ == "__main__":
    main()
