#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VMware Unified Data Collector

Tek scriptte 4 eski VMware collector'ın (datacenter/cluster/host/vm) tüm data_type
output'larını üretir. configuration_file.json'dan VmWare bloğunu okur, listedeki her
vCenter'a bağlanır ve tek JSON array olarak stdout'a basar.

Üretilen data_type'lar:
- vmware_datacenter_config / vmware_datacenter_metrics_agg
- vmware_cluster_config / vmware_cluster_metrics_agg
- vmware_host_hardware / vmware_host_runtime / vmware_host_storage / vmware_host_perf_raw / vmware_host_perf_agg
- vmware_vm_config / vmware_vm_runtime / vmware_vm_storage / vmware_vm_perf_raw / vmware_vm_perf_agg

Output: stdout = JSON array. stderr = log/uyarı.
"""

import json
import ssl
import socket
import argparse
import sys
import os
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl


# ---------------------------------------------------------------------------
# Config path search (NetBackup collector mantığı)
# ---------------------------------------------------------------------------
CONFIG_PATH_CANDIDATES = [
    "configuration_file.json",
    "Datalake_Project/configuration_file.json",
    "../Datalake_Project/configuration_file.json",
    "./Datalake_Project/configuration_file.json",
    "/Datalake_Project/configuration_file.json",
]

# ---------------------------------------------------------------------------
# Performance counter setleri (eski scriptlerle birebir aynı)
# ---------------------------------------------------------------------------
COMMON_PERF_COUNTERS = [
    'cpu.usage.average',
    'mem.usage.average',
    'disk.read.average',
    'disk.write.average',
    'net.usage.average',
]

HOST_EXTRA_COUNTERS = [
    'power.power.average',
]


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------
class VMwareCollectorConfig:
    """vmware_data_collector çalışma konfigürasyonu."""
    def __init__(self):
        self.vcenters = []
        self.port = 443
        self.username = None
        self.password = None
        self.perf_interval = 300
        self.perf_window = 900
        self.max_workers = 32
        self.perf_batch_size = 24
        self.timeout = 1800
        self.max_hosts = 0
        self.max_vms = 0
        self.config_path_used = None


def parse_args():
    parser = argparse.ArgumentParser(
        description='VMware Unified Data Collector (config-driven)'
    )
    parser.add_argument('--config', type=str, default=None,
                        help='configuration_file.json yolu (default: arama listesi)')
    parser.add_argument('--vmware-ip', type=str, default=None,
                        help='Comma-separated vCenter hostname/IP (config override)')
    parser.add_argument('--vmware-port', type=int, default=None,
                        help='vCenter port (config override)')
    parser.add_argument('--vmware-username', type=str, default=None,
                        help='vCenter username (config override)')
    parser.add_argument('--vmware-password', type=str, default=None,
                        help='vCenter password (config override)')
    parser.add_argument('--perf-interval', type=int, default=300,
                        help='Performance interval seconds (default: 300)')
    parser.add_argument('--perf-window', type=int, default=900,
                        help='Performance window seconds (default: 900 = 15min)')
    parser.add_argument('--max-workers', type=int, default=32,
                        help='Max parallel workers (default: 32)')
    parser.add_argument('--perf-batch-size', type=int, default=24,
                        help='Entities per QueryPerf API call (default: 24, max 64)')
    parser.add_argument('--timeout', type=int, default=1800,
                        help='Socket+collection timeout sec (default: 1800; 0=disabled)')
    parser.add_argument('--max-hosts', type=int, default=0,
                        help='Max hosts (0=all)')
    parser.add_argument('--max-vms', type=int, default=0,
                        help='Max VMs (0=all)')
    parser.add_argument('--print-config-summary', action='store_true',
                        help='Sadece config yüklemeyi test eder, JSON output üretmez')
    return parser.parse_args()


def split_csv(value):
    if value is None:
        return []
    return [item.strip() for item in str(value).split(',') if item.strip()]


def find_config_file(explicit_path=None):
    """Config dosyasını arar. Önce explicit, sonra default adaylar."""
    if explicit_path:
        if os.path.isfile(explicit_path):
            return explicit_path
        raise FileNotFoundError(f"Explicit config path not found: {explicit_path}")
    for candidate in CONFIG_PATH_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(
        "configuration_file.json hiçbir aday konumda bulunamadı: "
        + ", ".join(CONFIG_PATH_CANDIDATES)
    )


def load_config(args):
    """CLI + config dosyası birleştirilerek VMwareCollectorConfig üretir."""
    cfg = VMwareCollectorConfig()
    cfg.perf_interval = args.perf_interval
    cfg.perf_window = args.perf_window
    cfg.max_workers = args.max_workers
    cfg.perf_batch_size = args.perf_batch_size
    cfg.timeout = args.timeout
    cfg.max_hosts = args.max_hosts
    cfg.max_vms = args.max_vms

    file_data = {}
    try:
        config_path = find_config_file(args.config)
        cfg.config_path_used = config_path
        with open(config_path, 'r') as f:
            file_data = json.load(f).get('VmWare', {}) or {}
        print(f"VMware config yüklendi: {config_path}", file=sys.stderr)
    except FileNotFoundError as e:
        if not (args.vmware_ip and args.vmware_username and args.vmware_password):
            raise
        print(f"Uyarı: {e}; CLI override kullanılacak", file=sys.stderr)
    except Exception as e:
        print(f"Uyarı: config dosyası okunamadı: {e}", file=sys.stderr)

    # vCenter listesi
    if args.vmware_ip:
        cfg.vcenters = split_csv(args.vmware_ip)
    else:
        cfg.vcenters = split_csv(file_data.get('VMwareIP'))

    # Port
    port_val = args.vmware_port if args.vmware_port is not None else file_data.get('VMwarePort')
    if port_val is None or str(port_val).strip() == '':
        cfg.port = 443
    else:
        try:
            cfg.port = int(str(port_val).strip())
        except (TypeError, ValueError):
            print(f"Uyarı: VMwarePort parse edilemedi ('{port_val}'), 443 kullanılıyor", file=sys.stderr)
            cfg.port = 443

    # Credentials (key isimleri config dosyasıyla birebir uyumlu)
    cfg.username = (
        args.vmware_username
        or file_data.get('VMware_userName')
        or file_data.get('VMware_username')
        or file_data.get('username')
    )
    cfg.password = (
        args.vmware_password
        or file_data.get('VMware_password')
        or file_data.get('password')
    )

    # Validation
    if not cfg.vcenters:
        raise ValueError("VMwareIP listesi boş (config + CLI birlikte de değer üretmedi)")
    if not cfg.username:
        raise ValueError("VMware_userName / username eksik")
    if not cfg.password:
        raise ValueError("VMware_password / password eksik")

    return cfg


def print_config_summary(cfg):
    """Password göstermeden config özeti yazar (stderr)."""
    print(f"config_path_used={cfg.config_path_used}", file=sys.stderr)
    print(f"vcenters_count={len(cfg.vcenters)}", file=sys.stderr)
    print(f"port={cfg.port}", file=sys.stderr)
    print(f"username_present={bool(cfg.username)}", file=sys.stderr)
    print(f"password_present={bool(cfg.password)}", file=sys.stderr)
    print(f"perf_interval={cfg.perf_interval}", file=sys.stderr)
    print(f"perf_window={cfg.perf_window}", file=sys.stderr)
    print(f"max_workers={cfg.max_workers}", file=sys.stderr)
    print(f"perf_batch_size={cfg.perf_batch_size}", file=sys.stderr)
    print(f"timeout={cfg.timeout}", file=sys.stderr)
    print(f"max_hosts={cfg.max_hosts}", file=sys.stderr)
    print(f"max_vms={cfg.max_vms}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Helpers (eski scriptlerle birebir aynı semantik)
# ---------------------------------------------------------------------------
def safe_get_attr(obj, attr_path, default=None):
    """Nested attribute'ı güvenli şekilde döndür."""
    try:
        parts = attr_path.split('.')
        value = obj
        for part in parts:
            value = getattr(value, part, None)
            if value is None:
                return default
        return value
    except (AttributeError, TypeError):
        return default


