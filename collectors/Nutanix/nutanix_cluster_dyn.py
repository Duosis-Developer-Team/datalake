#!/usr/bin/env python3
import requests
import statistics
import time
import argparse

# Argümanları al
parser = argparse.ArgumentParser(
    description='Fetch Nutanix cluster stats via Prism API'
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

# API istek başlıkları ve kimlik doğrulama
HEADERS = {'Accept': 'application/json', 'Content-Type': 'application/json'}
AUTH = (USERNAME, PASSWORD)


def fetch_clusters(base_url):
    """Cluster verilerini almak için clusters endpoint'ine gider."""
    url = f"{base_url}/clusters/"
    resp = requests.get(url, headers=HEADERS, auth=AUTH, verify=False)
    resp.raise_for_status()
    entities = resp.json().get('entities', [])
    clusters = []
    for c in entities:
        dc = c.get('name', '').split('-')[0]
        clusters.append({
            'datacenter_name': dc,
            'cluster_name': c.get('name'),
            'cluster_uuid': c.get('uuid'),
            'num_nodes': c.get('num_nodes')
        })
    return clusters


def fetch_hosts(base_url, cluster_uuid):
    """Cluster UUID ile host bilgilerini alır."""
    url = f"{base_url}/hosts/"
    resp = requests.get(url, headers=HEADERS, auth=AUTH, verify=False)
    resp.raise_for_status()
    return resp.json().get('entities', [])


def fetch_host_stats(base_url, host_uuid):
    """Belirli bir host için historical stats verilerini alır."""
    end_time = int(time.time() * 1e6)
    start_time = end_time - int(15 * 60 * 1e6)
    metrics_groups = [
        ['hypervisor_memory_usage_ppm','hypervisor_cpu_usage_ppm','hypervisor_num_transmitted_bytes','hypervisor_num_received_bytes'],
        ['hypervisor_read_io_bandwidth_kBps','hypervisor_write_io_bandwidth_kBps','storage.usage_bytes','storage.capacity_bytes']
    ]
    results = {}
    for metrics in metrics_groups:
        params = '&'.join(f"metrics={m}" for m in metrics)
        url = f"{base_url}/hosts/{host_uuid}/stats/?{params}&start_time_in_usecs={start_time}&interval_in_secs=60"
        resp = requests.get(url, headers=HEADERS, auth=AUTH, verify=False)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            print(f"Warning: stats not found for host {host_uuid}")
            continue
        for stat in resp.json().get('stats_specific_responses', []):
            m = stat.get('metric')
            if stat.get('successful'):
                vals = stat.get('values', [])
                if vals:
                    results[m] = {'min': min(vals), 'max': max(vals), 'avg': statistics.mean(vals)}
            else:
                results[m] = {'min': None, 'max': None, 'avg': None, 'error': stat.get('message')}
    return results


def generate_insert_queries(data):
    """Veriyi INSERT sorgusu şeklinde hazırlar."""
    template = (
        "INSERT INTO nutanix_cluster_metrics ("
        "datacenter_name, cluster_name, cluster_uuid, num_nodes, "
        "total_memory_capacity, total_cpu_capacity, total_vms, "
        "network_transmitted_avg, network_received_avg, "
        "storage_capacity, storage_usage, "
        "memory_usage_min, memory_usage_max, memory_usage_avg, "
        "cpu_usage_min, cpu_usage_max, cpu_usage_avg, "
        "read_io_bandwidth_min, read_io_bandwidth_max, read_io_bandwidth_avg, "
        "write_io_bandwidth_min, write_io_bandwidth_max, write_io_bandwidth_avg) VALUES ("
        "'{datacenter_name}', '{cluster_name}', '{cluster_uuid}', {num_nodes}, "
        "{total_memory_capacity}, {total_cpu_capacity}, {total_vms}, "
        "{network_transmitted_avg}, {network_received_avg}, "
        "{storage_capacity}, {storage_usage}, "
        "{memory_usage_min}, {memory_usage_max}, {memory_usage_avg}, "
        "{cpu_usage_min}, {cpu_usage_max}, {cpu_usage_avg}, "
        "{read_io_bandwidth_min}, {read_io_bandwidth_max}, {read_io_bandwidth_avg}, "
        "{write_io_bandwidth_min}, {write_io_bandwidth_max}, {write_io_bandwidth_avg});"
    )
    queries = []
    for d in data:
        rec = {k: (v if v is not None else 'NULL') for k, v in d.items()}
        queries.append(template.format(**rec))
    return queries


def main():
    all_data = []
    for ip in prism_ips:
        base = f"https://{ip}:9440/PrismGateway/services/rest/v2.0"
        for c in fetch_clusters(base):
            mem_cap = cpu_cap = vm_count = 0
            net_tx = []; net_rx = []; mem_usg = []; cpu_usg = []
            read_io = []; write_io = []; storage_cap = storage_usg = 0
            hosts = fetch_hosts(base, c['cluster_uuid'])
            for h in hosts:
                stats = fetch_host_stats(base, h['uuid'])
                mem_cap += h.get('memory_capacity_in_bytes', 0)
                cpu_cap += h.get('cpu_capacity_in_hz', 0)
                vm_count += h.get('num_vms', 0)
                for key, arr in [
                    ('hypervisor_num_transmitted_bytes', net_tx),
                    ('hypervisor_num_received_bytes', net_rx),
                    ('hypervisor_memory_usage_ppm', mem_usg),
                    ('hypervisor_cpu_usage_ppm', cpu_usg),
                    ('hypervisor_read_io_bandwidth_kBps', read_io),
                    ('hypervisor_write_io_bandwidth_kBps', write_io)
                ]:
                    val = stats.get(key, {}).get('avg')
                    if val is not None:
                        arr.append(val)
                # Safely convert storage stats to int
                cap_raw = h.get('usage_stats', {}).get('storage.capacity_bytes', 0)
                use_raw = h.get('usage_stats', {}).get('storage.usage_bytes', 0)
                try:
                    storage_cap += int(cap_raw)
                except (TypeError, ValueError):
                    pass
                try:
                    storage_usg += int(use_raw)
                except (TypeError, ValueError):
                    pass
            all_data.append({
                **c,
                'total_memory_capacity': mem_cap,
                'total_cpu_capacity': cpu_cap,
                'total_vms': vm_count,
                'network_transmitted_avg': statistics.mean(net_tx) if net_tx else None,
                'network_received_avg': statistics.mean(net_rx) if net_rx else None,
                'storage_capacity': storage_cap,
                'storage_usage': storage_usg,
                'memory_usage_min': min(mem_usg) if mem_usg else None,
                'memory_usage_max': max(mem_usg) if mem_usg else None,
                'memory_usage_avg': statistics.mean(mem_usg) if mem_usg else None,
                'cpu_usage_min': min(cpu_usg) if cpu_usg else None,
                'cpu_usage_max': max(cpu_usg) if cpu_usg else None,
                'cpu_usage_avg': statistics.mean(cpu_usg) if cpu_usg else None,
                'read_io_bandwidth_min': min(read_io) if read_io else None,
                'read_io_bandwidth_max': max(read_io) if read_io else None,
                'read_io_bandwidth_avg': statistics.mean(read_io) if read_io else None,
                'write_io_bandwidth_min': min(write_io) if write_io else None,
                'write_io_bandwidth_max': max(write_io) if write_io else None,
                'write_io_bandwidth_avg': statistics.mean(write_io) if write_io else None
            })
    for query in generate_insert_queries(all_data):
        print(query)

if __name__ == '__main__':
    main()
