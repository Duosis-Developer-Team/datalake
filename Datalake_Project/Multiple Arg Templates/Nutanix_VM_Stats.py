import requests
import statistics
import time
from datetime import datetime
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

def fetch_vms(base_url):
    """VM verilerini almak için vms endpoint'ine gider."""
    all_vms = []
    page = 1
    while True:
        try:
            response = requests.get(f"{base_url}/vms/?count=500&page={page}", headers=HEADERS, auth=AUTH, verify=False)
            response.raise_for_status()
            vms = response.json().get("entities", [])
            if not vms:
                break
            all_vms.extend(vms)
            page += 1
        except requests.exceptions.RequestException as e:
            print(f"Error fetching VMs: {e}")
            break
    return all_vms

def fetch_vm_stats(base_url, vm_uuid):
    """Belirli bir VM için historical stats verilerini alır."""
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
            "hypervisor_read_io_bandwidth_kBps",
            "hypervisor_write_io_bandwidth_kBps"
        ]
    ]

    results = {}
    for metrics in metrics_groups:
        metrics_query = "&".join([f"metrics={metric}" for metric in metrics])
        stats_url = f"{base_url}/vms/{vm_uuid}/stats/?{metrics_query}&startTimeInUsecs={int(start_time)}&intervalInSecs=60"

        try:
            response = requests.get(stats_url, headers=HEADERS, auth=AUTH, verify=False)
            response.raise_for_status()
            response_json = response.json()

            if "statsSpecificResponses" not in response_json:
                continue

            stats_data = response_json["statsSpecificResponses"]
            for stat in stats_data:
                if stat["successful"]:
                    metric = stat["metric"]
                    values = stat["values"]
                    results[metric] = {
                        "min": min(values),
                        "max": max(values),
                        "avg": statistics.mean(values)
                    }
                else:
                    results[stat["metric"]] = {
                        "min": None,
                        "max": None,
                        "avg": None
                    }

        except requests.exceptions.RequestException as e:
            print(f"Error fetching stats for VM {vm_uuid}: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    return results

def calculate_storage_usage(vm):
    """VM için storage usage hesaplama."""
    ssd_usage = int(vm.get("stats", {}).get("controller.storage_tier.ssd.usage_bytes", 0))
    das_sata_usage = int(vm.get("stats", {}).get("controller.storage_tier.das-sata.usage_bytes", 0))
    return ssd_usage + das_sata_usage

def format_value(value):
    """PostgreSQL uyumlu değer formatlama."""
    if value is None:
        return 'NULL'
    if isinstance(value, str):
        return "'{}'".format(value.replace("'", "''"))
    return str(value)

def generate_insert_query(data):
    """Tek bir INSERT sorgusu oluşturur."""
    values = []
    for vm_data in data:
        values.append(f"({format_value(vm_data['vm_name'])}, "
                      f"{format_value(vm_data['vm_uuid'])}, "
                      f"{format_value(vm_data['cluster_uuid'])}, "
                      f"{format_value(vm_data['host_name'])}, "
                      f"{format_value(vm_data['host_uuid'])}, "
                      f"{format_value(vm_data['power_state'])}, "
                      f"{format_value(vm_data['memory_capacity'])}, "
                      f"{format_value(vm_data['cpu_count'])}, "
                      f"{format_value(vm_data['disk_capacity'])}, "
                      f"{format_value(vm_data['hypervisor_read_io_bandwidth_min'])}, "
                      f"{format_value(vm_data['hypervisor_read_io_bandwidth_max'])}, "
                      f"{format_value(vm_data['hypervisor_read_io_bandwidth_avg'])}, "
                      f"{format_value(vm_data['hypervisor_write_io_bandwidth_min'])}, "
                      f"{format_value(vm_data['hypervisor_write_io_bandwidth_max'])}, "
                      f"{format_value(vm_data['hypervisor_write_io_bandwidth_avg'])}, "
                      f"{format_value(vm_data['cpu_usage_min'])}, "
                      f"{format_value(vm_data['cpu_usage_max'])}, "
                      f"{format_value(vm_data['cpu_usage_avg'])}, "
                      f"{format_value(vm_data['memory_usage_min'])}, "
                      f"{format_value(vm_data['memory_usage_max'])}, "
                      f"{format_value(vm_data['memory_usage_avg'])}, "
                      f"{format_value(vm_data['used_storage'])}, "
                      f"{format_value(vm_data['guest_os'])}, "
                      f"{format_value(vm_data['prism_ip'])})")

    query = f"""
    INSERT INTO nutanix_vm_metrics (
        vm_name,
        vm_uuid,
        cluster_uuid,
        host_name,
        host_uuid,
        power_state,
        memory_capacity,
        cpu_count,
        disk_capacity,
        hypervisor_read_io_bandwidth_min,
        hypervisor_read_io_bandwidth_max,
        hypervisor_read_io_bandwidth_avg,
        hypervisor_write_io_bandwidth_min,
        hypervisor_write_io_bandwidth_max,
        hypervisor_write_io_bandwidth_avg,
        cpu_usage_min,
        cpu_usage_max,
        cpu_usage_avg,
        memory_usage_min,
        memory_usage_max,
        memory_usage_avg,
        used_storage,
        guest_os,
        prism_ip
    ) VALUES {", ".join(values)};"""
    return query.strip()

def main():
    all_data = []
    # Her bir PRISM_IP için döngü kuruyoruz
    for prism_ip in prism_ips:
        base_url = f"https://{prism_ip}:9440/PrismGateway/services/rest/v1"
        print(f"Processing Nutanix Prism IP: {prism_ip}")
        vms = fetch_vms(base_url)

        for vm in vms:
            vm_stats = fetch_vm_stats(base_url, vm["uuid"])
            used_storage = calculate_storage_usage(vm)
            guest_os = vm.get("guestOperatingSystem")

            vm_data = {
                "vm_name": vm["vmName"],
                "vm_uuid": vm["uuid"],
                "cluster_uuid": vm["clusterUuid"],
                "host_name": vm["hostName"],
                "host_uuid": vm["hostUuid"],
                "power_state": vm["powerState"],
                "memory_capacity": vm["memoryCapacityInBytes"],
                "cpu_count": vm["numVCpus"],
                "disk_capacity": vm["diskCapacityInBytes"],
                "hypervisor_read_io_bandwidth_min": vm_stats.get("hypervisor_read_io_bandwidth_kBps", {}).get("min"),
                "hypervisor_read_io_bandwidth_max": vm_stats.get("hypervisor_read_io_bandwidth_kBps", {}).get("max"),
                "hypervisor_read_io_bandwidth_avg": vm_stats.get("hypervisor_read_io_bandwidth_kBps", {}).get("avg"),
                "hypervisor_write_io_bandwidth_min": vm_stats.get("hypervisor_write_io_bandwidth_kBps", {}).get("min"),
                "hypervisor_write_io_bandwidth_max": vm_stats.get("hypervisor_write_io_bandwidth_kBps", {}).get("max"),
                "hypervisor_write_io_bandwidth_avg": vm_stats.get("hypervisor_write_io_bandwidth_kBps", {}).get("avg"),
                "cpu_usage_min": vm_stats.get("hypervisor_cpu_usage_ppm", {}).get("min"),
                "cpu_usage_max": vm_stats.get("hypervisor_cpu_usage_ppm", {}).get("max"),
                "cpu_usage_avg": vm_stats.get("hypervisor_cpu_usage_ppm", {}).get("avg"),
                "memory_usage_min": vm_stats.get("hypervisor_memory_usage_ppm", {}).get("min"),
                "memory_usage_max": vm_stats.get("hypervisor_memory_usage_ppm", {}).get("max"),
                "memory_usage_avg": vm_stats.get("hypervisor_memory_usage_ppm", {}).get("avg"),
                "used_storage": used_storage,
                "guest_os": guest_os,
                "prism_ip": prism_ip
            }

            all_data.append(vm_data)

    insert_query = generate_insert_query(all_data)
    print(insert_query)

if __name__ == "__main__":
    main()