def safe_timestamp(dt_obj):
    """datetime'ı ISO-8601 string'e çevirir. Epoch (1970) -> None (VMware unset timestamp)."""
    if dt_obj is None:
        return None
    try:
        if dt_obj.year == 1970 and dt_obj.month == 1 and dt_obj.day == 1:
            return None
        return dt_obj.isoformat()
    except Exception:
        return None


def serialize_record(record):
    """List/tuple alanları JSON string'e çevirir (PostgreSQL uyumu)."""
    for key, value in record.items():
        if isinstance(value, (list, tuple)) and not isinstance(value, str):
            record[key] = json.dumps(value)
    return record


def get_folder_path(vm):
    """VM klasör path'ini parent hierarchy üzerinden çıkarır."""
    try:
        path_parts = []
        entity = vm.parent
        while entity:
            if isinstance(entity, vim.Folder):
                if entity.name not in ['vm', 'Datacenters', 'host', 'network', 'datastore']:
                    path_parts.append(entity.name)
            elif isinstance(entity, vim.Datacenter):
                break
            entity = getattr(entity, 'parent', None)
        return '/'.join(reversed(path_parts)) if path_parts else ''
    except Exception:
        return ''


# ---------------------------------------------------------------------------
# Performance counter map yardımcıları
# ---------------------------------------------------------------------------
def build_counter_data(perf_mgr, desired_counter_names):
    """
    Eski scriptlerin counter handling'ini tek yerde toplar.
    Returns:
        counter_ids: list[int]                                  - QueryPerf metric_id için
        counter_info_map: dict[int, dict]                       - perf_raw zenginleştirme için
        scale_map: dict[int, dict]                              - cluster/datacenter aggregation için (scale + percent)
        name_to_id: dict[str, int]                              - 'cpu.usage.average' -> counter_id
    """
    counter_ids = []
    counter_info_map = {}
    scale_map = {}
    name_to_id = {}

    for pc in perf_mgr.perfCounter:
        full_name = f"{pc.groupInfo.key}.{pc.nameInfo.key}.{pc.rollupType}"
        if full_name not in desired_counter_names:
            continue
        cid = pc.key
        scale = getattr(pc.unitInfo, 'scale', 1) or 1
        unit_key = getattr(pc.unitInfo, 'key', '') or ''
        unit_label = getattr(pc.unitInfo, 'label', '') or ''
        is_percent = 'percent' in unit_key.lower() or '%' in unit_label.lower()

        counter_ids.append(cid)
        counter_info_map[cid] = {
            'name': full_name,
            'group': pc.groupInfo.key,
            'name_short': pc.nameInfo.key,
            'rollup': pc.rollupType,
            'stats_type': pc.statsType,
            'unit_key': pc.unitInfo.key,
            'unit_label': pc.unitInfo.label,
        }
        scale_map[cid] = {
            'name': full_name,
            'scale': scale,
            'is_percent': is_percent,
        }
        name_to_id[full_name] = cid

    return counter_ids, counter_info_map, scale_map, name_to_id


def extract_scaled_stats(result_item, scale_map):
    """
    QueryPerf result'ından host/vm için scaled+percent-converted {counter_id: {avg,min,max}} üretir.
    Eski cluster_collector / datacenter_collector'daki query_host_perf_stats davranışıyla birebir.
    Çoklu instance durumunda eski kod 'last one wins' davranışı uyguluyor; biz de aynısını yapıyoruz.
    """
    stats = {}
    if not result_item or not result_item.value:
        return stats
    for perf_metric in result_item.value:
        cid = perf_metric.id.counterId
        if not perf_metric.value:
            continue
        info = scale_map.get(cid)
        if not info:
            continue
        scale = info.get('scale', 1) or 1
        is_percent = info.get('is_percent', False)
        raw_avg = sum(perf_metric.value) / len(perf_metric.value)
        raw_min = min(perf_metric.value)
        raw_max = max(perf_metric.value)
        avg = raw_avg / scale
        mn = raw_min / scale
        mx = raw_max / scale
        if is_percent:
            avg /= 100.0
            mn /= 100.0
            mx /= 100.0
        # last-one-wins (multi-instance case için eski davranış)
        stats[cid] = {'avg': avg, 'min': mn, 'max': mx}
    return stats


# ---------------------------------------------------------------------------
# DATACENTER
# ---------------------------------------------------------------------------
def extract_datacenter_config(datacenter, vcenter_uuid, collection_timestamp):
    """Eski vmware_datacenter_collector.extract_datacenter_config ile birebir."""
    return {
        "data_type": "vmware_datacenter_config",
        "collection_timestamp": collection_timestamp,
        "vcenter_uuid": vcenter_uuid,
        "datacenter_moid": datacenter._moId,

        "name": datacenter.name,
        "overall_status": safe_get_attr(datacenter, 'overallStatus'),
    }


