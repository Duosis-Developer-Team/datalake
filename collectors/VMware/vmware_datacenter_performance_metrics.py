#!/usr/bin/env python3
"""
Collects vCenter performance metrics or tests vCenter name retrieval methods using pyVmomi.

Use --test-names to print various vCenter name sources (about.name, about.fullName, ServiceInstance.name,
stub URL, and advanced settings like vpxd.fqdn) and exit. Otherwise, collects metrics as before.
"""

import ssl
import argparse
import socket
import sys
from datetime import datetime, timedelta
from math import floor
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl


def parse_args():
    parser = argparse.ArgumentParser(
        description='Collect vCenter metrics or test name retrieval methods.'
    )
    parser.add_argument('--vmware-ip', required=True,
                        help='Comma-separated vCenter hostnames or IPs')
    parser.add_argument('--vmware-port', type=int, default=443,
                        help='vCenter port (default: 443)')
    parser.add_argument('--vmware-username', required=True,
                        help='Username for vCenter authentication')
    parser.add_argument('--vmware-password', required=True,
                        help='Password for vCenter authentication')
    parser.add_argument('--test-names', action='store_true',
                        help='Test various vCenter name sources and exit')
    return parser.parse_args()


def test_name_sources(si, content):
    # Gather candidate name sources
    sources = {}
    # AboutInfo
    sources['about.name'] = content.about.name
    sources['about.fullName'] = content.about.fullName
    sources['about.instanceUuid'] = content.about.instanceUuid
    # ServiceInstance.name if available
    sources['serviceInstance.name'] = getattr(si, 'name', None)
    # Stub URL
    try:
        sources['stub.url'] = si._stub.url
    except Exception:
        sources['stub.url'] = None
    # DNS
    try:
        sources['socket.getfqdn'] = socket.getfqdn(si._stub.host)
    except Exception:
        sources['socket.getfqdn'] = None
    # Advanced settings
    try:
        opt_mgr = content.setting
        for opt in opt_mgr.QueryOptions():
            key = opt.key
            if key in ('config.vpxd.hostnameUrl', 'VirtualCenter.FQDN'):
                sources[f'option.{key}'] = opt.value
    except Exception:
        pass
    # Print
    print(f"\n=== vCenter Name Sources ===")
    for k, v in sources.items():
        print(f"{k}: {v}")
    print("=== End of sources ===\n")


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


def main():
    args = parse_args()
    vcenters = [h.strip() for h in args.vmware_ip.split(',')]
    port = args.vmware_port
    user, pwd = args.vmware_username, args.vmware_password

    start, end = round_interval()
    desired = ['cpu.usage.average', 'mem.usage.average', 'disk.read.average', 'disk.write.average', 'net.usage.average']

    for vc in vcenters:
        si = SmartConnect(host=vc, user=user, pwd=pwd,
                          port=port, sslContext=ssl._create_unverified_context())
        content = si.RetrieveContent()

        if args.test_names:
            test_name_sources(si, content)
            Disconnect(si)
            sys.exit(0)

        # Determine vCenter identifier from advanced settings
        identifier = None
        try:
            opt_mgr = content.setting
            for opt in opt_mgr.QueryOptions():
                if opt.key == 'config.vpxd.hostnameUrl' and opt.value:
                    identifier = opt.value
                    break
            if not identifier:
                for opt in opt_mgr.QueryOptions():
                    if opt.key == 'VirtualCenter.FQDN' and opt.value:
                        identifier = opt.value
                        break
        except Exception:
            pass
        if not identifier:
            identifier = socket.getfqdn(vc)

        perf_mgr = content.perfManager
        cmap = get_perf_counter_map(perf_mgr, desired)

        # Initialize accumulators
        tmem_cap = tmem_used = 0.0
        tstr_cap = tstr_used = 0.0
        tcpu_cap = tcpu_used = 0.0
        davg = dmin = dmax = 0.0
        navg = nmin = nmax = 0.0
        mavg = mmin = mmax = 0.0
        cavg = cmin = cmax = 0.0
        hcount = vcount = ccnt = 0

        # Aggregate metrics
        for dc in content.rootFolder.childEntity:
            if not hasattr(dc, 'hostFolder'):
                continue
            clusters = [c for c in dc.hostFolder.childEntity if isinstance(c, vim.ClusterComputeResource)]
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
                cap = ds.summary.capacity / (1024**3)
                free = ds.summary.freeSpace / (1024**3)
                tstr_cap += cap; tstr_used += cap - free
            for h in hosts_list:
                hw = h.summary.hardware; qs = h.summary.quickStats
                tcpu_cap += hw.numCpuCores * hw.cpuMhz / 1000.0
                tcpu_used += (qs.overallCpuUsage or 0) / 1000.0
                tmem_cap += hw.memorySize / (1024**3)
                tmem_used += (qs.overallMemoryUsage or 0) / 1024.0
                stats = query_metrics(perf_mgr, h, cmap, start, end)
                rid, wid = cmap['disk.read.average']['id'], cmap['disk.write.average']['id']
                if rid in stats and wid in stats:
                    davg += stats[rid]['avg'] + stats[wid]['avg']
                    dmin += stats[rid]['min'] + stats[wid]['min']
                    dmax += stats[rid]['max'] + stats[wid]['max']
                nid = cmap['net.usage.average']['id']
                if nid in stats: navg += stats[nid]['avg']; nmin += stats[nid]['min']; nmax += stats[nid]['max']
                mid = cmap['mem.usage.average']['id']
                if mid in stats: mavg += stats[mid]['avg']; mmin += stats[mid]['min']; mmax += stats[mid]['max']
                cid = cmap['cpu.usage.average']['id']
                if cid in stats: cavg += stats[cid]['avg']; cmin += stats[cid]['min']; cmax += stats[cid]['max']
        if hcount:
            mavg /= hcount; mmin /= hcount; mmax /= hcount
            cavg /= hcount; cmin /= hcount; cmax /= hcount

        # Print aggregated metrics
        print(f"datacenter: {identifier}")
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