#!/usr/bin/env python3
import requests
import statistics
import time
import argparse

# Argümanları al
parser = argparse.ArgumentParser(
    description='Fetch Nutanix host stats via Prism API'
)
parser.add_argument(
    '--prism-ips',
    required=True,
    help='Comma-separated Prism IPs (e.g. 10.0.0.1,10.0.0.2)'
)
parser.add_argument(
    '--username',
    required=True,
    help='Prism API kullanıcı adı'
)
parser.add_argument(
    '--password',
    required=True,
    help='Prism API parolası'
)
args = parser.parse_args()

# Konfigürasyon verileri
prism_ips = [ip.strip() for ip in args.prism_ips.split(',') if ip.strip()]
USERNAME = args.username
PASSWORD = args.password

# SSL sertifika uyarılarını atlamak için
requests.packages.urllib3.disable_warnings()

# Headers & Auth
HEADERS = {'Accept': 'application/json', 'Content-Type': 'application/json'}
AUTH = (USERNAME, PASSWORD)


def fetch_hosts(base_url):
    """Hosts endpoint'inden bilgileri alır."""
    resp = requests.get(f"{base_url}/hosts/", headers=HEADERS, auth=AUTH, verify=False)
    resp.raise_for_status()
    return resp.json().get('entities', [])


def fetch_host_stats(base_url, uuid, mem_cap, cpu_cap):
    """Host için historical stats alınır."""
    end_time = int(time.time() * 1e6)
    start_time = end_time - int(15 * 60 * 1e6)
    metrics_groups = [
        ['hypervisor_memory_usage_ppm', 'hypervisor_cpu_usage_ppm',
         'hypervisor_num_transmitted_bytes', 'hypervisor_num_received_bytes'],
        ['read_io_bandwidth_kBps', 'write_io_bandwidth_kBps']
    ]
    results = {}
    for metrics in metrics_groups:
        q = '&'.join(f"metrics={m}" for m in metrics)
        url = f"{base_url}/hosts/{uuid}/stats/?{q}&start_time_in_usecs={start_time}&interval_in_secs=60"
        resp = requests.get(url, headers=HEADERS, auth=AUTH, verify=False)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            print(f"Warning: stats not found for host {uuid}")
            continue
        for stat in resp.json().get('stats_specific_responses', []):
            m = stat.get('metric')
            if stat.get('successful'):
                vals = stat.get('values', [])
                if vals:
                    if 'ppm' in m:
                        conv = [ (v / 1e6) * mem_cap if 'memory' in m else (v / 1e6) * cpu_cap for v in vals ]
                        results[m] = {'min': min(conv), 'max': max(conv), 'avg': statistics.mean(conv)}
                    else:
                        results[m] = {'min': min(vals), 'max': max(vals), 'avg': statistics.mean(vals)}
            else:
                results[m] = {'min': None, 'max': None, 'avg': None, 'error': stat.get('message')}
    return results