def calculate_datacenter_metrics_agg(
    datacenter, vcenter_uuid, collection_timestamp,
    cluster_objs, host_scaled_stats_by_moid, scale_map,
    start_time, end_time
):
    """
    Eski vmware_datacenter_collector.calculate_datacenter_metrics_agg ile birebir.
    host_scaled_stats_by_moid: {host_moid: {counter_id: {avg,min,max}}} (önceden hesaplanmış)
    """
    total_cluster_count = len(cluster_objs)
    total_host_count = 0
    total_vm_count = 0

    total_cpu_cores = 0
    total_cpu_threads = 0
    total_cpu_mhz_capacity = 0
    total_cpu_mhz_used = 0

    total_memory_bytes_capacity = 0
    total_memory_bytes_used = 0

    total_storage_bytes_capacity = 0
    total_storage_bytes_used = 0

    cpu_perc_list = []
    mem_perc_list = []
    disk_kbps_list = []
    net_kbps_list = []

    for cluster in cluster_objs:
        total_host_count += len(cluster.host)

        for host in cluster.host:
            for vm in host.vm:
                if not getattr(vm.config, 'template', False):
                    total_vm_count += 1

            hw = host.summary.hardware
            qs = host.summary.quickStats

            total_cpu_cores += hw.numCpuCores or 0
            total_cpu_threads += hw.numCpuThreads or 0
            total_cpu_mhz_capacity += (hw.numCpuCores or 0) * (hw.cpuMhz or 0)
            total_cpu_mhz_used += qs.overallCpuUsage or 0

            total_memory_bytes_capacity += hw.memorySize or 0
            total_memory_bytes_used += (qs.overallMemoryUsage or 0) * 1024 * 1024

            stats = host_scaled_stats_by_moid.get(host._moId, {})
            for counter_id, stat in stats.items():
                info = scale_map.get(counter_id, {})
                counter_name = info.get('name', '')
                if 'cpu.usage' in counter_name:
                    cpu_perc_list.append(stat)
                elif 'mem.usage' in counter_name:
                    mem_perc_list.append(stat)
                elif 'disk' in counter_name:
                    disk_kbps_list.append(stat)
                elif 'net.usage' in counter_name:
                    net_kbps_list.append(stat)

    # Storage from datastores
    for ds in datacenter.datastore:
        total_storage_bytes_capacity += ds.summary.capacity or 0
        total_storage_bytes_used += (ds.summary.capacity or 0) - (ds.summary.freeSpace or 0)

    cpu_avg = sum(s['avg'] for s in cpu_perc_list) / len(cpu_perc_list) if cpu_perc_list else 0
    cpu_min = min(s['min'] for s in cpu_perc_list) if cpu_perc_list else 0
    cpu_max = max(s['max'] for s in cpu_perc_list) if cpu_perc_list else 0

    mem_avg = sum(s['avg'] for s in mem_perc_list) / len(mem_perc_list) if mem_perc_list else 0
    mem_min = min(s['min'] for s in mem_perc_list) if mem_perc_list else 0
    mem_max = max(s['max'] for s in mem_perc_list) if mem_perc_list else 0

    disk_avg = sum(s['avg'] for s in disk_kbps_list) if disk_kbps_list else 0
    disk_min = sum(s['min'] for s in disk_kbps_list) if disk_kbps_list else 0
    disk_max = sum(s['max'] for s in disk_kbps_list) if disk_kbps_list else 0

    net_avg = sum(s['avg'] for s in net_kbps_list) if net_kbps_list else 0
    net_min = sum(s['min'] for s in net_kbps_list) if net_kbps_list else 0
    net_max = sum(s['max'] for s in net_kbps_list) if net_kbps_list else 0

    return {
        "data_type": "vmware_datacenter_metrics_agg",
        "collection_timestamp": collection_timestamp,
        "vcenter_uuid": vcenter_uuid,
        "datacenter_moid": datacenter._moId,
        "datacenter_name": datacenter.name,

        "window_start": start_time.isoformat(),
        "window_end": end_time.isoformat(),

        "total_cluster_count": total_cluster_count,
        "total_host_count": total_host_count,
        "total_vm_count": total_vm_count,

        "total_cpu_cores": total_cpu_cores,
        "total_cpu_threads": total_cpu_threads,
        "total_cpu_mhz_capacity": total_cpu_mhz_capacity,
        "total_cpu_mhz_used": total_cpu_mhz_used,

        "total_memory_bytes_capacity": total_memory_bytes_capacity,
        "total_memory_bytes_used": total_memory_bytes_used,

        "total_storage_bytes_capacity": total_storage_bytes_capacity,
        "total_storage_bytes_used": total_storage_bytes_used,

        "cpu_usage_avg_percent": cpu_avg,
        "cpu_usage_min_percent": cpu_min,
        "cpu_usage_max_percent": cpu_max,
        "memory_usage_avg_percent": mem_avg,
        "memory_usage_min_percent": mem_min,
        "memory_usage_max_percent": mem_max,

        "disk_usage_avg_kbps": disk_avg,
        "disk_usage_min_kbps": disk_min,
        "disk_usage_max_kbps": disk_max,

        "network_usage_avg_kbps": net_avg,
        "network_usage_min_kbps": net_min,
        "network_usage_max_kbps": net_max,
    }


# ---------------------------------------------------------------------------
# CLUSTER
# ---------------------------------------------------------------------------
def extract_cluster_config(cluster, vcenter_uuid, collection_timestamp, datacenter_moid):
    """Eski vmware_cluster_collector.extract_cluster_config ile birebir."""
    summary = cluster.summary
    config = cluster.configuration

    return {
        "data_type": "vmware_cluster_config",
        "collection_timestamp": collection_timestamp,
        "vcenter_uuid": vcenter_uuid,
        "datacenter_moid": datacenter_moid,
        "cluster_moid": cluster._moId,
        "name": cluster.name,

        "summary_num_hosts": safe_get_attr(summary, 'numHosts'),
        "summary_num_cpu_cores": safe_get_attr(summary, 'numCpuCores'),
        "summary_num_cpu_threads": safe_get_attr(summary, 'numCpuThreads'),
        "summary_effective_cpu": safe_get_attr(summary, 'effectiveCpu'),
        "summary_total_cpu": safe_get_attr(summary, 'totalCpu'),
        "summary_num_effective_hosts": safe_get_attr(summary, 'numEffectiveHosts'),
        "summary_total_memory": safe_get_attr(summary, 'totalMemory'),
        "summary_effective_memory": safe_get_attr(summary, 'effectiveMemory'),
        "summary_overall_status": safe_get_attr(summary, 'overallStatus'),

        "config_das_enabled": safe_get_attr(config, 'dasConfig.enabled'),
        "config_das_vm_monitoring": safe_get_attr(config, 'dasConfig.vmMonitoring'),
        "config_das_host_monitoring": safe_get_attr(config, 'dasConfig.hostMonitoring'),

        "config_drs_enabled": safe_get_attr(config, 'drsConfig.enabled'),
        "config_drs_default_vm_behavior": safe_get_attr(config, 'drsConfig.defaultVmBehavior'),
        "config_drs_vmotion_rate": safe_get_attr(config, 'drsConfig.vmotionRate'),

        "config_dpm_enabled": safe_get_attr(config, 'dpmConfigInfo.enabled'),
    }


