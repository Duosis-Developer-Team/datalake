#!/usr/bin/env python3
"""
VMware Cluster Collector - Config + Aggregated Metrics

This script extracts raw cluster configuration and calculates
aggregated metrics from hosts. It produces:
- vmware_cluster_config: Cluster configuration and summary
- vmware_cluster_metrics_agg: Pre-calculated aggregated metrics (for Grafana/reporting)

Output: Single JSON array to stdout (config and metrics_agg records; ETL routes by data_type)
"""

import json
import ssl
import argparse
import sys
from datetime import datetime, timezone, timedelta
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='VMware Cluster Collector - Config and Aggregated Metrics'
    )
    parser.add_argument('--vmware-ip', required=True,
                        help='vCenter hostname or IP')
    parser.add_argument('--vmware-port', type=int, default=443,
                        help='vCenter port (default: 443)')
    parser.add_argument('--vmware-username', required=True,
                        help='Username for vCenter authentication')
    parser.add_argument('--vmware-password', required=True,
                        help='Password for vCenter authentication')
    parser.add_argument('--perf-interval', type=int, default=300,
                        help='Performance interval in seconds (default: 300)')
    parser.add_argument('--perf-window', type=int, default=900,
                        help='Performance window in seconds (default: 900 = 15min)')
    return parser.parse_args()


def safe_get_attr(obj, attr_path, default=None):
    """Safely get nested attribute value."""
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


def get_counter_info_map(perf_mgr, desired_counters):
    """Build counter ID to info mapping."""
    counter_map = {}
    for pc in perf_mgr.perfCounter:
        counter_name = f"{pc.groupInfo.key}.{pc.nameInfo.key}.{pc.rollupType}"
        if counter_name in desired_counters:
            scale = getattr(pc.unitInfo, 'scale', 1) or 1
            unit_key = getattr(pc.unitInfo, 'key', '').lower()
            unit_label = getattr(pc.unitInfo, 'label', '').lower()
            is_percent = 'percent' in unit_key or '%' in unit_label

            counter_map[pc.key] = {
                'name': counter_name,
                'scale': scale,
                'is_percent': is_percent
            }
    return counter_map


def query_host_perf_stats(perf_mgr, host, counter_map, start_time, end_time, interval_id):
    """Query performance stats for a host and return aggregated values."""
    try:
        metric_ids = [vim.PerformanceManager.MetricId(counterId=cid, instance='*')
                      for cid in counter_map.keys()]

        spec = vim.PerformanceManager.QuerySpec(
            entity=host,
            metricId=metric_ids,
            startTime=start_time,
            endTime=end_time,
            intervalId=interval_id
        )

        results = perf_mgr.QueryPerf(querySpec=[spec])
        if not results:
            return {}

        stats = {}
        for perf_metric in results[0].value:
            counter_id = perf_metric.id.counterId
            if not perf_metric.value:
                continue

            info = counter_map.get(counter_id, {})
            scale = info.get('scale', 1)
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

            stats[counter_id] = {'avg': avg, 'min': mn, 'max': mx}

        return stats
    except Exception as e:
        print(f"Warning: Failed to query perf for host {host._moId}: {e}", file=sys.stderr)
        return {}


def extract_cluster_config(cluster, vcenter_uuid, collection_timestamp, datacenter_moid):
    """
    Extract cluster configuration AS-IS from VMware API.
    Source: cluster.configuration, cluster.summary
    """
    summary = cluster.summary
    config = cluster.configuration

    return {
        "data_type": "vmware_cluster_config",
        "collection_timestamp": collection_timestamp,
        "vcenter_uuid": vcenter_uuid,
        "datacenter_moid": datacenter_moid,
        "cluster_moid": cluster._moId,
        "name": cluster.name,

        # cluster.summary fields (AS-IS)
        "summary_num_hosts": safe_get_attr(summary, 'numHosts'),
        "summary_num_cpu_cores": safe_get_attr(summary, 'numCpuCores'),
        "summary_num_cpu_threads": safe_get_attr(summary, 'numCpuThreads'),
        "summary_effective_cpu": safe_get_attr(summary, 'effectiveCpu'),
        "summary_total_cpu": safe_get_attr(summary, 'totalCpu'),
        "summary_num_effective_hosts": safe_get_attr(summary, 'numEffectiveHosts'),
        "summary_total_memory": safe_get_attr(summary, 'totalMemory'),
        "summary_effective_memory": safe_get_attr(summary, 'effectiveMemory'),
        "summary_overall_status": safe_get_attr(summary, 'overallStatus'),

        # cluster.configuration.dasConfig (HA)
        "config_das_enabled": safe_get_attr(config, 'dasConfig.enabled'),
        "config_das_vm_monitoring": safe_get_attr(config, 'dasConfig.vmMonitoring'),
        "config_das_host_monitoring": safe_get_attr(config, 'dasConfig.hostMonitoring'),

        # cluster.configuration.drsConfig (DRS)
        "config_drs_enabled": safe_get_attr(config, 'drsConfig.enabled'),
        "config_drs_default_vm_behavior": safe_get_attr(config, 'drsConfig.defaultVmBehavior'),
        "config_drs_vmotion_rate": safe_get_attr(config, 'drsConfig.vmotionRate'),

        # cluster.configuration.dpmConfigInfo (DPM)
        "config_dpm_enabled": safe_get_attr(config, 'dpmConfigInfo.enabled'),
    }


