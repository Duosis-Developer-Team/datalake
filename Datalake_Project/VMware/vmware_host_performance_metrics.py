#!/usr/bin/env python3
"""
Collects ESXi host-level performance metrics from vCenter using pyVmomi.
Processes each cluster and host in parallel threads.
Outputs plain-text metrics in a human-readable format.
Metrics include capacity, counts, 15-minute interval avg/min/max usage per host,
plus system/BIOS UUID, power usage, uptime, and storage capacity.
Uses a static 5-minute sampling period (intervalId=300) and pools samples over the last 15 minutes.
"""

import ssl
import argparse
from datetime import datetime, timedelta
from math import floor
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
from concurrent.futures import ThreadPoolExecutor, as_completed


def parse_args():
    parser = argparse.ArgumentParser(
        description='Collect host metrics from vCenter using pyVmomi.'
    )
    parser.add_argument('--vmware-ip', required=True,
                        help='Comma-separated vCenter hostnames or IPs')
    parser.add_argument('--vmware-port', type=int, default=443,
                        help='vCenter port (default: 443)')
    parser.add_argument('--vmware-username', required=True,
                        help='Username for vCenter authentication')
    parser.add_argument('--vmware-password', required=True,
                        help='Password for vCenter authentication')
    return parser.parse_args()


def round_interval(now=None, interval=15):
    if now is None:
        now = datetime.now()
    slot = floor(now.minute / interval) * interval
    base = now.replace(minute=0, second=0, microsecond=0)
    end = base + timedelta(minutes=slot)
    start = end - timedelta(minutes=interval)
    return start, end


def get_perf_counter_map(perf_mgr, keys):
    cmap = {}
    for pc in perf_mgr.perfCounter:
        full = f"{pc.groupInfo.key}.{pc.nameInfo.key}.{pc.rollupType}"
        if full in keys:
            scale = getattr(pc.unitInfo, 'scale', 1) or 1
            uk = getattr(pc.unitInfo, 'key', '').lower()
            lbl = getattr(pc.unitInfo, 'label', '').lower()
            is_pct = 'percent' in uk or '%' in lbl
            cmap[full] = {'id': pc.key, 'scale': scale, 'percent': is_pct}
    return cmap


def query_metrics(perf_mgr, entity, cmap, start, end, interval_id=300):
    mids = [vim.PerformanceManager.MetricId(counterId=v['id'], instance='*')
            for v in cmap.values()]
    spec = vim.PerformanceManager.QuerySpec(
        entity=entity,
        metricId=mids,
        startTime=start,
        endTime=end,
        intervalId=interval_id
    )
    try:
        results = perf_mgr.QueryPerf(querySpec=[spec])
    except vmodl.fault.InvalidArgument as e:
        raise RuntimeError(f"QueryPerf invalid argument: {e.faultMessage}")
    samples = {}
    if results:
        for m in results[0].value:
            cid = m.id.counterId
            vals = m.value or []
            samples.setdefault(cid, []).extend(vals)
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
            avg /= 100.0; mn /= 100.0; mx /= 100.0
        stats[cid] = {'avg': avg, 'min': mn, 'max': mx}
    return stats