def calculate_cluster_metrics_agg(
    cluster, vcenter_uuid, datacenter_moid, collection_timestamp,
    host_scaled_stats_by_moid, scale_map,
    start_time, end_time
):
    """Eski vmware_cluster_collector.calculate_cluster_metrics_agg ile birebir."""
    hosts = cluster.host
    total_host_count = len(hosts)
    total_vm_count = sum(
        1 for h in hosts
        for vm in h.vm
        if not getattr(vm.config, 'template', False)
    )

    total_cpu_cores = 0
    total_cpu_threads = 0
    total_cpu_mhz_capacity = 0
    total_cpu_mhz_used = 0
    total_memory_bytes_capacity = 0
    total_memory_bytes_used = 0

    cpu_perc_list = []
    mem_perc_list = []
    disk_kbps_list = []
    net_kbps_list = []

    for host in hosts:
        hw = host.summary.hardware
        qs = host.summary.quickStats

        total_cpu_cores += hw.numCpuCores or 0
        total_cpu_threads += hw.numCpuThreads or 0
        total_cpu_mhz_capacity += (hw.numCpuCores or 0) * (hw.cpuMhz or 0)
        total_cpu_mhz_used += qs.overallCpuUsage or 0

        total_memory_bytes_capacity += hw.memorySize or 0
        total_memory_bytes_used += (qs.overallMemoryUsage or 0) * 1024 * 1024

        stats = host_scaled_stats_by_moid.get(host._moId, {})
        for counter_id, stat in stats.items():
            info = scale_map.get(counter_id, {})
            counter_name = info.get('name', '')
            if 'cpu.usage' in counter_name:
                cpu_perc_list.append(stat)
            elif 'mem.usage' in counter_name:
                mem_perc_list.append(stat)
            elif 'disk' in counter_name:
                disk_kbps_list.append(stat)
            elif 'net.usage' in counter_name:
                net_kbps_list.append(stat)

    total_storage_bytes_capacity = 0
    total_storage_bytes_used = 0
    for ds in cluster.datastore:
        cap = ds.summary.capacity or 0
        free = ds.summary.freeSpace or 0
        total_storage_bytes_capacity += cap
        total_storage_bytes_used += cap - free

    cpu_avg = sum(s['avg'] for s in cpu_perc_list) / len(cpu_perc_list) if cpu_perc_list else None
    cpu_min = min(s['min'] for s in cpu_perc_list) if cpu_perc_list else None
    cpu_max = max(s['max'] for s in cpu_perc_list) if cpu_perc_list else None

    mem_avg = sum(s['avg'] for s in mem_perc_list) / len(mem_perc_list) if mem_perc_list else None
    mem_min = min(s['min'] for s in mem_perc_list) if mem_perc_list else None
    mem_max = max(s['max'] for s in mem_perc_list) if mem_perc_list else None

    disk_avg = sum(s['avg'] for s in disk_kbps_list) if disk_kbps_list else None
    disk_min = sum(s['min'] for s in disk_kbps_list) if disk_kbps_list else None
    disk_max = sum(s['max'] for s in disk_kbps_list) if disk_kbps_list else None

    net_avg = sum(s['avg'] for s in net_kbps_list) if net_kbps_list else None
    net_min = sum(s['min'] for s in net_kbps_list) if net_kbps_list else None
    net_max = sum(s['max'] for s in net_kbps_list) if net_kbps_list else None

    return {
        "data_type": "vmware_cluster_metrics_agg",
        "collection_timestamp": collection_timestamp,
        "vcenter_uuid": vcenter_uuid,
        "datacenter_moid": datacenter_moid,
        "cluster_moid": cluster._moId,
        "cluster_name": cluster.name,

        "window_start": start_time.isoformat(),
        "window_end": end_time.isoformat(),

        "total_host_count": total_host_count,
        "total_vm_count": total_vm_count,

        "total_cpu_cores": total_cpu_cores,
        "total_cpu_threads": total_cpu_threads,
        "total_cpu_mhz_capacity": total_cpu_mhz_capacity,
        "total_cpu_mhz_used": total_cpu_mhz_used,

        "total_memory_bytes_capacity": total_memory_bytes_capacity,
        "total_memory_bytes_used": total_memory_bytes_used,

        "total_storage_bytes_capacity": total_storage_bytes_capacity,
        "total_storage_bytes_used": total_storage_bytes_used,

        "cpu_usage_avg_percent": cpu_avg,
        "cpu_usage_min_percent": cpu_min,
        "cpu_usage_max_percent": cpu_max,
        "memory_usage_avg_percent": mem_avg,
        "memory_usage_min_percent": mem_min,
        "memory_usage_max_percent": mem_max,

        "disk_usage_avg_kbps": disk_avg,
        "disk_usage_min_kbps": disk_min,
        "disk_usage_max_kbps": disk_max,

        "network_usage_avg_kbps": net_avg,
        "network_usage_min_kbps": net_min,
        "network_usage_max_kbps": net_max,
    }


# ---------------------------------------------------------------------------
# HOST
# ---------------------------------------------------------------------------
def extract_host_hardware(host, vcenter_uuid, collection_timestamp, hierarchy):
    """Eski vmware_host_collector.extract_host_hardware ile birebir."""
    hw = host.summary.hardware
    sys_info = host.hardware.systemInfo
    product = host.config.product

    other_id_info = None
    if hasattr(sys_info, 'otherIdentifyingInfo') and sys_info.otherIdentifyingInfo:
        other_id_info = json.dumps([str(info) for info in sys_info.otherIdentifyingInfo])

    return {
        "data_type": "vmware_host_hardware",
        "collection_timestamp": collection_timestamp,
        "vcenter_uuid": vcenter_uuid,
        "datacenter_moid": hierarchy.get('datacenter'),
        "cluster_moid": hierarchy.get('cluster'),
        "host_moid": host._moId,

        "vendor": safe_get_attr(hw, 'vendor'),
        "model": safe_get_attr(hw, 'model'),
        "uuid": safe_get_attr(hw, 'uuid'),
        "memory_size": safe_get_attr(hw, 'memorySize'),
        "cpu_model": safe_get_attr(hw, 'cpuModel'),
        "cpu_mhz": safe_get_attr(hw, 'cpuMhz'),
        "num_cpu_pkgs": safe_get_attr(hw, 'numCpuPkgs'),
        "num_cpu_cores": safe_get_attr(hw, 'numCpuCores'),
        "num_cpu_threads": safe_get_attr(hw, 'numCpuThreads'),
        "num_nics": safe_get_attr(hw, 'numNics'),
        "num_hbas": safe_get_attr(hw, 'numHBAs'),

        "system_info_vendor": safe_get_attr(sys_info, 'vendor'),
        "system_info_model": safe_get_attr(sys_info, 'model'),
        "system_info_uuid": safe_get_attr(sys_info, 'uuid'),
        "system_info_other_identifying_info": other_id_info,

        "product_name": safe_get_attr(product, 'name'),
        "product_full_name": safe_get_attr(product, 'fullName'),
        "product_vendor": safe_get_attr(product, 'vendor'),
        "product_version": safe_get_attr(product, 'version'),
        "product_build": safe_get_attr(product, 'build'),
        "product_locale_version": safe_get_attr(product, 'localeVersion'),
        "product_locale_build": safe_get_attr(product, 'localeBuild'),
        "product_os_type": safe_get_attr(product, 'osType'),
        "product_product_line_id": safe_get_attr(product, 'productLineId'),
        "product_api_type": safe_get_attr(product, 'apiType'),
        "product_api_version": safe_get_attr(product, 'apiVersion'),
        "product_license_product_name": safe_get_attr(product, 'licenseProductName'),
        "product_license_product_version": safe_get_attr(product, 'licenseProductVersion'),
    }


def extract_host_runtime(host, vcenter_uuid, collection_timestamp):
    """Eski vmware_host_collector.extract_host_runtime ile birebir."""
    runtime = host.runtime
    qs = host.summary.quickStats
    config = host.summary.config

    return {
        "data_type": "vmware_host_runtime",
        "collection_timestamp": collection_timestamp,
        "vcenter_uuid": vcenter_uuid,
        "host_moid": host._moId,

        "connection_state": safe_get_attr(runtime, 'connectionState'),
        "power_state": safe_get_attr(runtime, 'powerState'),
        "standby_mode": safe_get_attr(runtime, 'standbyMode'),
        "in_maintenance_mode": safe_get_attr(runtime, 'inMaintenanceMode'),
        "in_quarantine_mode": safe_get_attr(runtime, 'inQuarantineMode'),
        "boot_time": safe_timestamp(safe_get_attr(runtime, 'bootTime')),
        "health_system_runtime_system_health_info": str(safe_get_attr(runtime, 'healthSystemRuntime.systemHealthInfo')) if safe_get_attr(runtime, 'healthSystemRuntime.systemHealthInfo') else None,

        "quick_stats_overall_cpu_usage": safe_get_attr(qs, 'overallCpuUsage'),
        "quick_stats_overall_memory_usage": safe_get_attr(qs, 'overallMemoryUsage'),
        "quick_stats_distributed_cpu_fairness": safe_get_attr(qs, 'distributedCpuFairness'),
        "quick_stats_distributed_memory_fairness": safe_get_attr(qs, 'distributedMemoryFairness'),
        "quick_stats_uptime": safe_get_attr(qs, 'uptime'),

        "config_name": safe_get_attr(config, 'name'),
        "config_port": safe_get_attr(config, 'port'),
        "config_ssl_thumbprint": safe_get_attr(config, 'sslThumbprint'),
    }


