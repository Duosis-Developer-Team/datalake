#!/usr/bin/env python3
"""
Collects VM-level performance metrics from vCenter using pyVmomi.
Processes host and VM data in parallel threads, caching host-level UUIDs.
Outputs plain-text metrics per VM in a human-readable format.
Metrics include Number of CPUs, ESXi System UUID, Total CPU Capacity Mhz,
Total Memory Capacity GB, CPU Usage Avg/Min/Max Mhz, Memory Usage Avg/Min/Max %,
Disk I/O Avg/Min/Max KBps, Guest OS, Datastore list, Used/Provisioned Space GB,
Folder path, VM UUID, BootTime.
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
        description='Collect VM metrics from vCenter using pyVmomi.'
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


def round_interval(now=None, minutes=15):
    if now is None:
        now = datetime.now()
    slot = floor(now.minute / minutes) * minutes
    base = now.replace(minute=0, second=0, microsecond=0)
    end = base + timedelta(minutes=slot)
    start = end - timedelta(minutes=minutes)
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


def query_metrics(perf_mgr, entity, mids, cmap, start, end, interval_id=300):
    spec = vim.PerformanceManager.QuerySpec(
        entity=entity,
        metricId=mids,
        startTime=start,
        endTime=end,
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
        info = next(v for v in cmap.values() if v['id'] == cid)
        avg_raw = sum(vals) / len(vals)
        mn_raw = min(vals)
        mx_raw = max(vals)
        avg = avg_raw / info['scale']
        mn = mn_raw / info['scale']
        mx = mx_raw / info['scale']
        if info['percent']:
            avg /= 100.0; mn /= 100.0; mx /= 100.0
        stats[cid] = {'avg': avg, 'min': mn, 'max': mx}
    return stats


def process_vm(dc_name, cluster_name, host_name, host_uuid, vm, perf_mgr, cmap, mids, start, end, interval):
    # VM and host details
    num_cpus = vm.summary.config.numCpu
    esxi_system_uuid = host_uuid
    total_cpu_capacity_mhz = 0  # VM-level total CPU capacity would require host CPU info
    # Total memory from VM config (memorySizeMB); convert to GB
    memory_size_mb = getattr(vm.summary.config, 'memorySizeMB', 0) or 0
    total_mem_capacity_gb = memory_size_mb / 1024.0

    vm_name = vm.summary.config.name
    power_state = vm.runtime.powerState
    guest_os = vm.summary.config.guestFullName or ''

    # Storage
    committed = getattr(vm.summary.storage, 'committed', 0)
    uncommitted = getattr(vm.summary.storage, 'uncommitted', 0)
    used_space_gb = committed / (1024**3)
    prov_space_gb = (committed + uncommitted) / (1024**3)
    ds_names = [ds.info.name for ds in vm.datastore] if vm.datastore else []
    ds_list = ",".join(ds_names)

    # VM path, UUID, bootTime
    vmx = vm.summary.config.vmPathName or ''
    try:
        folder = vmx.split(']')[1].rsplit('/',1)[0].lstrip('/')
    except:
        folder = ''
    moid = getattr(vm, '_moId', '')
    inst_uuid = getattr(vm.config, 'instanceUuid', '')
    vm_uuid = f"VirtualMachine-{moid}:{inst_uuid}" if moid and inst_uuid else ''
    boot = getattr(vm.runtime, 'bootTime', None)
    boot_time = boot.strftime('%m/%d/%Y %H:%M:%S') if boot else ''

    # Performance stats
    stats = query_metrics(perf_mgr, vm, mids, cmap, start, end, interval)
    cpu_id = cmap['cpu.usage.average']['id']
    cpu = stats.get(cpu_id, {'avg':0,'min':0,'max':0})
    mem_id = cmap['mem.usage.average']['id']
    mem = stats.get(mem_id, {'avg':0,'min':0,'max':0})
    rid = cmap['disk.read.average']['id']; wid = cmap['disk.write.average']['id']
    disk = {'avg':0,'min':0,'max':0}
    if rid in stats and wid in stats:
        disk['avg'] = stats[rid]['avg'] + stats[wid]['avg']
        disk['min'] = stats[rid]['min'] + stats[wid]['min']
        disk['max'] = stats[rid]['max'] + stats[wid]['max']
    nid = cmap['net.usage.average']['id']
    net = stats.get(nid, {'avg':0,'min':0,'max':0})

    return "\n".join([
        f"Datacenter: {dc_name}",
        f"Cluster: {cluster_name}",
        f"VMHost: {host_name}",
        f"VMName: {vm_name}",
        f"Timestamp: {start.strftime('%Y-%m-%d %H:%M')}",
        f"Number of CPUs: {num_cpus}",
        f"ESXi System UUID: {esxi_system_uuid}",
        f"Total CPU Capacity Mhz: {total_cpu_capacity_mhz}",
        f"Total Memory Capacity GB: {total_mem_capacity_gb:.2f}",
        f"CPU Usage Avg Mhz: {cpu['avg']}",
        f"CPU Usage Min Mhz: {cpu['min']}",
        f"CPU Usage Max Mhz: {cpu['max']}",
        f"Memory Usage Avg perc: {mem['avg']}",
        f"Memory Usage Min perc: {mem['min']}",
        f"Memory Usage Max perc: {mem['max']}",
        f"Disk Usage Avg KBps: {disk['avg']}",
        f"Disk Usage Min KBps: {disk['min']}",
        f"Disk Usage Max KBps: {disk['max']}",
        f"Guest OS: {guest_os}",
        f"Datastore: {ds_list}",
        f"Used Space GB: {used_space_gb:.2f}",
        f"Provisioned Space GB: {prov_space_gb:.2f}",
        f"Folder: {folder}",
        f"UUID: {vm_uuid}",
        f"BootTime: {boot_time}"
    ]) + "\n"


def main():
    args = parse_args()
    servers = list(dict.fromkeys([h.strip() for h in args.vmware_ip.split(',')]))
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

    # Collect inventory and host UUIDs
    jobs = []
    host_uuid_map = {}
    instances = []
    for svc in servers:
        si = SmartConnect(host=svc, user=user, pwd=pwd, port=port,
                          sslContext=ssl._create_unverified_context())
        instances.append(si)
        content = si.RetrieveContent()
        perf_mgr = content.perfManager
        cmap = get_perf_counter_map(perf_mgr, desired)
        mids = [vim.PerformanceManager.MetricId(counterId=v['id'], instance='*')
                for v in cmap.values()]
        for dc in content.rootFolder.childEntity:
            if not hasattr(dc, 'hostFolder'):
                continue
            for cl in dc.hostFolder.childEntity:
                if not isinstance(cl, vim.ClusterComputeResource):
                    continue
                for host in cl.host:
                    host_uuid_map[host._moId] = getattr(host.hardware.systemInfo, 'uuid', 'N/A')
                    for vm in host.vm:
                        if vm.config.template:
                            continue
                        jobs.append((dc.name, cl.name, host.name,
                                     host_uuid_map[host._moId],
                                     vm, perf_mgr, cmap, mids,
                                     start, end, interval))

    # Parallel execution
    with ThreadPoolExecutor(max_workers=32) as exe:
        futures = [exe.submit(process_vm, *job) for job in jobs]
        for f in as_completed(futures):
            print(f.result())

    for si in instances:
        Disconnect(si)


if __name__ == '__main__':
    main()
