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

# PRISM_IP değeri birden fazla IP içerebileceği için virgül ile ayrılmış string'i listeye dönüştür
prism_ip_string = nutanix_config['PRISM_IP']
if prism_ip_string:
    prism_ips = [ip.strip() for ip in prism_ip_string.split(",") if ip.strip()]
else:
    prism_ips = []

USERNAME = nutanix_config["USERNAME"]
PASSWORD = nutanix_config["PASSWORD"]

###############################################################
# SSL Sertifika uyarısını atlamak için
requests.packages.urllib3.disable_warnings()

# Headers
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Kimlik doğrulama
AUTH = (USERNAME, PASSWORD)

def fetch_hosts(base_url):
    """Host bilgilerini almak için hosts endpoint'ine gider."""
    response = requests.get(f"{base_url}/hosts/", headers=HEADERS, auth=AUTH, verify=False)
    response.raise_for_status()
    return response.json()["entities"]

def fetch_host_stats(base_url, host_uuid, memory_capacity, cpu_capacity):
    """Belirli bir host için historical stats verilerini alır."""
    end_time = int(time.time() * 1e6)  # Şu anki zaman (mikroseconds)
    start_time = end_time - (15 * 60 * 1e6)  # 15 dakika önce

    metrics_groups = [
        [
            "hypervisor_memory_usage_ppm",
            "hypervisor_cpu_usage_ppm",
            "hypervisor_num_transmitted_bytes",
            "hypervisor_num_received_bytes"
        ],
        [
            "read_io_bandwidth_kBps",
            "write_io_bandwidth_kBps"
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
                if "ppm" in metric:
                    # PPM değerlerini kapasiteye göre dönüştürme (örneğin, bellek için)
                    converted_values = [(value / 1e6) * memory_capacity if "memory" in metric else (value / 1e6) * cpu_capacity for value in values]
                    results[metric] = {
                        "min": min(converted_values),
                        "max": max(converted_values),
                        "avg": statistics.mean(converted_values)
                    }
                else:
                    results[metric] = {
                        "min": min(values),
                        "max": max(values),
                        "avg": statistics.mean(values)
                    }
            else:
                results[stat["metric"]] = {
                    "min": None,
                    "max": None,
                    "avg": None,
                    "error": stat["message"]
                }

    return results

def generate_insert_query(data):
    """Tüm veriler için tek bir INSERT sorgusu hazırlar."""
    values = []
    for host_data in data:
        values.append(f"('{host_data['host_name']}', "
                      f"'{host_data['host_uuid']}', "
                      f"'{host_data['cluster_uuid']}', "
                      f"{host_data['total_memory_capacity']}, "
                      f"{host_data['total_cpu_capacity']}, "
                      f"{host_data['num_cpu_cores']}, "
                      f"{host_data['total_vms']}, "
                      f"{host_data['boottime']}, "
                      f"{host_data['network_transmitted_avg'] if host_data['network_transmitted_avg'] is not None else 'NULL'}, "
                      f"{host_data['network_received_avg'] if host_data['network_received_avg'] is not None else 'NULL'}, "
                      f"{host_data['memory_usage_min'] if host_data['memory_usage_min'] is not None else 'NULL'}, "
                      f"{host_data['memory_usage_max'] if host_data['memory_usage_max'] is not None else 'NULL'}, "
                      f"{host_data['memory_usage_avg'] if host_data['memory_usage_avg'] is not None else 'NULL'}, "
                      f"{host_data['cpu_usage_min'] if host_data['cpu_usage_min'] is not None else 'NULL'}, "
                      f"{host_data['cpu_usage_max'] if host_data['cpu_usage_max'] is not None else 'NULL'}, "
                      f"{host_data['cpu_usage_avg'] if host_data['cpu_usage_avg'] is not None else 'NULL'}, "
                      f"{host_data['storage_capacity']}, "
                      f"{host_data['storage_usage']}, "
                      f"{host_data['read_io_bandwidth_min'] if host_data['read_io_bandwidth_min'] is not None else 'NULL'}, "
                      f"{host_data['read_io_bandwidth_max'] if host_data['read_io_bandwidth_max'] is not None else 'NULL'}, "
                      f"{host_data['read_io_bandwidth_avg'] if host_data['read_io_bandwidth_avg'] is not None else 'NULL'}, "
                      f"{host_data['write_io_bandwidth_min'] if host_data['write_io_bandwidth_min'] is not None else 'NULL'}, "
                      f"{host_data['write_io_bandwidth_max'] if host_data['write_io_bandwidth_max'] is not None else 'NULL'}, "
                      f"{host_data['write_io_bandwidth_avg'] if host_data['write_io_bandwidth_avg'] is not None else 'NULL'})")
    query = f"""
    INSERT INTO nutanix_host_metrics (
        host_name, host_uuid, cluster_uuid, total_memory_capacity, total_cpu_capacity, 
        num_cpu_cores, total_vms, boottime, network_transmitted_avg, network_received_avg, 
        memory_usage_min, memory_usage_max, memory_usage_avg, cpu_usage_min, 
        cpu_usage_max, cpu_usage_avg, storage_capacity, storage_usage, 
        read_io_bandwidth_min, read_io_bandwidth_max, read_io_bandwidth_avg, 
        write_io_bandwidth_min, write_io_bandwidth_max, write_io_bandwidth_avg
    ) VALUES {", ".join(values)};
    """
    return query.strip()

def main():
    all_data = []
    # Her bir PRISM_IP için döngü kuruyoruz
    for prism_ip in prism_ips:
        base_url = f"https://{prism_ip}:9440/PrismGateway/services/rest/v2.0"
        hosts = fetch_hosts(base_url)

        for host in hosts:
            host_stats = fetch_host_stats(
                base_url,
                host["uuid"],
                host["memory_capacity_in_bytes"],
                host["cpu_capacity_in_hz"]
            )

            host_data = {
                "host_name": host["name"],
                "host_uuid": host["uuid"],
                "cluster_uuid": host["cluster_uuid"],
                "total_memory_capacity": host["memory_capacity_in_bytes"],
                "total_cpu_capacity": host["cpu_capacity_in_hz"],
                "num_cpu_cores": host["num_cpu_cores"],
                "total_vms": host["num_vms"],
                "boottime": host["boot_time_in_usecs"],
                "network_transmitted_avg": host_stats.get("hypervisor_num_transmitted_bytes", {}).get("avg"),
                "network_received_avg": host_stats.get("hypervisor_num_received_bytes", {}).get("avg"),
                "memory_usage_min": host_stats.get("hypervisor_memory_usage_ppm", {}).get("min"),
                "memory_usage_max": host_stats.get("hypervisor_memory_usage_ppm", {}).get("max"),
                "memory_usage_avg": host_stats.get("hypervisor_memory_usage_ppm", {}).get("avg"),
                "cpu_usage_min": host_stats.get("hypervisor_cpu_usage_ppm", {}).get("min"),
                "cpu_usage_max": host_stats.get("hypervisor_cpu_usage_ppm", {}).get("max"),
                "cpu_usage_avg": host_stats.get("hypervisor_cpu_usage_ppm", {}).get("avg"),
                "storage_capacity": int(host["usage_stats"]["storage.capacity_bytes"]),
                "storage_usage": int(host["usage_stats"]["storage.usage_bytes"]),
                "read_io_bandwidth_min": host_stats.get("read_io_bandwidth_kBps", {}).get("min"),
                "read_io_bandwidth_max": host_stats.get("read_io_bandwidth_kBps", {}).get("max"),
                "read_io_bandwidth_avg": host_stats.get("read_io_bandwidth_kBps", {}).get("avg"),
                "write_io_bandwidth_min": host_stats.get("write_io_bandwidth_kBps", {}).get("min"),
                "write_io_bandwidth_max": host_stats.get("write_io_bandwidth_kBps", {}).get("max"),
                "write_io_bandwidth_avg": host_stats.get("write_io_bandwidth_kBps", {}).get("avg")
            }
            all_data.append(host_data)

    insert_query = generate_insert_query(all_data)
    print(insert_query)

if __name__ == "__main__":
    main()