def extract_host_storage(host, vcenter_uuid, collection_timestamp):
    """Eski vmware_host_collector.extract_host_storage ile birebir (one row per datastore)."""
    storage_records = []
    if not host.datastore:
        return storage_records

    for ds in host.datastore:
        storage_records.append({
            "data_type": "vmware_host_storage",
            "collection_timestamp": collection_timestamp,
            "vcenter_uuid": vcenter_uuid,
            "host_moid": host._moId,
            "datastore_moid": ds._moId,

            "datastore_name": safe_get_attr(ds, 'name'),
            "datastore_url": safe_get_attr(ds, 'summary.url'),
            "datastore_capacity": safe_get_attr(ds, 'summary.capacity'),
            "datastore_free_space": safe_get_attr(ds, 'summary.freeSpace'),
            "datastore_type": safe_get_attr(ds, 'summary.type'),
            "datastore_accessible": safe_get_attr(ds, 'summary.accessible'),
            "datastore_multiple_host_access": safe_get_attr(ds, 'summary.multipleHostAccess'),
        })

    return storage_records


def host_perf_raw_from_query_result(host_moid, result_item, vcenter_uuid, collection_timestamp,
                                    counter_info_map, start_time, interval_id):
    """Eski vmware_host_collector.perf_raw_from_query_result ile birebir."""
    perf_raw_records = []
    if not result_item or not result_item.value:
        return perf_raw_records
    for perf_metric in result_item.value:
        counter_id = perf_metric.id.counterId
        instance = perf_metric.id.instance or ''
        counter_info = counter_info_map.get(counter_id) or {
            'name': f'counter_{counter_id}', 'group': 'unknown', 'name_short': 'unknown',
            'rollup': 'unknown', 'stats_type': 'unknown', 'unit_key': 'unknown', 'unit_label': ''}
        if not perf_metric.value:
            continue
        interval_seconds = interval_id
        for i, value in enumerate(perf_metric.value):
            sample_time = start_time + timedelta(seconds=i * interval_seconds)
            perf_raw_records.append({
                "data_type": "vmware_host_perf_raw",
                "collection_timestamp": collection_timestamp,
                "vcenter_uuid": vcenter_uuid,
                "host_moid": host_moid,
                "counter_id": counter_id,
                "counter_name": counter_info['name'],
                "counter_group": counter_info['group'],
                "counter_name_short": counter_info['name_short'],
                "counter_rollup_type": counter_info['rollup'],
                "counter_stats_type": counter_info['stats_type'],
                "counter_unit_key": counter_info['unit_key'],
                "counter_unit_label": counter_info['unit_label'],
                "instance": instance,
                "sample_timestamp": sample_time.isoformat(),
                "value": value,
                "interval_id": interval_id,
            })
    return perf_raw_records


def calculate_host_perf_agg(perf_raw_records, vcenter_uuid, collection_timestamp, start_time, end_time):
    """Eski vmware_host_collector.calculate_host_perf_agg ile birebir."""
    perf_agg_records = []
    grouped = {}
    for record in perf_raw_records:
        key = (record['counter_id'], record['instance'])
        if key not in grouped:
            grouped[key] = {
                'values': [],
                'counter_info': {
                    'counter_name': record['counter_name'],
                    'counter_group': record['counter_group'],
                    'counter_rollup_type': record['counter_rollup_type'],
                    'counter_unit_key': record['counter_unit_key'],
                },
                'host_moid': record['host_moid']
            }
        grouped[key]['values'].append(record['value'])

    for (counter_id, instance), data in grouped.items():
        values = data['values']
        if not values:
            continue
        perf_agg_records.append({
            "data_type": "vmware_host_perf_agg",
            "collection_timestamp": collection_timestamp,
            "vcenter_uuid": vcenter_uuid,
            "host_moid": data['host_moid'],

            "window_start": start_time.isoformat(),
            "window_end": end_time.isoformat(),
            "window_duration_seconds": int((end_time - start_time).total_seconds()),
            "sample_count": len(values),

            "counter_id": counter_id,
            "counter_name": data['counter_info']['counter_name'],
            "counter_group": data['counter_info']['counter_group'],
            "counter_rollup_type": data['counter_info']['counter_rollup_type'],
            "counter_unit_key": data['counter_info']['counter_unit_key'],
            "instance": instance,

            "value_avg": sum(values) / len(values),
            "value_min": min(values),
            "value_max": max(values),
            "value_stddev": None,
            "value_first": values[0],
            "value_last": values[-1],
        })
    return perf_agg_records


def process_one_host_config_only(host, hierarchy, vcenter_uuid, collection_timestamp):
    """Eski vmware_host_collector.process_one_host_config_only ile birebir."""
    records = []
    try:
        records.append(extract_host_hardware(host, vcenter_uuid, collection_timestamp, hierarchy))
        records.append(extract_host_runtime(host, vcenter_uuid, collection_timestamp))
        records.extend(extract_host_storage(host, vcenter_uuid, collection_timestamp))
    except Exception as e:
        print(f"Warning: Failed to process host {getattr(host, '_moId', '?')}: {e}", file=sys.stderr)
    return host._moId, hierarchy, records


# ---------------------------------------------------------------------------
# VM
# ---------------------------------------------------------------------------
def extract_vm_config(vm, vcenter_uuid, collection_timestamp, hierarchy):
    """Eski vmware_vm_collector.extract_vm_config ile birebir."""
    config = vm.summary.config
    vm_config = vm.config

    record = {
        "data_type": "vmware_vm_config",
        "collection_timestamp": collection_timestamp,
        "vcenter_uuid": vcenter_uuid,
        "datacenter_moid": hierarchy.get('datacenter'),
        "cluster_moid": hierarchy.get('cluster'),
        "host_moid": hierarchy.get('host'),
        "vm_moid": vm._moId,

        "name": safe_get_attr(config, 'name'),
        "template": safe_get_attr(config, 'template'),
        "vm_path_name": safe_get_attr(config, 'vmPathName'),
        "memory_size_mb": safe_get_attr(config, 'memorySizeMB'),
        "cpu_reservation": safe_get_attr(config, 'cpuReservation'),
        "memory_reservation": safe_get_attr(config, 'memoryReservation'),
        "num_cpu": safe_get_attr(config, 'numCpu'),
        "num_ethernet_cards": safe_get_attr(config, 'numEthernetCards'),
        "num_virtual_disks": safe_get_attr(config, 'numVirtualDisks'),
        "uuid": safe_get_attr(config, 'uuid'),
        "instance_uuid": safe_get_attr(config, 'instanceUuid'),
        "guest_id": safe_get_attr(config, 'guestId'),
        "guest_full_name": safe_get_attr(config, 'guestFullName'),
        "annotation": safe_get_attr(config, 'annotation'),

        "change_version": safe_get_attr(vm_config, 'changeVersion'),
        "modified": safe_timestamp(safe_get_attr(vm_config, 'modified')),
        "change_tracking_enabled": safe_get_attr(vm_config, 'changeTrackingEnabled'),
        "firmware": safe_get_attr(vm_config, 'firmware'),
        "max_mks_connections": safe_get_attr(vm_config, 'maxMksConnections'),
        "guest_auto_lock_enabled": safe_get_attr(vm_config, 'guestAutoLockEnabled'),
        "managed_by_extension_key": safe_get_attr(vm_config, 'managedBy.extensionKey'),
        "managed_by_type": safe_get_attr(vm_config, 'managedBy.type'),
        "version": safe_get_attr(vm_config, 'version'),

        "folder_path": get_folder_path(vm),
    }
    return serialize_record(record)