def calculate_cluster_metrics_agg(cluster, vcenter_uuid, datacenter_moid, collection_timestamp,
                                  perf_mgr, counter_map, start_time, end_time, interval_id):
    """
    Calculate aggregated metrics for one cluster from its hosts.
    Returns one record compatible with raw_vmware_cluster_metrics_agg.
    """
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

        stats = query_host_perf_stats(perf_mgr, host, counter_map, start_time, end_time, interval_id)

        for counter_id, stat in stats.items():
            counter_info = counter_map.get(counter_id, {})
            counter_name = counter_info.get('name', '')

            if 'cpu.usage' in counter_name:
                cpu_perc_list.append(stat)
            elif 'mem.usage' in counter_name:
                mem_perc_list.append(stat)
            elif 'disk' in counter_name:
                disk_kbps_list.append(stat)
            elif 'net.usage' in counter_name:
                net_kbps_list.append(stat)

    # Storage from cluster datastores
    total_storage_bytes_capacity = 0
    total_storage_bytes_used = 0
    for ds in cluster.datastore:
        cap = ds.summary.capacity or 0
        free = ds.summary.freeSpace or 0
        total_storage_bytes_capacity += cap
        total_storage_bytes_used += cap - free

    # Aggregate percentages (average across hosts)
    cpu_avg = sum(s['avg'] for s in cpu_perc_list) / len(cpu_perc_list) if cpu_perc_list else None
    cpu_min = min(s['min'] for s in cpu_perc_list) if cpu_perc_list else None
    cpu_max = max(s['max'] for s in cpu_perc_list) if cpu_perc_list else None

    mem_avg = sum(s['avg'] for s in mem_perc_list) / len(mem_perc_list) if mem_perc_list else None
    mem_min = min(s['min'] for s in mem_perc_list) if mem_perc_list else None
    mem_max = max(s['max'] for s in mem_perc_list) if mem_perc_list else None

    # Disk/network: sum across hosts (KBps)
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


def main():
    """Main execution."""
    args = parse_args()

    collection_timestamp = datetime.now(timezone.utc).isoformat()
    all_records = []
    si = None

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(seconds=args.perf_window)
    interval_id = args.perf_interval

    desired_counters = [
        'cpu.usage.average',
        'mem.usage.average',
        'disk.read.average',
        'disk.write.average',
        'net.usage.average'
    ]

    try:
        context = ssl._create_unverified_context()
        si = SmartConnect(
            host=args.vmware_ip,
            user=args.vmware_username,
            pwd=args.vmware_password,
            port=args.vmware_port,
            sslContext=context
        )

        content = si.RetrieveContent()
        vcenter_uuid = content.about.instanceUuid
        perf_mgr = content.perfManager
        counter_map = get_counter_info_map(perf_mgr, desired_counters)

        for datacenter in content.rootFolder.childEntity:
            if not hasattr(datacenter, 'hostFolder'):
                continue

            datacenter_moid = datacenter._moId

            for entity in datacenter.hostFolder.childEntity:
                if not isinstance(entity, vim.ClusterComputeResource):
                    continue

                all_records.append(extract_cluster_config(
                    entity, vcenter_uuid, collection_timestamp, datacenter_moid
                ))
                all_records.append(calculate_cluster_metrics_agg(
                    entity, vcenter_uuid, datacenter_moid, collection_timestamp,
                    perf_mgr, counter_map, start_time, end_time, interval_id
                ))

        print(json.dumps(all_records, default=str, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        if si:
            Disconnect(si)


if __name__ == '__main__':
    main()
