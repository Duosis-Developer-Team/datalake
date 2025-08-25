#!/usr/bin/env python3
"""
Collects cluster-level performance metrics from vCenter using pyVmomi.
Processes each cluster in parallel threads.
Outputs plain-text metrics in a human-readable format.
Metrics include capacity, counts, 15-minute interval avg/min/max usage values,
plus computed free values and storage totals.
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
        description='Collect cluster metrics from vCenter using pyVmomi.'
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
    mins = floor(now.minute / interval) * interval
    base = now.replace(minute=0, second=0, microsecond=0)
    end = base + timedelta(minutes=mins)
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
    mids = [vim.PerformanceManager.MetricId(counterId=v['id'], instance='*') for v in cmap.values()]
    spec = vim.PerformanceManager.QuerySpec(
        entity=entity, metricId=mids,
        startTime=start, endTime=end,
        intervalId=interval_id
    )
    try:
        res = perf_mgr.QueryPerf(querySpec=[spec])
    except vmodl.fault.InvalidArgument as e:
        raise RuntimeError(f"QueryPerf invalid argument: {e}")
    samples = {}
    if res:
        for val in res[0].value:
            cid = val.id.counterId
            samples.setdefault(cid, []).extend(val.value or [])
    stats = {}
    for cid, vals in samples.items():
        if not vals:
            continue
        info = next(v for v in cmap.values() if v['id'] == cid)
        raw_avg = sum(vals) / len(vals)
        raw_min = min(vals); raw_max = max(vals)
        avg = raw_avg / info['scale']; mn = raw_min / info['scale']; mx = raw_max / info['scale']
        if info['percent']:
            avg /= 100.0; mn /= 100.0; mx /= 100.0
        stats[cid] = {'avg': avg, 'min': mn, 'max': mx}
    return stats


def process_cluster(identifier, cl, perf_mgr, cmap, start, end, interval):
    # Accumulators
    tmem_cap = tmem_used = 0.0
    tstr_cap = tstr_used = 0.0
    tcpu_cap = tcpu_used = 0.0
    davg = dmin = dmax = 0.0
    navg = nmin = nmax = 0.0
    mavg = mmin = mmax = 0.0
    cavg = cmin = cmax = 0.0

    hosts = cl.host
    hcount = len(hosts)
    vcount = sum(len([vm for vm in h.vm if not getattr(vm.config, 'template', False)]) for h in hosts)

    # Storage sums
    for ds in cl.datastore:
        cap_gb = ds.summary.capacity / (1024**3)
        free_gb = ds.summary.freeSpace / (1024**3)
        tstr_cap += cap_gb
        tstr_used += (cap_gb - free_gb)

    # Host metrics
    for h in hosts:
        hw = h.summary.hardware
        qs = h.summary.quickStats
        cpu_cap = (hw.numCpuCores * hw.cpuMhz) / 1000.0
        cpu_used = (qs.overallCpuUsage or 0) / 1000.0
        mem_cap = hw.memorySize / (1024**3)
        mem_used = (qs.overallMemoryUsage or 0) / 1024.0

        tcpu_cap += cpu_cap; tcpu_used += cpu_used
        tmem_cap += mem_cap; tmem_used += mem_used

        stats = query_metrics(perf_mgr, h, cmap, start, end, interval)
        rid = cmap['disk.read.average']['id']; wid = cmap['disk.write.average']['id']
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

    # Normalize percentages
    if hcount:
        mavg /= hcount; mmin /= hcount; mmax /= hcount
        cavg /= hcount; cmin /= hcount; cmax /= hcount

    # Free values
    cpu_free = tcpu_cap - tcpu_used
    mem_free = tmem_cap - tmem_used

    # Build output
    lines = [
        f"Datacenter: {identifier}",
        f"Cluster: {cl.name}",
        f"Timestamp: {start.strftime('%Y-%m-%d %H:%M')}",
        f"vHost Count: {hcount}",
        f"VM Count: {vcount}",
        f"CPU GHz Capacity: {round(tcpu_cap,2)}",
        f"CPU GHz Used: {round(tcpu_used,2)}",
        f"CPU GHz Free: {round(cpu_free,2)}",
        f"Memory Capacity GB: {round(tmem_cap,2)}",
        f"Memory Used GB: {round(tmem_used,2)}",
        f"Memory Free GB: {round(mem_free,2)}",
        f"Disk Usage Avg KBps: {round(davg,2)}",
        f"Disk Usage Min KBps: {int(dmin)}",
        f"Disk Usage Max KBps: {int(dmax)}",
        f"Network Usage Avg KBps: {round(navg,2)}",
        f"Network Usage Min KBps: {int(nmin)}",
        f"Network Usage Max KBps: {int(nmax)}",
        f"Memory Usage Avg perc: {mavg}",
        f"Memory Usage Min perc: {mmin}",
        f"Memory Usage Max perc: {mmax}",
        f"CPU Usage Avg perc: {cavg}",
        f"CPU Usage Min perc: {cmin}",
        f"CPU Usage Max perc: {cmax}",
        f"Total FreeSpace GB: {round(tstr_cap - tstr_used,2)}",
        f"Total Capacity GB: {round(tstr_cap,2)}"
    ]
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    servers = [h.strip() for h in args.vmware_ip.split(',')]
    port = args.vmware_port
    user = args.vmware_username
    pwd = args.vmware_password

    start, end = round_interval()
    interval = 300
    desired = [
        'cpu.usage.average','mem.usage.average',
        'disk.read.average','disk.write.average',
        'net.usage.average'
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

            # Advanced setting for identifier
            try:
                opts = {opt.key: opt.value for opt in content.setting.QueryOptions()
                        if opt.key in ('config.vpxd.hostnameUrl','VirtualCenter.FQDN')}
                identifier = opts.get('config.vpxd.hostnameUrl') or opts.get('VirtualCenter.FQDN') or vc
            except Exception:
                identifier = vc

            for dc in content.rootFolder.childEntity:
                if not hasattr(dc, 'hostFolder'):
                    continue
                for cl in [c for c in dc.hostFolder.childEntity
                           if isinstance(c, vim.ClusterComputeResource)]:
                    futures.append(executor.submit(
                        process_cluster, identifier, cl,
                        perf_mgr, cmap, start, end, interval
                    ))
        for f in as_completed(futures):
            print(f.result())

    for si in service_instances:
        Disconnect(si)


if __name__ == '__main__':
    main()