def extract_vm_runtime(vm, vcenter_uuid, collection_timestamp):
    """Eski vmware_vm_collector.extract_vm_runtime ile birebir."""
    runtime = vm.runtime
    guest = vm.guest
    qs = vm.summary.quickStats

    offline_feature_req = None
    if hasattr(runtime, 'offlineFeatureRequirement') and runtime.offlineFeatureRequirement:
        offline_feature_req = json.dumps([str(f) for f in runtime.offlineFeatureRequirement])

    feature_req = None
    if hasattr(runtime, 'featureRequirement') and runtime.featureRequirement:
        feature_req = json.dumps([str(f) for f in runtime.featureRequirement])

    record = {
        "data_type": "vmware_vm_runtime",
        "collection_timestamp": collection_timestamp,
        "vcenter_uuid": vcenter_uuid,
        "vm_moid": vm._moId,

        "power_state": safe_get_attr(runtime, 'powerState'),
        "connection_state": safe_get_attr(runtime, 'connectionState'),
        "boot_time": safe_timestamp(safe_get_attr(runtime, 'bootTime')),
        "suspend_time": safe_timestamp(safe_get_attr(runtime, 'suspendTime')),
        "suspend_interval": safe_get_attr(runtime, 'suspendInterval'),
        "question": str(safe_get_attr(runtime, 'question')) if safe_get_attr(runtime, 'question') else None,
        "memory_overhead": safe_get_attr(runtime, 'memoryOverhead'),
        "max_cpu_usage": safe_get_attr(runtime, 'maxCpuUsage'),
        "max_memory_usage": safe_get_attr(runtime, 'maxMemoryUsage'),
        "num_mks_connections": safe_get_attr(runtime, 'numMksConnections'),
        "record_replay_state": safe_get_attr(runtime, 'recordReplayState'),
        "clean_power_off": safe_get_attr(runtime, 'cleanPowerOff'),
        "need_secondary_reason": safe_get_attr(runtime, 'needSecondaryReason'),
        "online_standby": safe_get_attr(runtime, 'onlineStandby'),
        "min_required_evc_mode_key": safe_get_attr(runtime, 'minRequiredEVCModeKey'),
        "consolidation_needed": safe_get_attr(runtime, 'consolidationNeeded'),
        "offline_feature_requirement": offline_feature_req,
        "feature_requirement": feature_req,

        "guest_tools_status": safe_get_attr(guest, 'toolsStatus'),
        "guest_tools_version": safe_get_attr(guest, 'toolsVersion'),
        "guest_tools_version_status": safe_get_attr(guest, 'toolsVersionStatus'),
        "guest_tools_running_status": safe_get_attr(guest, 'toolsRunningStatus'),
        "guest_tools_version_status2": safe_get_attr(guest, 'toolsVersionStatus2'),
        "guest_guest_id": safe_get_attr(guest, 'guestId'),
        "guest_guest_family": safe_get_attr(guest, 'guestFamily'),
        "guest_guest_full_name": safe_get_attr(guest, 'guestFullName'),
        "guest_host_name": safe_get_attr(guest, 'hostName'),
        "guest_ip_address": safe_get_attr(guest, 'ipAddress'),
        "guest_guest_state": safe_get_attr(guest, 'guestState'),

        "quick_stats_overall_cpu_usage": safe_get_attr(qs, 'overallCpuUsage'),
        "quick_stats_overall_cpu_demand": safe_get_attr(qs, 'overallCpuDemand'),
        "quick_stats_guest_memory_usage": safe_get_attr(qs, 'guestMemoryUsage'),
        "quick_stats_host_memory_usage": safe_get_attr(qs, 'hostMemoryUsage'),
        "quick_stats_guest_heartbeat_status": safe_get_attr(qs, 'guestHeartbeatStatus'),
        "quick_stats_distributed_cpu_entitlement": safe_get_attr(qs, 'distributedCpuEntitlement'),
        "quick_stats_distributed_memory_entitlement": safe_get_attr(qs, 'distributedMemoryEntitlement'),
        "quick_stats_static_cpu_entitlement": safe_get_attr(qs, 'staticCpuEntitlement'),
        "quick_stats_static_memory_entitlement": safe_get_attr(qs, 'staticMemoryEntitlement'),
        "quick_stats_private_memory": safe_get_attr(qs, 'privateMemory'),
        "quick_stats_shared_memory": safe_get_attr(qs, 'sharedMemory'),
        "quick_stats_swapped_memory": safe_get_attr(qs, 'swappedMemory'),
        "quick_stats_ballooned_memory": safe_get_attr(qs, 'balloonedMemory'),
        "quick_stats_consumed_overhead_memory": safe_get_attr(qs, 'consumedOverheadMemory'),
        "quick_stats_ft_log_bandwidth": safe_get_attr(qs, 'ftLogBandwidth'),
        "quick_stats_ft_secondary_latency": safe_get_attr(qs, 'ftSecondaryLatency'),
        "quick_stats_ft_latency_status": safe_get_attr(qs, 'ftLatencyStatus'),
        "quick_stats_compressed_memory": safe_get_attr(qs, 'compressedMemory'),
        "quick_stats_uptime_seconds": safe_get_attr(qs, 'uptimeSeconds'),
        "quick_stats_ssd_swapped_memory": safe_get_attr(qs, 'ssdSwappedMemory'),
    }
    return serialize_record(record)


def extract_vm_storage(vm, vcenter_uuid, collection_timestamp):
    """Eski vmware_vm_collector.extract_vm_storage ile birebir."""
    storage_records = []
    storage = vm.summary.storage

    if not vm.datastore:
        return storage_records

    for ds in vm.datastore:
        record = {
            "data_type": "vmware_vm_storage",
            "collection_timestamp": collection_timestamp,
            "vcenter_uuid": vcenter_uuid,
            "vm_moid": vm._moId,
            "datastore_moid": ds._moId,

            "datastore_name": safe_get_attr(ds, 'name'),
            "datastore_url": safe_get_attr(ds, 'summary.url'),
            "datastore_capacity": safe_get_attr(ds, 'summary.capacity'),
            "datastore_free_space": safe_get_attr(ds, 'summary.freeSpace'),
            "datastore_type": safe_get_attr(ds, 'summary.type'),
            "datastore_accessible": safe_get_attr(ds, 'summary.accessible'),
            "datastore_multiple_host_access": safe_get_attr(ds, 'summary.multipleHostAccess'),

            "committed": safe_get_attr(storage, 'committed'),
            "uncommitted": safe_get_attr(storage, 'uncommitted'),
            "unshared": safe_get_attr(storage, 'unshared'),
        }
        storage_records.append(serialize_record(record))

    return storage_records