def process_host(dc_name, cl_name, host, perf_mgr, cmap, start, end, interval):
    # UUIDs
    system_uuid = getattr(host.config, 'uuid', 'N/A')
    bios_uuid = getattr(host.hardware.systemInfo, 'uuid', 'N/A')
    # Uptime
    boot = host.runtime.bootTime
    uptime = boot.strftime('%m/%d/%Y %H:%M:%S') if boot else 'N/A'

    hw = host.summary.hardware
    qs = host.summary.quickStats
    cpu_cap = (hw.numCpuCores * hw.cpuMhz) / 1000.0
    cpu_used = (qs.overallCpuUsage or 0) / 1000.0
    cpu_free = cpu_cap - cpu_used
    mem_cap = hw.memorySize / (1024**3)
    mem_used = (qs.overallMemoryUsage or 0) / 1024.0
    mem_free = mem_cap - mem_used

    # Storage per host
    ds_list = getattr(host, 'datastore', [])
    total_str_cap = sum(ds.summary.capacity for ds in ds_list) / (1024**3)
    total_str_free = sum(ds.summary.freeSpace for ds in ds_list) / (1024**3)

    stats = query_metrics(perf_mgr, host, cmap, start, end, interval)
    # Disk I/O
    rid = cmap['disk.read.average']['id']; wid = cmap['disk.write.average']['id']
    disk_avg = stats[rid]['avg'] + stats[wid]['avg'] if rid in stats and wid in stats else 0.0
    disk_min = stats[rid]['min'] + stats[wid]['min'] if rid in stats and wid in stats else 0.0
    disk_max = stats[rid]['max'] + stats[wid]['max'] if rid in stats and wid in stats else 0.0
    # Network
    nid = cmap['net.usage.average']['id']
    net = stats.get(nid, {'avg':0.0,'min':0.0,'max':0.0})
    # Power
    pid = cmap.get('power.power.average', {}).get('id')
    power = stats.get(pid, {'avg':0.0})['avg'] if pid else 'N/A'
    # Percentages
    mid = cmap['mem.usage.average']['id']
    mem_pct = stats[mid] if mid in stats else {'avg':0.0,'min':0.0,'max':0.0}
    cid = cmap['cpu.usage.average']['id']
    cpu_pct = stats[cid] if cid in stats else {'avg':0.0,'min':0.0,'max':0.0}

    out = []
    out.append(f"Datacenter: {dc_name}")
    out.append(f"Cluster: {cl_name}")
    out.append(f"VMHost: {host.name}")
    out.append(f"Timestamp: {start.strftime('%Y-%m-%d %H:%M')}")
    out.append(f"ESXi System UUID: {system_uuid}")
    out.append(f"ESXi BIOS UUID: {bios_uuid}")
    out.append(f"CPU GHz Capacity: {round(cpu_cap,2)}")
    out.append(f"CPU GHz Used: {round(cpu_used,2)}")
    out.append(f"CPU GHz Free: {round(cpu_free,2)}")
    out.append(f"Memory Capacity GB: {round(mem_cap,2)}")
    out.append(f"Memory Used GB: {round(mem_used,2)}")
    out.append(f"Memory Free GB: {round(mem_free,2)}")
    out.append(f"Disk Usage Avg KBps: {round(disk_avg,2)}")
    out.append(f"Disk Usage Min KBps: {round(disk_min,2)}")
    out.append(f"Disk Usage Max KBps: {round(disk_max,2)}")
    out.append(f"Network Usage Avg KBps: {round(net['avg'],2)}")
    out.append(f"Network Usage Min KBps: {round(net['min'],2)}")
    out.append(f"Network Usage Max KBps: {round(net['max'],2)}")
    out.append(f"Memory Usage Avg perc: {mem_pct['avg']}")
    out.append(f"Memory Usage Min perc: {mem_pct['min']}")
    out.append(f"Memory Usage Max perc: {mem_pct['max']}")
    out.append(f"CPU Usage Avg perc: {cpu_pct['avg']}")
    out.append(f"CPU Usage Min perc: {cpu_pct['min']}")
    out.append(f"CPU Usage Max perc: {cpu_pct['max']}")
    out.append(f"Total CapacityGB: {round(total_str_cap,2)}")
    out.append(f"Total FreeSpaceGB: {round(total_str_free,2)}")
    out.append(f"Power Usage: {power}")
    out.append(f"Uptime: {uptime}")
    return "\n".join(out) + "\n"


def main():
    args = parse_args()
    servers = list(dict.fromkeys([h.strip() for h in args.vmware_ip.split(',')]))
    port = args.vmware_port
    user = args.vmware_username
    pwd = args.vmware_password

    start, end = round_interval()
    interval = 300
    desired = [
        'cpu.usage.average', 'mem.usage.average',
        'disk.read.average', 'disk.write.average',
        'net.usage.average', 'power.power.average'
    ]

    service_instances = []
    with ThreadPoolExecutor() as executor:
        futures = []
        for vc in servers:
            si = SmartConnect(host=vc, user=user, pwd=pwd, port=port,
                              sslContext=ssl._create_unverified_context())
            service_instances.append(si)
            content = si.RetrieveContent()
            perf_mgr = content.perfManager
            cmap = get_perf_counter_map(perf_mgr, desired)
            for dc in content.rootFolder.childEntity:
                if not hasattr(dc, 'hostFolder'):
                    continue
                for cl in [c for c in dc.hostFolder.childEntity
                           if isinstance(c, vim.ClusterComputeResource)]:
                    for host in cl.host:
                        futures.append(
                            executor.submit(
                                process_host,
                                dc.name, cl.name,
                                host, perf_mgr, cmap,
                                start, end, interval
                            )
                        )
        for f in as_completed(futures):
            print(f.result())
    for si in service_instances:
        Disconnect(si)


if __name__ == '__main__':
    main()
