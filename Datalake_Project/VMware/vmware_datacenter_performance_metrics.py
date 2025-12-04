#!/usr/bin/env python3
"""
Collects datacenter-level performance metrics from vCenter using pyVmomi.
Outputs plain-text metrics for each datacenter in a human-readable format.
Metrics include capacity, counts, and 15-minute interval avg/min/max usage values.
Uses a static 5-minute sampling period (intervalId=300) and pools samples over the last 15 minutes.
"""

import ssl
import argparse
from datetime import datetime, timedelta
from math import floor
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl


def parse_args():
    parser = argparse.ArgumentParser(
        description='Collect datacenter metrics from vCenter using pyVmomi.'
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
    # Build metric list
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
    # Collect samples
    samples = {}
    if results:
        for m in results[0].value:
            cid = m.id.counterId
            vals = m.value or []
            samples.setdefault(cid, []).extend(vals)
    # Compute stats
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
        mn  = raw_min / scale
        mx  = raw_max / scale
        if info['percent']:
            avg /= 100.0; mn /= 100.0; mx /= 100.0
        stats[cid] = {'avg': avg, 'min': mn, 'max': mx}
    return stats


def main():
    args = parse_args()
    vcenters = [h.strip() for h in args.vmware_ip.split(',')]
    port = args.vmware_port
    user, pwd = args.vmware_username, args.vmware_password

    # Determine last 15-minute window
    start, end = round_interval()
    interval = 300  # 5-minute sampling period

    desired = [
        'cpu.usage.average', 'mem.usage.average',
        'disk.read.average', 'disk.write.average',
        'net.usage.average'
    ]

    for vc in vcenters:
        si = SmartConnect(host=vc, user=user, pwd=pwd,
                          port=port, sslContext=ssl._create_unverified_context())
        content = si.RetrieveContent()
        perf_mgr = content.perfManager
        cmap = get_perf_counter_map(perf_mgr, desired)

        for dc in content.rootFolder.childEntity:
            if not hasattr(dc, 'hostFolder'):
                continue
            # Initialize accumulators
            tmem_cap = tmem_used = 0.0
            tstr_cap = tstr_used = 0.0
            tcpu_cap = tcpu_used = 0.0
            davg = dmin = dmax = 0.0
            navg = nmin = nmax = 0.0
            mavg = mmin = mmax = 0.0
            cavg = cmin = cmax = 0.0

            # Inventory lists
            clusters = [c for c in dc.hostFolder.childEntity
                        if isinstance(c, vim.ClusterComputeResource)]
            hosts_list = []
            vms_list = []
            for cl in clusters:
                for h in cl.host:
                    hosts_list.append(h)
                    for vm in h.vm:
                        if not getattr(vm.config, 'template', False):
                            vms_list.append(vm)

            # Counts
            hcount = len(hosts_list)
            vcount = len(vms_list)
            ccnt = len(clusters)

            # Storage capacities
            for ds in dc.datastore:
                cap = ds.summary.capacity / (1024**3)
                free = ds.summary.freeSpace / (1024**3)
                tstr_cap += cap
                tstr_used += (cap - free)

            # Host metrics
            for h in hosts_list:
                hw = h.summary.hardware
                qs = h.summary.quickStats
                tcpu_cap += (hw.numCpuCores * hw.cpuMhz) / 1000.0
                tcpu_used += (qs.overallCpuUsage or 0) / 1000.0
                tmem_cap += hw.memorySize / (1024**3)
                tmem_used += (qs.overallMemoryUsage or 0) / 1024.0

                stats = query_metrics(perf_mgr, h, cmap, start, end, interval)
                # Disk I/O
                rid = cmap['disk.read.average']['id']
                wid = cmap['disk.write.average']['id']
                if rid in stats and wid in stats:
                    davg += stats[rid]['avg'] + stats[wid]['avg']
                    dmin += stats[rid]['min'] + stats[wid]['min']
                    dmax += stats[rid]['max'] + stats[wid]['max']
                # Network I/O
                nid = cmap['net.usage.average']['id']
                if nid in stats:
                    navg += stats[nid]['avg']
                    nmin += stats[nid]['min']
                    nmax += stats[nid]['max']
                # Memory % usage
                mid = cmap['mem.usage.average']['id']
                if mid in stats:
                    mavg += stats[mid]['avg']
                    mmin += stats[mid]['min']
                    mmax += stats[mid]['max']
                # CPU % usage
                cid = cmap['cpu.usage.average']['id']
                if cid in stats:
                    cavg += stats[cid]['avg']
                    cmin += stats[cid]['min']
                    cmax += stats[cid]['max']

            # Normalize percent metrics by host count
            if hcount:
                mavg /= hcount; mmin /= hcount; mmax /= hcount
                cavg /= hcount; cmin /= hcount; cmax /= hcount

            # Print output
            print(f"datacenter: {dc.name}")
            print(f"timestamp: {start.strftime('%Y-%m-%d %H:%M')}")
            print(f"total memory capacity gb: {round(tmem_cap, 2)}")
            print(f"total memory used gb: {round(tmem_used, 2)}")
            print(f"total storage capacity gb: {int(tstr_cap * 1024)}")
            print(f"total used storage gb: {int(tstr_used * 1024)}")
            print(f"total cpu ghz capacity: {round(tcpu_cap, 2)}")
            print(f"total cpu ghz used: {round(tcpu_used, 2)}")
            print(f"disk usage avg kbps: {round(davg, 2)}")
            print(f"disk usage min kbps: {round(dmin, 2)}")
            print(f"disk usage max kbps: {round(dmax, 2)}")
            print(f"network usage avg kbps: {round(navg, 2)}")
            print(f"network usage min kbps: {round(nmin, 2)}")
            print(f"network usage max kbps: {round(nmax, 2)}")
            print(f"memory usage avg perc: {mavg}")
            print(f"memory usage min perc: {mmin}")
            print(f"memory usage max perc: {mmax}")
            print(f"cpu usage avg perc: {cavg}")
            print(f"cpu usage min perc: {cmin}")
            print(f"cpu usage max perc: {cmax}")
            print(f"total host count: {hcount}")
            print(f"total vm count: {vcount}")
            print(f"total cluster count: {ccnt}\n")

        Disconnect(si)


if __name__ == '__main__':
    main()