def vm_perf_raw_from_query_result(vm_moid, result_item, vcenter_uuid, collection_timestamp,
                                  counter_info_map, start_time, interval_id):
    """Eski vmware_vm_collector.vm_perf_raw_from_query_result ile birebir."""
    perf_raw_records = []
    if not result_item or not result_item.value:
        return perf_raw_records
    for perf_metric in result_item.value:
        counter_id = perf_metric.id.counterId
        instance = perf_metric.id.instance or ''
        counter_info = counter_info_map.get(counter_id) or {
            'name': f'counter_{counter_id}', 'group': 'unknown', 'name_short': 'unknown',
            'rollup': 'unknown', 'stats_type': 'unknown', 'unit_key': 'unknown', 'unit_label': ''}
        if not perf_metric.value:
            continue
        interval_seconds = interval_id
        for i, value in enumerate(perf_metric.value):
            sample_time = start_time + timedelta(seconds=i * interval_seconds)
            record = {
                "data_type": "vmware_vm_perf_raw",
                "collection_timestamp": collection_timestamp,
                "vcenter_uuid": vcenter_uuid,
                "vm_moid": vm_moid,
                "counter_id": counter_id,
                "counter_name": counter_info['name'],
                "counter_group": counter_info['group'],
                "counter_name_short": counter_info['name_short'],
                "counter_rollup_type": counter_info['rollup'],
                "counter_stats_type": counter_info['stats_type'],
                "counter_unit_key": counter_info['unit_key'],
                "counter_unit_label": counter_info['unit_label'],
                "instance": instance,
                "sample_timestamp": sample_time.isoformat(),
                "value": value,
                "interval_id": interval_id,
            }
            perf_raw_records.append(serialize_record(record))
    return perf_raw_records


def calculate_vm_perf_agg(perf_raw_records, vcenter_uuid, collection_timestamp, start_time, end_time):
    """Eski vmware_vm_collector.calculate_vm_perf_agg ile birebir."""
    perf_agg_records = []
    grouped = {}
    for record in perf_raw_records:
        key = (record['counter_id'], record['instance'])
        if key not in grouped:
            grouped[key] = {
                'values': [],
                'counter_info': {
                    'counter_name': record['counter_name'],
                    'counter_group': record['counter_group'],
                    'counter_rollup_type': record['counter_rollup_type'],
                    'counter_unit_key': record['counter_unit_key'],
                },
                'vm_moid': record['vm_moid']
            }
        grouped[key]['values'].append(record['value'])

    for (counter_id, instance), data in grouped.items():
        values = data['values']
        if not values:
            continue
        record = {
            "data_type": "vmware_vm_perf_agg",
            "collection_timestamp": collection_timestamp,
            "vcenter_uuid": vcenter_uuid,
            "vm_moid": data['vm_moid'],

            "window_start": start_time.isoformat(),
            "window_end": end_time.isoformat(),
            "window_duration_seconds": int((end_time - start_time).total_seconds()),
            "sample_count": len(values),

            "counter_id": counter_id,
            "counter_name": data['counter_info']['counter_name'],
            "counter_group": data['counter_info']['counter_group'],
            "counter_rollup_type": data['counter_info']['counter_rollup_type'],
            "counter_unit_key": data['counter_info']['counter_unit_key'],
            "instance": instance,

            "value_avg": sum(values) / len(values),
            "value_min": min(values),
            "value_max": max(values),
            "value_stddev": None,
            "value_first": values[0],
            "value_last": values[-1],
        }
        perf_agg_records.append(serialize_record(record))
    return perf_agg_records


def process_one_vm_config_only(vm, hierarchy, vcenter_uuid, collection_timestamp):
    """Eski vmware_vm_collector.process_one_vm_config_only ile birebir."""
    records = []
    try:
        records.append(extract_vm_config(vm, vcenter_uuid, collection_timestamp, hierarchy))
        records.append(extract_vm_runtime(vm, vcenter_uuid, collection_timestamp))
        records.extend(extract_vm_storage(vm, vcenter_uuid, collection_timestamp))
    except Exception as e:
        print(f"Warning: Failed to process VM {getattr(vm, '_moId', '?')}: {e}", file=sys.stderr)
    return vm._moId, hierarchy, records


