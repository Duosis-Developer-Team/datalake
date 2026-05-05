#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VMware Unified Performance Metrics Collector

4 eski VMware performance_metrics scriptini (datacenter/cluster/host/vm) tek
dosyada birleştirir. configuration_file.json'dan VmWare bilgilerini okur,
listedeki her vCenter'a bağlanır ve toplanan metrikleri JSON array (default)
veya plain-text (eski format) olarak stdout'a basar.

Üretilen 4 data_type:
- vmware_datacenter_performance_metrics
- vmware_cluster_performance_metrics
- vmware_host_performance_metrics
- vmware_vm_performance_metrics

Hesaplamalar, field/label isimleri (büyük-küçük harf ve boşluklar dahil),
unit conversion mantığı, sampling penceresi (15 dk / 300 sn) eski 4 script
ile birebir korunur. "total storage capacity gb" gibi label'larda eski unit
tutarsızlıkları (örn. *1024 ile MB döndüren "gb" alanı) bilerek korunur.

Output: stdout = JSON array (veya text). stderr = log/uyarı.
"""

import json
import ssl
import socket
import argparse
import sys
import os
from datetime import datetime, timezone, timedelta
from math import floor
from concurrent.futures import ThreadPoolExecutor, as_completed

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl


# ---------------------------------------------------------------------------
# Config path search (NetBackup collector ile aynı mantık)
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
COMMON_COUNTERS = [
    'cpu.usage.average',
    'mem.usage.average',
    'disk.read.average',
    'disk.write.average',
    'net.usage.average',
]

HOST_COUNTERS = COMMON_COUNTERS + [
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
        self.output_format = 'json'
        self.config_path_used = None


def parse_args():
    parser = argparse.ArgumentParser(
        description='VMware Unified Performance Metrics Collector (config-driven)'
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
    parser.add_argument('--output-format', choices=['json', 'text'], default='json',
                        help='Output format: json (default) veya text (eski plain-text)')
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
    cfg.output_format = args.output_format

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

    # vCenter listesi (CLI override > config), duplicate-free, sırayı koru
    if args.vmware_ip:
        raw_vcenters = split_csv(args.vmware_ip)
    else:
        raw_vcenters = split_csv(file_data.get('VMwareIP'))
    seen = set()
    cfg.vcenters = [v for v in raw_vcenters if not (v in seen or seen.add(v))]

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
    print(f"output_format={cfg.output_format}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Eski 4 scriptten birebir taşınan helper'lar
# ---------------------------------------------------------------------------
def round_interval(now=None, interval=15):
    """15dk pencere mantığı (eski scriptlerle birebir aynı)."""
    if now is None:
        now = datetime.now()
    mins = floor(now.minute / interval) * interval
    base = now.replace(minute=0, second=0, microsecond=0)
    end = base + timedelta(minutes=mins)
    start = end - timedelta(minutes=interval)
    return start, end


def get_perf_counter_map(perf_mgr, keys):
    """Counter map (full_name -> {id, scale, percent})."""
    cmap = {}
    for pc in perf_mgr.perfCounter:
        full = f"{pc.groupInfo.key}.{pc.nameInfo.key}.{pc.rollupType}"
        if full in keys:
            scale = getattr(pc.unitInfo, 'scale', 1) or 1
            uk = getattr(pc.unitInfo, 'key', '') or ''
            lbl = getattr(pc.unitInfo, 'label', '') or ''
            is_pct = 'percent' in uk.lower() or '%' in lbl.lower()
            cmap[full] = {'id': pc.key, 'scale': scale, 'percent': is_pct}
    return cmap


def query_metrics(perf_mgr, entity, cmap, start, end, interval_id=300, mids=None):
    """
    Eski scriptlerle birebir uyumlu QueryPerf + scaled stats.
    Returns: {counter_id: {'avg':, 'min':, 'max':}}
    """
    if mids is None:
        mids = [vim.PerformanceManager.MetricId(counterId=v['id'], instance='*')
                for v in cmap.values()]
    spec = vim.PerformanceManager.QuerySpec(
        entity=entity,
        metricId=mids,
        startTime=start,
        endTime=end,
        intervalId=interval_id,
    )
    try:
        results = perf_mgr.QueryPerf(querySpec=[spec])
    except vmodl.fault.InvalidArgument as e:
        raise RuntimeError(f"QueryPerf invalid argument: {e}")
    samples = {}
    if results:
        for m in results[0].value:
            cid = m.id.counterId
            samples.setdefault(cid, []).extend(m.value or [])
    stats = {}
    for cid, vals in samples.items():
        if not vals:
            continue
        info = next(v for v in cmap.values() if v['id'] == cid)
        scale = info['scale']
        raw_avg = sum(vals) / len(vals)
        raw_min = min(vals)
        raw_max = max(vals)
        avg = raw_avg / scale
        mn = raw_min / scale
        mx = raw_max / scale
        if info['percent']:
            avg /= 100.0
            mn /= 100.0
            mx /= 100.0
        stats[cid] = {'avg': avg, 'min': mn, 'max': mx}
    return stats


def get_vcenter_identifier(content, vc, use_socket_fallback=False):
    """Eski scriptlerle birebir aynı identifier mantığı."""
    try:
        opts = {
            opt.key: opt.value
            for opt in content.setting.QueryOptions()
            if opt.key in ('config.vpxd.hostnameUrl', 'VirtualCenter.FQDN')
        }
        ident = opts.get('config.vpxd.hostnameUrl') or opts.get('VirtualCenter.FQDN')
        if ident:
            return ident
    except Exception:
        pass
    if use_socket_fallback:
        try:
            return socket.getfqdn(vc)
        except Exception:
            return vc
    return vc


# ---------------------------------------------------------------------------
# Datacenter performance metrics (eski vmware_datacenter_performance_metrics.py)
# ---------------------------------------------------------------------------
def collect_datacenter_metrics(content, identifier, perf_mgr, cmap, start, end, interval):
    """
    Eski datacenter performance script'inin hesabı bire bir.
    Tek bir record üretir (vCenter genelinde aggregate).
    """
    tmem_cap = tmem_used = 0.0
    tstr_cap = tstr_used = 0.0
    tcpu_cap = tcpu_used = 0.0
    davg = dmin = dmax = 0.0
    navg = nmin = nmax = 0.0
    mavg = mmin = mmax = 0.0
    cavg = cmin = cmax = 0.0
    hcount = vcount = ccnt = 0

    for dc in content.rootFolder.childEntity:
        if not hasattr(dc, 'hostFolder'):
            continue
        clusters = [c for c in dc.hostFolder.childEntity
                    if isinstance(c, vim.ClusterComputeResource)]
        ccnt += len(clusters)
        hosts_list, vms_list = [], []
        for cl in clusters:
            hosts_list.extend(cl.host)
            for h in cl.host:
                for vm in h.vm:
                    if not getattr(vm.config, 'template', False):
                        vms_list.append(vm)
        hcount += len(hosts_list)
        vcount += len(vms_list)

        for ds in dc.datastore:
            cap = ds.summary.capacity / (1024 ** 3)
            free = ds.summary.freeSpace / (1024 ** 3)
            tstr_cap += cap
            tstr_used += cap - free

        for h in hosts_list:
            hw = h.summary.hardware
            qs = h.summary.quickStats
            tcpu_cap += hw.numCpuCores * hw.cpuMhz / 1000.0
            tcpu_used += (qs.overallCpuUsage or 0) / 1000.0
            tmem_cap += hw.memorySize / (1024 ** 3)
            tmem_used += (qs.overallMemoryUsage or 0) / 1024.0

            try:
                stats = query_metrics(perf_mgr, h, cmap, start, end, interval)
            except Exception as e:
                print(f"Warning: DC perf query failed for host {h._moId}: {e}", file=sys.stderr)
                stats = {}

            rid = cmap['disk.read.average']['id']
            wid = cmap['disk.write.average']['id']
            if rid in stats and wid in stats:
                davg += stats[rid]['avg'] + stats[wid]['avg']
                dmin += stats[rid]['min'] + stats[wid]['min']
                dmax += stats[rid]['max'] + stats[wid]['max']
            nid = cmap['net.usage.average']['id']
            if nid in stats:
                navg += stats[nid]['avg']; nmin += stats[nid]['min']; nmax += stats[nid]['max']
            mid = cmap['mem.usage.average']['id']
            if mid in stats:
                mavg += stats[mid]['avg']; mmin += stats[mid]['min']; mmax += stats[mid]['max']
            cid = cmap['cpu.usage.average']['id']
            if cid in stats:
                cavg += stats[cid]['avg']; cmin += stats[cid]['min']; cmax += stats[cid]['max']

    if hcount:
        mavg /= hcount; mmin /= hcount; mmax /= hcount
        cavg /= hcount; cmin /= hcount; cmax /= hcount

    # JSON snake_case (Avro/NiFi/PostgreSQL uyumlu); text mode eski label'larla
    record = {
        "data_type": "vmware_datacenter_performance_metrics",
        "datacenter": identifier,
        "timestamp": start.strftime('%Y-%m-%d %H:%M'),
        "total_memory_capacity_gb": round(tmem_cap, 2),
        "total_memory_used_gb": round(tmem_used, 2),
        "total_storage_capacity_gb": int(tstr_cap * 1024),  # eski script ile birebir (MB döndürür ama label "gb")
        "total_used_storage_gb": int(tstr_used * 1024),     # aynısı
        "total_cpu_ghz_capacity": round(tcpu_cap, 2),
        "total_cpu_ghz_used": round(tcpu_used, 2),
        "disk_usage_avg_kbps": round(davg, 2),
        "disk_usage_min_kbps": round(dmin, 2),
        "disk_usage_max_kbps": round(dmax, 2),
        "network_usage_avg_kbps": round(navg, 2),
        "network_usage_min_kbps": round(nmin, 2),
        "network_usage_max_kbps": round(nmax, 2),
        "memory_usage_avg_perc": mavg,
        "memory_usage_min_perc": mmin,
        "memory_usage_max_perc": mmax,
        "cpu_usage_avg_perc": cavg,
        "cpu_usage_min_perc": cmin,
        "cpu_usage_max_perc": cmax,
        "total_host_count": hcount,
        "total_vm_count": vcount,
        "total_cluster_count": ccnt,
    }
    return record


def datacenter_record_to_text(rec):
    """Eski datacenter scripti formatında plain-text blok üret (eski label'larla)."""
    lines = [
        f"datacenter: {rec['datacenter']}",
        f"timestamp: {rec['timestamp']}",
        f"total memory capacity gb: {rec['total_memory_capacity_gb']}",
        f"total memory used gb: {rec['total_memory_used_gb']}",
        f"total storage capacity gb: {rec['total_storage_capacity_gb']}",
        f"total used storage gb: {rec['total_used_storage_gb']}",
        f"total cpu ghz capacity: {rec['total_cpu_ghz_capacity']}",
        f"total cpu ghz used: {rec['total_cpu_ghz_used']}",
        f"disk usage avg kbps: {rec['disk_usage_avg_kbps']}",
        f"disk usage min kbps: {rec['disk_usage_min_kbps']}",
        f"disk usage max kbps: {rec['disk_usage_max_kbps']}",
        f"network usage avg kbps: {rec['network_usage_avg_kbps']}",
        f"network usage min kbps: {rec['network_usage_min_kbps']}",
        f"network usage max kbps: {rec['network_usage_max_kbps']}",
        f"memory usage avg perc: {rec['memory_usage_avg_perc']}",
        f"memory usage min perc: {rec['memory_usage_min_perc']}",
        f"memory usage max perc: {rec['memory_usage_max_perc']}",
        f"cpu usage avg perc: {rec['cpu_usage_avg_perc']}",
        f"cpu usage min perc: {rec['cpu_usage_min_perc']}",
        f"cpu usage max perc: {rec['cpu_usage_max_perc']}",
        f"total host count: {rec['total_host_count']}",
        f"total vm count: {rec['total_vm_count']}",
        f"total cluster count: {rec['total_cluster_count']}",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Cluster performance metrics (eski vmware_cluster_performance_metrics.py)
# ---------------------------------------------------------------------------
def collect_cluster_metrics(identifier, cl, perf_mgr, cmap, start, end, interval):
    """Eski cluster performance script ile birebir hesap ve label."""
    tmem_cap = tmem_used = 0.0
    tstr_cap = tstr_used = 0.0
    tcpu_cap = tcpu_used = 0.0
    davg = dmin = dmax = 0.0
    navg = nmin = nmax = 0.0
    mavg = mmin = mmax = 0.0
    cavg = cmin = cmax = 0.0

    hosts = cl.host
    hcount = len(hosts)
    vcount = sum(
        len([vm for vm in h.vm if not getattr(vm.config, 'template', False)])
        for h in hosts
    )

    for ds in cl.datastore:
        cap_gb = ds.summary.capacity / (1024 ** 3)
        free_gb = ds.summary.freeSpace / (1024 ** 3)
        tstr_cap += cap_gb
        tstr_used += (cap_gb - free_gb)

    for h in hosts:
        hw = h.summary.hardware
        qs = h.summary.quickStats
        cpu_cap = (hw.numCpuCores * hw.cpuMhz) / 1000.0
        cpu_used = (qs.overallCpuUsage or 0) / 1000.0
        mem_cap = hw.memorySize / (1024 ** 3)
        mem_used = (qs.overallMemoryUsage or 0) / 1024.0

        tcpu_cap += cpu_cap; tcpu_used += cpu_used
        tmem_cap += mem_cap; tmem_used += mem_used

        try:
            stats = query_metrics(perf_mgr, h, cmap, start, end, interval)
        except Exception as e:
            print(f"Warning: Cluster perf query failed for host {h._moId}: {e}", file=sys.stderr)
            stats = {}

        rid = cmap['disk.read.average']['id']
        wid = cmap['disk.write.average']['id']
        if rid in stats and wid in stats:
            davg += stats[rid]['avg'] + stats[wid]['avg']
            dmin += stats[rid]['min'] + stats[wid]['min']
            dmax += stats[rid]['max'] + stats[wid]['max']
        nid = cmap['net.usage.average']['id']
        if nid in stats:
            navg += stats[nid]['avg']; nmin += stats[nid]['min']; nmax += stats[nid]['max']
        mid = cmap['mem.usage.average']['id']
        if mid in stats:
            mavg += stats[mid]['avg']; mmin += stats[mid]['min']; mmax += stats[mid]['max']
        cid = cmap['cpu.usage.average']['id']
        if cid in stats:
            cavg += stats[cid]['avg']; cmin += stats[cid]['min']; cmax += stats[cid]['max']

    if hcount:
        mavg /= hcount; mmin /= hcount; mmax /= hcount
        cavg /= hcount; cmin /= hcount; cmax /= hcount

    cpu_free = tcpu_cap - tcpu_used
    mem_free = tmem_cap - tmem_used

    record = {
        "data_type": "vmware_cluster_performance_metrics",
        "datacenter": identifier,
        "cluster": cl.name,
        "timestamp": start.strftime('%Y-%m-%d %H:%M'),
        "vhost_count": hcount,
        "vm_count": vcount,
        "cpu_ghz_capacity": round(tcpu_cap, 2),
        "cpu_ghz_used": round(tcpu_used, 2),
        "cpu_ghz_free": round(cpu_free, 2),
        "memory_capacity_gb": round(tmem_cap, 2),
        "memory_used_gb": round(tmem_used, 2),
        "memory_free_gb": round(mem_free, 2),
        "disk_usage_avg_kbps": round(davg, 2),
        "disk_usage_min_kbps": int(dmin),
        "disk_usage_max_kbps": int(dmax),
        "network_usage_avg_kbps": round(navg, 2),
        "network_usage_min_kbps": int(nmin),
        "network_usage_max_kbps": int(nmax),
        "memory_usage_avg_perc": mavg,
        "memory_usage_min_perc": mmin,
        "memory_usage_max_perc": mmax,
        "cpu_usage_avg_perc": cavg,
        "cpu_usage_min_perc": cmin,
        "cpu_usage_max_perc": cmax,
        "total_freespace_gb": round(tstr_cap - tstr_used, 2),
        "total_capacity_gb": round(tstr_cap, 2),
    }
    return record


def cluster_record_to_text(rec):
    """Eski cluster scripti formatında plain-text blok (eski label'larla)."""
    lines = [
        f"Datacenter: {rec['datacenter']}",
        f"Cluster: {rec['cluster']}",
        f"Timestamp: {rec['timestamp']}",
        f"vHost Count: {rec['vhost_count']}",
        f"VM Count: {rec['vm_count']}",
        f"CPU GHz Capacity: {rec['cpu_ghz_capacity']}",
        f"CPU GHz Used: {rec['cpu_ghz_used']}",
        f"CPU GHz Free: {rec['cpu_ghz_free']}",
        f"Memory Capacity GB: {rec['memory_capacity_gb']}",
        f"Memory Used GB: {rec['memory_used_gb']}",
        f"Memory Free GB: {rec['memory_free_gb']}",
        f"Disk Usage Avg KBps: {rec['disk_usage_avg_kbps']}",
        f"Disk Usage Min KBps: {rec['disk_usage_min_kbps']}",
        f"Disk Usage Max KBps: {rec['disk_usage_max_kbps']}",
        f"Network Usage Avg KBps: {rec['network_usage_avg_kbps']}",
        f"Network Usage Min KBps: {rec['network_usage_min_kbps']}",
        f"Network Usage Max KBps: {rec['network_usage_max_kbps']}",
        f"Memory Usage Avg perc: {rec['memory_usage_avg_perc']}",
        f"Memory Usage Min perc: {rec['memory_usage_min_perc']}",
        f"Memory Usage Max perc: {rec['memory_usage_max_perc']}",
        f"CPU Usage Avg perc: {rec['cpu_usage_avg_perc']}",
        f"CPU Usage Min perc: {rec['cpu_usage_min_perc']}",
        f"CPU Usage Max perc: {rec['cpu_usage_max_perc']}",
        f"Total FreeSpace GB: {rec['total_freespace_gb']}",
        f"Total Capacity GB: {rec['total_capacity_gb']}",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Host performance metrics (eski vmware_host_performance_metrics.py)
# ---------------------------------------------------------------------------
def collect_host_metrics(identifier, cl_name, host, perf_mgr, cmap, start, end, interval):
    """Eski host performance script ile birebir hesap ve label."""
    system_uuid = getattr(host.config, 'uuid', 'N/A') if getattr(host, 'config', None) else 'N/A'
    bios_uuid = getattr(host.hardware.systemInfo, 'uuid', 'N/A') if getattr(host, 'hardware', None) else 'N/A'

    boot = getattr(host.runtime, 'bootTime', None) if getattr(host, 'runtime', None) else None
    uptime = boot.strftime('%m/%d/%Y %H:%M:%S') if boot else 'N/A'

    hw = host.summary.hardware
    qs = host.summary.quickStats
    cpu_cap = (hw.numCpuCores * hw.cpuMhz) / 1000.0
    cpu_used = (qs.overallCpuUsage or 0) / 1000.0
    cpu_free = cpu_cap - cpu_used
    mem_cap = hw.memorySize / (1024 ** 3)
    mem_used = (qs.overallMemoryUsage or 0) / 1024.0
    mem_free = mem_cap - mem_used

    ds_list = getattr(host, 'datastore', []) or []
    total_str_cap = sum(ds.summary.capacity for ds in ds_list) / (1024 ** 3)
    total_str_free = sum(ds.summary.freeSpace for ds in ds_list) / (1024 ** 3)

    try:
        stats = query_metrics(perf_mgr, host, cmap, start, end, interval)
    except Exception as e:
        print(f"Warning: Host perf query failed for {host._moId}: {e}", file=sys.stderr)
        stats = {}

    rid = cmap['disk.read.average']['id']
    wid = cmap['disk.write.average']['id']
    disk_avg = stats.get(rid, {'avg': 0})['avg'] + stats.get(wid, {'avg': 0})['avg']
    disk_min = stats.get(rid, {'min': 0})['min'] + stats.get(wid, {'min': 0})['min']
    disk_max = stats.get(rid, {'max': 0})['max'] + stats.get(wid, {'max': 0})['max']

    nid = cmap['net.usage.average']['id']
    net = stats.get(nid, {'avg': 0, 'min': 0, 'max': 0})

    pid = cmap.get('power.power.average', {}).get('id')
    power = stats.get(pid, {'avg': 0})['avg'] if pid else 'N/A'

    mem_pct = stats.get(cmap['mem.usage.average']['id'], {'avg': 0, 'min': 0, 'max': 0})
    cpu_pct = stats.get(cmap['cpu.usage.average']['id'], {'avg': 0, 'min': 0, 'max': 0})

    record = {
        "data_type": "vmware_host_performance_metrics",
        "datacenter": identifier,
        "cluster": cl_name,
        "vmhost": host.name,
        "timestamp": start.strftime('%Y-%m-%d %H:%M'),
        "esxi_system_uuid": system_uuid,
        "esxi_bios_uuid": bios_uuid,
        "cpu_ghz_capacity": round(cpu_cap, 2),
        "cpu_ghz_used": round(cpu_used, 2),
        "cpu_ghz_free": round(cpu_free, 2),
        "memory_capacity_gb": round(mem_cap, 2),
        "memory_used_gb": round(mem_used, 2),
        "memory_free_gb": round(mem_free, 2),
        "disk_usage_avg_kbps": round(disk_avg, 2),
        "disk_usage_min_kbps": round(disk_min, 2),
        "disk_usage_max_kbps": round(disk_max, 2),
        "network_usage_avg_kbps": round(net['avg'], 2),
        "network_usage_min_kbps": round(net['min'], 2),
        "network_usage_max_kbps": round(net['max'], 2),
        "memory_usage_avg_perc": mem_pct['avg'],
        "memory_usage_min_perc": mem_pct['min'],
        "memory_usage_max_perc": mem_pct['max'],
        "cpu_usage_avg_perc": cpu_pct['avg'],
        "cpu_usage_min_perc": cpu_pct['min'],
        "cpu_usage_max_perc": cpu_pct['max'],
        "total_capacity_gb": round(total_str_cap, 2),
        "total_freespace_gb": round(total_str_free, 2),
        "power_usage": power,
        "uptime": uptime,
    }
    return record


def host_record_to_text(rec):
    """Eski host scripti formatında plain-text blok (eski label'larla)."""
    lines = [
        f"Datacenter: {rec['datacenter']}",
        f"Cluster:    {rec['cluster']}",
        f"VMHost:     {rec['vmhost']}",
        f"Timestamp:  {rec['timestamp']}",
        f"ESXi System UUID: {rec['esxi_system_uuid']}",
        f"ESXi BIOS UUID:   {rec['esxi_bios_uuid']}",
        f"CPU GHz Capacity: {rec['cpu_ghz_capacity']}",
        f"CPU GHz Used:     {rec['cpu_ghz_used']}",
        f"CPU GHz Free:     {rec['cpu_ghz_free']}",
        f"Memory Capacity GB: {rec['memory_capacity_gb']}",
        f"Memory Used GB:     {rec['memory_used_gb']}",
        f"Memory Free GB:     {rec['memory_free_gb']}",
        f"Disk Usage Avg KBps: {rec['disk_usage_avg_kbps']}",
        f"Disk Usage Min KBps: {rec['disk_usage_min_kbps']}",
        f"Disk Usage Max KBps: {rec['disk_usage_max_kbps']}",
        f"Network Usage Avg KBps: {rec['network_usage_avg_kbps']}",
        f"Network Usage Min KBps: {rec['network_usage_min_kbps']}",
        f"Network Usage Max KBps: {rec['network_usage_max_kbps']}",
        f"Memory Usage Avg perc: {rec['memory_usage_avg_perc']}",
        f"Memory Usage Min perc: {rec['memory_usage_min_perc']}",
        f"Memory Usage Max perc: {rec['memory_usage_max_perc']}",
        f"CPU Usage Avg perc:    {rec['cpu_usage_avg_perc']}",
        f"CPU Usage Min perc:    {rec['cpu_usage_min_perc']}",
        f"CPU Usage Max perc:    {rec['cpu_usage_max_perc']}",
        f"Total CapacityGB:      {rec['total_capacity_gb']}",
        f"Total FreeSpaceGB:     {rec['total_freespace_gb']}",
        f"Power Usage:            {rec['power_usage']}",
        f"Uptime:                 {rec['uptime']}",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# VM performance metrics (eski vmware_vm_performance_metrics.py)
# ---------------------------------------------------------------------------
def collect_vm_metrics(dc_name, cluster_name, host_name, host_uuid, vm,
                       perf_mgr, cmap, mids, start, end, interval):
    """Eski VM performance script ile birebir hesap ve label."""
    num_cpus = vm.summary.config.numCpu
    esxi_system_uuid = host_uuid
    total_cpu_capacity_mhz = 0  # eski script ile aynı, hardcoded 0
    memory_size_mb = getattr(vm.summary.config, 'memorySizeMB', 0) or 0
    total_mem_capacity_gb = memory_size_mb / 1024.0

    vm_name = vm.summary.config.name
    guest_os = vm.summary.config.guestFullName or ''

    committed = getattr(vm.summary.storage, 'committed', 0) or 0
    uncommitted = getattr(vm.summary.storage, 'uncommitted', 0) or 0
    used_space_gb = committed / (1024 ** 3)
    prov_space_gb = (committed + uncommitted) / (1024 ** 3)
    ds_names = [ds.info.name for ds in vm.datastore] if vm.datastore else []
    ds_list = ",".join(ds_names)

    vmx = vm.summary.config.vmPathName or ''
    try:
        folder = vmx.split(']')[1].rsplit('/', 1)[0].lstrip('/')
    except Exception:
        folder = ''

    moid = getattr(vm, '_moId', '')
    inst_uuid = getattr(vm.config, 'instanceUuid', '') if getattr(vm, 'config', None) else ''
    vm_uuid = f"VirtualMachine-{moid}:{inst_uuid}" if moid and inst_uuid else ''

    boot = getattr(vm.runtime, 'bootTime', None)
    boot_time = boot.strftime('%m/%d/%Y %H:%M:%S') if boot else ''

    try:
        stats = query_metrics(perf_mgr, vm, cmap, start, end, interval, mids=mids)
    except Exception as e:
        print(f"Warning: VM perf query failed for {vm._moId}: {e}", file=sys.stderr)
        stats = {}

    cpu_id = cmap['cpu.usage.average']['id']
    cpu = stats.get(cpu_id, {'avg': 0, 'min': 0, 'max': 0})
    mem_id = cmap['mem.usage.average']['id']
    mem = stats.get(mem_id, {'avg': 0, 'min': 0, 'max': 0})
    rid = cmap['disk.read.average']['id']
    wid = cmap['disk.write.average']['id']
    disk = {'avg': 0, 'min': 0, 'max': 0}
    if rid in stats and wid in stats:
        disk['avg'] = stats[rid]['avg'] + stats[wid]['avg']
        disk['min'] = stats[rid]['min'] + stats[wid]['min']
        disk['max'] = stats[rid]['max'] + stats[wid]['max']

    record = {
        "data_type": "vmware_vm_performance_metrics",
        "datacenter": dc_name,
        "cluster": cluster_name,
        "vmhost": host_name,
        "vmname": vm_name,
        "timestamp": start.strftime('%Y-%m-%d %H:%M'),
        "number_of_cpus": num_cpus,
        "esxi_system_uuid": esxi_system_uuid,
        "total_cpu_capacity_mhz": total_cpu_capacity_mhz,
        "total_memory_capacity_gb": float(f"{total_mem_capacity_gb:.2f}"),
        "cpu_usage_avg_mhz": cpu['avg'],
        "cpu_usage_min_mhz": cpu['min'],
        "cpu_usage_max_mhz": cpu['max'],
        "memory_usage_avg_perc": mem['avg'],
        "memory_usage_min_perc": mem['min'],
        "memory_usage_max_perc": mem['max'],
        "disk_usage_avg_kbps": disk['avg'],
        "disk_usage_min_kbps": disk['min'],
        "disk_usage_max_kbps": disk['max'],
        "guest_os": guest_os,
        "datastore": ds_list,
        "used_space_gb": float(f"{used_space_gb:.2f}"),
        "provisioned_space_gb": float(f"{prov_space_gb:.2f}"),
        "folder": folder,
        "uuid": vm_uuid,
        "boot_time": boot_time,
    }
    return record


def vm_record_to_text(rec):
    """Eski VM scripti formatında plain-text blok (eski label'larla)."""
    lines = [
        f"Datacenter: {rec['datacenter']}",
        f"Cluster: {rec['cluster']}",
        f"VMHost: {rec['vmhost']}",
        f"VMName: {rec['vmname']}",
        f"Timestamp: {rec['timestamp']}",
        f"Number of CPUs: {rec['number_of_cpus']}",
        f"ESXi System UUID: {rec['esxi_system_uuid']}",
        f"Total CPU Capacity Mhz: {rec['total_cpu_capacity_mhz']}",
        f"Total Memory Capacity GB: {rec['total_memory_capacity_gb']:.2f}",
        f"CPU Usage Avg Mhz: {rec['cpu_usage_avg_mhz']}",
        f"CPU Usage Min Mhz: {rec['cpu_usage_min_mhz']}",
        f"CPU Usage Max Mhz: {rec['cpu_usage_max_mhz']}",
        f"Memory Usage Avg perc: {rec['memory_usage_avg_perc']}",
        f"Memory Usage Min perc: {rec['memory_usage_min_perc']}",
        f"Memory Usage Max perc: {rec['memory_usage_max_perc']}",
        f"Disk Usage Avg KBps: {rec['disk_usage_avg_kbps']}",
        f"Disk Usage Min KBps: {rec['disk_usage_min_kbps']}",
        f"Disk Usage Max KBps: {rec['disk_usage_max_kbps']}",
        f"Guest OS: {rec['guest_os']}",
        f"Datastore: {rec['datastore']}",
        f"Used Space GB: {rec['used_space_gb']:.2f}",
        f"Provisioned Space GB: {rec['provisioned_space_gb']:.2f}",
        f"Folder: {rec['folder']}",
        f"UUID: {rec['uuid']}",
        f"BootTime: {rec['boot_time']}",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Per-vCenter orchestration
# ---------------------------------------------------------------------------
def collect_vcenter(vc, cfg, start, end, interval):
    """Tek bir vCenter için 4 data_type'ı toplar."""
    si = None
    records = []
    try:
        print(f"vCenter bağlantısı kuruluyor: {vc}:{cfg.port} (user={cfg.username})", file=sys.stderr)
        si = SmartConnect(
            host=vc, user=cfg.username, pwd=cfg.password,
            port=cfg.port, sslContext=ssl._create_unverified_context()
        )
        content = si.RetrieveContent()
        perf_mgr = content.perfManager

        # Counter map'leri (host için power dahil; cluster/dc/vm için common)
        host_cmap = get_perf_counter_map(perf_mgr, HOST_COUNTERS)
        common_cmap = get_perf_counter_map(perf_mgr, COMMON_COUNTERS)

        # VM tarafı için precomputed metric_ids (eski script ile birebir)
        vm_mids = [vim.PerformanceManager.MetricId(counterId=v['id'], instance='*')
                   for v in common_cmap.values()]

        # Identifier'lar
        # - Datacenter scope: socket fallback'lı (eski datacenter scripti)
        # - Cluster/Host scope: vc fallback'lı (eski cluster/host scriptleri)
        dc_identifier = get_vcenter_identifier(content, vc, use_socket_fallback=True)
        cl_host_identifier = get_vcenter_identifier(content, vc, use_socket_fallback=False)

        # 1) Datacenter performance (vCenter-level aggregate, tek record)
        try:
            dc_rec = collect_datacenter_metrics(
                content, dc_identifier, perf_mgr, common_cmap, start, end, interval
            )
            records.append(dc_rec)
        except Exception as e:
            print(f"Warning: Datacenter metrics failed for {vc}: {e}", file=sys.stderr)

        # Cluster/Host/VM iterasyonu
        cluster_jobs = []  # (cl, identifier, dc_name)
        host_jobs = []     # (identifier, cl_name, host)
        vm_jobs = []       # (dc_name, cl_name, host_name, host_uuid, vm)

        for dc in content.rootFolder.childEntity:
            if not hasattr(dc, 'hostFolder'):
                continue
            for cl in dc.hostFolder.childEntity:
                if not isinstance(cl, vim.ClusterComputeResource):
                    continue
                cluster_jobs.append((cl, cl_host_identifier))
                for host in cl.host:
                    host_jobs.append((cl_host_identifier, cl.name, host))
                    host_uuid = 'N/A'
                    try:
                        host_uuid = getattr(host.hardware.systemInfo, 'uuid', 'N/A')
                    except Exception:
                        pass
                    for vm in host.vm:
                        try:
                            if vm.config.template:
                                continue
                        except Exception:
                            continue
                        vm_jobs.append((dc.name, cl.name, host.name, host_uuid, vm))

        # 2) Cluster performance — paralel
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = [
                ex.submit(collect_cluster_metrics, ident, cl, perf_mgr, common_cmap, start, end, interval)
                for (cl, ident) in cluster_jobs
            ]
            for f in as_completed(futures):
                try:
                    records.append(f.result())
                except Exception as e:
                    print(f"Warning: Cluster metrics task failed: {e}", file=sys.stderr)

        # 3) Host performance — paralel (32 worker, eski script ile aynı)
        with ThreadPoolExecutor(max_workers=32) as ex:
            futures = [
                ex.submit(collect_host_metrics, ident, cl_name, host, perf_mgr, host_cmap, start, end, interval)
                for (ident, cl_name, host) in host_jobs
            ]
            for f in as_completed(futures):
                try:
                    records.append(f.result())
                except Exception as e:
                    print(f"Warning: Host metrics task failed: {e}", file=sys.stderr)

        # 4) VM performance — paralel (32 worker, eski script ile aynı)
        with ThreadPoolExecutor(max_workers=32) as ex:
            futures = [
                ex.submit(collect_vm_metrics,
                          dc_name, cl_name, host_name, host_uuid, vm,
                          perf_mgr, common_cmap, vm_mids, start, end, interval)
                for (dc_name, cl_name, host_name, host_uuid, vm) in vm_jobs
            ]
            for f in as_completed(futures):
                try:
                    records.append(f.result())
                except Exception as e:
                    print(f"Warning: VM metrics task failed: {e}", file=sys.stderr)

        print(f"vCenter {vc}: {len(records)} record toplandı", file=sys.stderr)
        return records

    finally:
        if si:
            try:
                Disconnect(si)
            except Exception as e:
                print(f"Warning: Disconnect failed for {vc}: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------
def emit_json(all_records):
    print(json.dumps(all_records, ensure_ascii=False, default=str))


def emit_text(all_records):
    """data_type'a göre eski scriptlerin plain-text format'ında basar."""
    for rec in all_records:
        dt = rec.get('data_type')
        if dt == 'vmware_datacenter_performance_metrics':
            sys.stdout.write(datacenter_record_to_text(rec) + "\n")
        elif dt == 'vmware_cluster_performance_metrics':
            sys.stdout.write(cluster_record_to_text(rec) + "\n")
        elif dt == 'vmware_host_performance_metrics':
            sys.stdout.write(host_record_to_text(rec) + "\n")
        elif dt == 'vmware_vm_performance_metrics':
            sys.stdout.write(vm_record_to_text(rec) + "\n")


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

    start, end = round_interval()
    interval = 300

    all_records = []
    for vc in cfg.vcenters:
        try:
            records = collect_vcenter(vc, cfg, start, end, interval)
            all_records.extend(records)
        except Exception as e:
            print(f"ERROR: vCenter collection failed for {vc}: {e}", file=sys.stderr)
            continue

    print(f"Toplam {len(all_records)} record stdout'a yazılıyor (format={cfg.output_format})", file=sys.stderr)
    try:
        if cfg.output_format == 'text':
            emit_text(all_records)
        else:
            emit_json(all_records)
    except Exception as e:
        print(f"ERROR: output write failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