def generate_insert_query(data):
    """Tüm host verilerini tek INSERT sorgusunda birleştirir."""
    vals = []
    for d in data:
        try:
            cap = int(d.get('storage_capacity', 0))
        except (TypeError, ValueError):
            cap = 'NULL'
        try:
            use = int(d.get('storage_usage', 0))
        except (TypeError, ValueError):
            use = 'NULL'
        vals.append(
            f"('{d['host_name']}', '{d['host_uuid']}', '{d['cluster_uuid']}', "
            f"{d['total_memory_capacity']}, {d['total_cpu_capacity']}, {d['num_cpu_cores']}, "
            f"{d['total_vms']}, {d['boottime']}, "
            f"{d.get('network_transmitted_avg','NULL')}, {d.get('network_received_avg','NULL')}, "
            f"{d.get('memory_usage_min','NULL')}, {d.get('memory_usage_max','NULL')}, {d.get('memory_usage_avg','NULL')}, "
            f"{d.get('cpu_usage_min','NULL')}, {d.get('cpu_usage_max','NULL')}, {d.get('cpu_usage_avg','NULL')}, "
            f"{cap}, {use}, "
            f"{d.get('read_io_bandwidth_min','NULL')}, {d.get('read_io_bandwidth_max','NULL')}, {d.get('read_io_bandwidth_avg','NULL')}, "
            f"{d.get('write_io_bandwidth_min','NULL')}, {d.get('write_io_bandwidth_max','NULL')}, {d.get('write_io_bandwidth_avg','NULL')}" 
            ")"
        )
    query = (
        "INSERT INTO nutanix_host_metrics (host_name, host_uuid, cluster_uuid, "
        "total_memory_capacity, total_cpu_capacity, num_cpu_cores, total_vms, boottime, "
        "network_transmitted_avg, network_received_avg, memory_usage_min, memory_usage_max, memory_usage_avg, "
        "cpu_usage_min, cpu_usage_max, cpu_usage_avg, storage_capacity, storage_usage, "
        "read_io_bandwidth_min, read_io_bandwidth_max, read_io_bandwidth_avg, "
        "write_io_bandwidth_min, write_io_bandwidth_max, write_io_bandwidth_avg) VALUES "
        + ", ".join(vals) + ";"
    )
    return query


def main():
    all_data = []
    for ip in prism_ips:
        base = f"https://{ip}:9440/PrismGateway/services/rest/v2.0"
        hosts = fetch_hosts(base)
        for h in hosts:
            stats = fetch_host_stats(
                base,
                h['uuid'],
                h.get('memory_capacity_in_bytes', 0),
                h.get('cpu_capacity_in_hz', 0)
            )
            d = {
                'host_name': h.get('name'),
                'host_uuid': h.get('uuid'),
                'cluster_uuid': h.get('cluster_uuid'),
                'total_memory_capacity': h.get('memory_capacity_in_bytes', 0),
                'total_cpu_capacity': h.get('cpu_capacity_in_hz', 0),
                'num_cpu_cores': h.get('num_cpu_cores', 0),
                'total_vms': h.get('num_vms', 0),
                'boottime': h.get('boot_time_in_usecs', 0),
                'network_transmitted_avg': stats.get('hypervisor_num_transmitted_bytes', {}).get('avg'),
                'network_received_avg': stats.get('hypervisor_num_received_bytes', {}).get('avg'),
                'memory_usage_min': stats.get('hypervisor_memory_usage_ppm', {}).get('min'),
                'memory_usage_max': stats.get('hypervisor_memory_usage_ppm', {}).get('max'),
                'memory_usage_avg': stats.get('hypervisor_memory_usage_ppm', {}).get('avg'),
                'cpu_usage_min': stats.get('hypervisor_cpu_usage_ppm', {}).get('min'),
                'cpu_usage_max': stats.get('hypervisor_cpu_usage_ppm', {}).get('max'),
                'cpu_usage_avg': stats.get('hypervisor_cpu_usage_ppm', {}).get('avg'),
                'storage_capacity': h.get('usage_stats', {}).get('storage.capacity_bytes', 0),
                'storage_usage': h.get('usage_stats', {}).get('storage.usage_bytes', 0),
                'read_io_bandwidth_min': stats.get('read_io_bandwidth_kBps', {}).get('min'),
                'read_io_bandwidth_max': stats.get('read_io_bandwidth_kBps', {}).get('max'),
                'read_io_bandwidth_avg': stats.get('read_io_bandwidth_kBps', {}).get('avg'),
                'write_io_bandwidth_min': stats.get('write_io_bandwidth_kBps', {}).get('min'),
                'write_io_bandwidth_max': stats.get('write_io_bandwidth_kBps', {}).get('max'),
                'write_io_bandwidth_avg': stats.get('write_io_bandwidth_kBps', {}).get('avg')
            }
            all_data.append(d)
    print(generate_insert_query(all_data))

if __name__ == '__main__':
    main()