# ---------------------------------------------------------------------------
# vCenter collection
# ---------------------------------------------------------------------------
def collect_vcenter(vc_host, cfg):
    """Tek bir vCenter için tüm data_type'ları toplar."""
    si = None
    all_records = []
    try:
        if cfg.timeout > 0:
            socket.setdefaulttimeout(cfg.timeout)

        print(f"vCenter bağlantısı kuruluyor: {vc_host}:{cfg.port} (user={cfg.username})", file=sys.stderr)
        context = ssl._create_unverified_context()
        si = SmartConnect(
            host=vc_host,
            user=cfg.username,
            pwd=cfg.password,
            port=cfg.port,
            sslContext=context,
        )

        content = si.RetrieveContent()
        vcenter_uuid = content.about.instanceUuid
        perf_mgr = content.perfManager

        collection_timestamp = datetime.now(timezone.utc).isoformat()
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(seconds=cfg.perf_window)

        # Counter setleri (host: 6 counter; VM: 6 counter; cluster/datacenter aggregation host stats üzerinden)
        host_desired = COMMON_PERF_COUNTERS + HOST_EXTRA_COUNTERS
        vm_desired = COMMON_PERF_COUNTERS + HOST_EXTRA_COUNTERS

        host_counter_ids, host_counter_info_map, host_scale_map, _ = build_counter_data(perf_mgr, host_desired)
        vm_counter_ids, vm_counter_info_map, vm_scale_map, _ = build_counter_data(perf_mgr, vm_desired)

        host_metric_ids = [vim.PerformanceManager.MetricId(counterId=cid, instance='*') for cid in host_counter_ids]
        vm_metric_ids = [vim.PerformanceManager.MetricId(counterId=cid, instance='*') for cid in vm_counter_ids]

        # Hierarchy walk
        datacenters = []
        for dc in content.rootFolder.childEntity:
            if not hasattr(dc, 'hostFolder'):
                continue
            datacenters.append(dc)

        # Datacenter config (her zaman yayınlanır)
        for dc in datacenters:
            all_records.append(extract_datacenter_config(dc, vcenter_uuid, collection_timestamp))

        # Cluster + host + vm job listeleri
        host_jobs = []   # (host, hierarchy)
        vm_jobs = []     # (vm, hierarchy)
        clusters_by_dc = {}  # dc_moid -> [cluster]

        for dc in datacenters:
            dc_moid = dc._moId
            clusters_by_dc[dc_moid] = []
            for entity in dc.hostFolder.childEntity:
                if not isinstance(entity, vim.ClusterComputeResource):
                    continue
                clusters_by_dc[dc_moid].append(entity)
                cluster_moid = entity._moId

                for host in entity.host:
                    host_hierarchy = {'datacenter': dc_moid, 'cluster': cluster_moid}
                    host_jobs.append((host, host_hierarchy))

                    host_moid = host._moId
                    for vm in host.vm:
                        try:
                            if getattr(vm.config, 'template', False):
                                continue
                        except Exception:
                            continue
                        vm_hierarchy = {
                            'datacenter': dc_moid,
                            'cluster': cluster_moid,
                            'host': host_moid,
                        }
                        vm_jobs.append((vm, vm_hierarchy))
                        if cfg.max_vms > 0 and len(vm_jobs) >= cfg.max_vms:
                            break
                    if cfg.max_vms > 0 and len(vm_jobs) >= cfg.max_vms:
                        break
                    if cfg.max_hosts > 0 and len(host_jobs) >= cfg.max_hosts:
                        break
                if cfg.max_hosts > 0 and len(host_jobs) >= cfg.max_hosts:
                    break

        if cfg.max_hosts > 0:
            print(f"Limiting to first {len(host_jobs)} hosts (--max-hosts={cfg.max_hosts})", file=sys.stderr)
        if cfg.max_vms > 0:
            print(f"Limiting to first {len(vm_jobs)} VMs (--max-vms={cfg.max_vms})", file=sys.stderr)

        print(f"vCenter {vc_host}: {len(datacenters)} DC, "
              f"{sum(len(v) for v in clusters_by_dc.values())} cluster, "
              f"{len(host_jobs)} host, {len(vm_jobs)} vm", file=sys.stderr)

        # ---------- Phase 1a: parallel host config ----------
        host_config_results = []
        if host_jobs:
            with ThreadPoolExecutor(max_workers=cfg.max_workers) as executor:
                futures = [
                    executor.submit(process_one_host_config_only, h, hier, vcenter_uuid, collection_timestamp)
                    for (h, hier) in host_jobs
                ]
                try:
                    completion = as_completed(futures, timeout=cfg.timeout if cfg.timeout > 0 else None)
                    for f in completion:
                        host_config_results.append(f.result())
                except FuturesTimeoutError:
                    print("Timeout reached in host phase 1; outputting partial results.", file=sys.stderr)

        # ---------- Phase 1b: parallel VM config ----------
        vm_config_results = []
        if vm_jobs:
            with ThreadPoolExecutor(max_workers=cfg.max_workers) as executor:
                futures = [
                    executor.submit(process_one_vm_config_only, vm, hier, vcenter_uuid, collection_timestamp)
                    for (vm, hier) in vm_jobs
                ]
                try:
                    completion = as_completed(futures, timeout=cfg.timeout if cfg.timeout > 0 else None)
                    for f in completion:
                        vm_config_results.append(f.result())
                except FuturesTimeoutError:
                    print("Timeout reached in VM phase 1; outputting partial results.", file=sys.stderr)

        # ---------- Phase 2a: batch QueryPerf for hosts ----------
        batch_size = max(1, min(cfg.perf_batch_size, 64))
        hosts = [j[0] for j in host_jobs]
        host_perf_by_moid = {}        # host_moid -> (perf_raw_list, perf_agg_list)
        host_scaled_by_moid = {}      # host_moid -> {counter_id: {avg,min,max}}

        for i in range(0, len(hosts), batch_size):
            batch = hosts[i:i + batch_size]
            specs = [
                vim.PerformanceManager.QuerySpec(
                    entity=h,
                    metricId=host_metric_ids,
                    startTime=start_time,
                    endTime=end_time,
                    intervalId=cfg.perf_interval,
                )
                for h in batch
            ]
            try:
                results = perf_mgr.QueryPerf(querySpec=specs)
                for j, res in enumerate(results):
                    if j >= len(batch):
                        break
                    host_moid = batch[j]._moId
                    perf_raw = host_perf_raw_from_query_result(
                        host_moid, res, vcenter_uuid, collection_timestamp,
                        host_counter_info_map, start_time, cfg.perf_interval,
                    )
                    perf_agg = calculate_host_perf_agg(
                        perf_raw, vcenter_uuid, collection_timestamp, start_time, end_time,
                    )
                    host_perf_by_moid[host_moid] = (perf_raw, perf_agg)
                    host_scaled_by_moid[host_moid] = extract_scaled_stats(res, host_scale_map)
            except Exception as e:
                print(f"Warning: Batch QueryPerf failed for host batch at index {i}: {e}", file=sys.stderr)
                for h in batch:
                    host_perf_by_moid[h._moId] = ([], [])
                    host_scaled_by_moid[h._moId] = {}

        # ---------- Phase 2b: batch QueryPerf for VMs ----------
        vms = [j[0] for j in vm_jobs]
        vm_perf_by_moid = {}

        for i in range(0, len(vms), batch_size):
            batch = vms[i:i + batch_size]
            specs = [
                vim.PerformanceManager.QuerySpec(
                    entity=vm,
                    metricId=vm_metric_ids,
                    startTime=start_time,
                    endTime=end_time,
                    intervalId=cfg.perf_interval,
                )
                for vm in batch
            ]
            try:
                results = perf_mgr.QueryPerf(querySpec=specs)
                for j, res in enumerate(results):
                    if j >= len(batch):
                        break
                    vm_moid = batch[j]._moId
                    perf_raw = vm_perf_raw_from_query_result(
                        vm_moid, res, vcenter_uuid, collection_timestamp,
                        vm_counter_info_map, start_time, cfg.perf_interval,
                    )
                    perf_agg = calculate_vm_perf_agg(
                        perf_raw, vcenter_uuid, collection_timestamp, start_time, end_time,
                    )
                    vm_perf_by_moid[vm_moid] = (perf_raw, perf_agg)
            except Exception as e:
                print(f"Warning: Batch QueryPerf failed for VM batch at index {i}: {e}", file=sys.stderr)
                for vm in batch:
                    vm_perf_by_moid[vm._moId] = ([], [])

        # ---------- Output: host records (config + perf_raw + perf_agg) ----------
        for host_moid, hierarchy, recs in host_config_results:
            all_records.extend(recs)
            raw, agg = host_perf_by_moid.get(host_moid, ([], []))
            all_records.extend(raw)
            all_records.extend(agg)

        # ---------- Output: vm records (config + perf_raw + perf_agg) ----------
        for vm_moid, hierarchy, recs in vm_config_results:
            all_records.extend(recs)
            raw, agg = vm_perf_by_moid.get(vm_moid, ([], []))
            all_records.extend(raw)
            all_records.extend(agg)

        # ---------- Cluster config + cluster_metrics_agg ----------
        for dc in datacenters:
            dc_moid = dc._moId
            for cluster in clusters_by_dc.get(dc_moid, []):
                try:
                    all_records.append(extract_cluster_config(
                        cluster, vcenter_uuid, collection_timestamp, dc_moid
                    ))
                    all_records.append(calculate_cluster_metrics_agg(
                        cluster, vcenter_uuid, dc_moid, collection_timestamp,
                        host_scaled_by_moid, host_scale_map,
                        start_time, end_time,
                    ))
                except Exception as e:
                    print(f"Warning: Cluster {getattr(cluster, '_moId', '?')} aggregation failed: {e}", file=sys.stderr)

        # ---------- Datacenter metrics_agg ----------
        for dc in datacenters:
            try:
                cluster_objs = clusters_by_dc.get(dc._moId, [])
                all_records.append(calculate_datacenter_metrics_agg(
                    dc, vcenter_uuid, collection_timestamp,
                    cluster_objs, host_scaled_by_moid, host_scale_map,
                    start_time, end_time,
                ))
            except Exception as e:
                print(f"Warning: Datacenter {getattr(dc, '_moId', '?')} aggregation failed: {e}", file=sys.stderr)

        return all_records

    finally:
        if si:
            try:
                Disconnect(si)
            except Exception as e:
                print(f"Warning: Disconnect failed for {vc_host}: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    args = parse_args()
    try:
        cfg = load_config(args)
    except Exception as e:
        print(f"ERROR: config loading failed: {e}", file=sys.stderr)
        sys.exit(1)

    if args.print_config_summary:
        print_config_summary(cfg)
        return

    print_config_summary(cfg)
    print(f"Toplam {len(cfg.vcenters)} vCenter işlenecek", file=sys.stderr)

    all_records = []
    for vc in cfg.vcenters:
        try:
            records = collect_vcenter(vc, cfg)
            print(f"vCenter {vc}: {len(records)} record toplandı", file=sys.stderr)
            all_records.extend(records)
        except Exception as e:
            print(f"ERROR: vCenter collection failed for {vc}: {e}", file=sys.stderr)
            continue

    print(f"Toplam {len(all_records)} record stdout'a yazılıyor", file=sys.stderr)
    try:
        print(json.dumps(all_records, ensure_ascii=False, default=str))
    except Exception as e:
        print(f"ERROR: JSON serialization failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
