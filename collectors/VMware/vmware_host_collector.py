#!/usr/bin/env python3
"""
VMware Host Collector - Raw Data Extraction (Zero Transformation)

This script extracts raw data from VMware vCenter API for ESXi hosts
with NO calculations or conversions. It produces multiple data_type records:
- vmware_host_hardware: Hardware configuration
- vmware_host_runtime: Runtime state
- vmware_host_storage: Host-Datastore relationships
- vmware_host_perf_raw: Raw performance samples
- vmware_host_perf_agg: Aggregated performance (optimization)

Output: Single JSON array to stdout containing all data_types
"""

import json
import ssl
import socket
import argparse
import sys
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='VMware Host Collector - Raw Data Extraction'
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
    parser.add_argument('--max-workers', type=int, default=16,
                        help='Max parallel workers for host processing (default: 16)')
    parser.add_argument('--timeout', type=int, default=1800,
                        help='Socket and total collection timeout in seconds (default: 1800 = 30 min). 0 = no timeout')
    parser.add_argument('--max-hosts', type=int, default=0,
                        help='Max hosts to process; 0 = all (default: 0)')
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


def safe_timestamp(dt_obj):
    """Convert datetime object to ISO-8601 string. Returns None for epoch time (unset timestamps)."""
    if dt_obj is None:
        return None
    try:
        # Check if timestamp is epoch time (1970-01-01) = unset timestamp in VMware
        if dt_obj.year == 1970 and dt_obj.month == 1 and dt_obj.day == 1:
            return None
        return dt_obj.isoformat()
    except:
        return None


def serialize_record(record):
    """Serialize any list/array fields to JSON strings for PostgreSQL compatibility."""
    for key, value in record.items():
        if isinstance(value, (list, tuple)) and not isinstance(value, str):
            record[key] = json.dumps(value)
    return record


def extract_host_hardware(host, vcenter_uuid, collection_timestamp, hierarchy):
    """
    Extract host hardware configuration AS-IS from VMware API.
    Source: host.hardware, host.summary.hardware, host.config.product
    """
    hw = host.summary.hardware
    sys_info = host.hardware.systemInfo
    product = host.config.product
    
    # Handle array field - serialize to JSON string for PostgreSQL compatibility
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
        
        # host.summary.hardware fields (AS-IS)
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
        
        # host.hardware.systemInfo fields (AS-IS)
        "system_info_vendor": safe_get_attr(sys_info, 'vendor'),
        "system_info_model": safe_get_attr(sys_info, 'model'),
        "system_info_uuid": safe_get_attr(sys_info, 'uuid'),
        "system_info_other_identifying_info": other_id_info,
        
        # host.config.product fields (AS-IS)
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
    """
    Extract host runtime state AS-IS from VMware API.
    Source: host.runtime, host.summary.quickStats, host.summary.config
    """
    runtime = host.runtime
    qs = host.summary.quickStats
    config = host.summary.config
    
    return {
        "data_type": "vmware_host_runtime",
        "collection_timestamp": collection_timestamp,
        "vcenter_uuid": vcenter_uuid,
        "host_moid": host._moId,
        
        # host.runtime fields (AS-IS)
        "connection_state": safe_get_attr(runtime, 'connectionState'),
        "power_state": safe_get_attr(runtime, 'powerState'),
        "standby_mode": safe_get_attr(runtime, 'standbyMode'),
        "in_maintenance_mode": safe_get_attr(runtime, 'inMaintenanceMode'),
        "in_quarantine_mode": safe_get_attr(runtime, 'inQuarantineMode'),
        "boot_time": safe_timestamp(safe_get_attr(runtime, 'bootTime')),
        "health_system_runtime_system_health_info": str(safe_get_attr(runtime, 'healthSystemRuntime.systemHealthInfo')) if safe_get_attr(runtime, 'healthSystemRuntime.systemHealthInfo') else None,
        
        # host.summary.quickStats (AS-IS, NO CONVERSION)
        "quick_stats_overall_cpu_usage": safe_get_attr(qs, 'overallCpuUsage'),
        "quick_stats_overall_memory_usage": safe_get_attr(qs, 'overallMemoryUsage'),
        "quick_stats_distributed_cpu_fairness": safe_get_attr(qs, 'distributedCpuFairness'),
        "quick_stats_distributed_memory_fairness": safe_get_attr(qs, 'distributedMemoryFairness'),
        "quick_stats_uptime": safe_get_attr(qs, 'uptime'),
        
        # host.summary.config (connection info)
        "config_name": safe_get_attr(config, 'name'),
        "config_port": safe_get_attr(config, 'port'),
        "config_ssl_thumbprint": safe_get_attr(config, 'sslThumbprint'),
    }


def extract_host_storage(host, vcenter_uuid, collection_timestamp):
    """
    Extract Host-Datastore relationships AS-IS.
    Source: host.datastore[]
    Returns: List of records (one per datastore)
    """
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
            
            # Datastore info (AS-IS)
            "datastore_name": safe_get_attr(ds, 'name'),
            "datastore_url": safe_get_attr(ds, 'summary.url'),
            "datastore_capacity": safe_get_attr(ds, 'summary.capacity'),
            "datastore_free_space": safe_get_attr(ds, 'summary.freeSpace'),
            "datastore_type": safe_get_attr(ds, 'summary.type'),
            "datastore_accessible": safe_get_attr(ds, 'summary.accessible'),
            "datastore_multiple_host_access": safe_get_attr(ds, 'summary.multipleHostAccess'),
        })
    
    return storage_records


def get_counter_info(perf_mgr, counter_id):
    """Get counter metadata."""
    try:
        for pc in perf_mgr.perfCounter:
            if pc.key == counter_id:
                return {
                    'name': f"{pc.groupInfo.key}.{pc.nameInfo.key}.{pc.rollupType}",
                    'group': pc.groupInfo.key,
                    'name_short': pc.nameInfo.key,
                    'rollup': pc.rollupType,
                    'stats_type': pc.statsType,
                    'unit_key': pc.unitInfo.key,
                    'unit_label': pc.unitInfo.label,
                }
    except:
        pass
    return {
        'name': f"counter_{counter_id}",
        'group': 'unknown',
        'name_short': 'unknown',
        'rollup': 'unknown',
        'stats_type': 'unknown',
        'unit_key': 'unknown',
        'unit_label': '',
    }


def extract_host_perf_raw(host, vcenter_uuid, collection_timestamp, perf_mgr, counter_ids, start_time, end_time, interval_id):
    """
    Extract raw performance samples AS-IS (NO AGGREGATION).
    Source: perfManager.QueryPerf()
    Returns: List of records (one per sample)
    """
    perf_raw_records = []
    
    try:
        metric_ids = [vim.PerformanceManager.MetricId(counterId=cid, instance='*') 
                      for cid in counter_ids]
        
        spec = vim.PerformanceManager.QuerySpec(
            entity=host,
            metricId=metric_ids,
            startTime=start_time,
            endTime=end_time,
            intervalId=interval_id
        )
        
        results = perf_mgr.QueryPerf(querySpec=[spec])
        if not results:
            return perf_raw_records
        
        for perf_metric in results[0].value:
            counter_id = perf_metric.id.counterId
            instance = perf_metric.id.instance or ''
            counter_info = get_counter_info(perf_mgr, counter_id)
            
            if not perf_metric.value:
                continue
            
            interval_seconds = interval_id
            for i, value in enumerate(perf_metric.value):
                sample_time = start_time + timedelta(seconds=i * interval_seconds)
                
                perf_raw_records.append({
                    "data_type": "vmware_host_perf_raw",
                    "collection_timestamp": collection_timestamp,
                    "vcenter_uuid": vcenter_uuid,
                    "host_moid": host._moId,
                    
                    # Counter metadata
                    "counter_id": counter_id,
                    "counter_name": counter_info['name'],
                    "counter_group": counter_info['group'],
                    "counter_name_short": counter_info['name_short'],
                    "counter_rollup_type": counter_info['rollup'],
                    "counter_stats_type": counter_info['stats_type'],
                    "counter_unit_key": counter_info['unit_key'],
                    "counter_unit_label": counter_info['unit_label'],
                    "instance": instance,
                    
                    # Sample data (AS-IS)
                    "sample_timestamp": sample_time.isoformat(),
                    "value": value,
                    "interval_id": interval_id,
                })
    
    except Exception as e:
        print(f"Warning: Failed to extract perf data for Host {host._moId}: {e}", file=sys.stderr)
    
    return perf_raw_records


def calculate_host_perf_agg(perf_raw_records, vcenter_uuid, collection_timestamp, start_time, end_time):
    """
    Calculate aggregated performance metrics from raw samples.
    This is an OPTIMIZATION table.
    """
    perf_agg_records = []
    
    # Group by counter_id and instance
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
    
    # Calculate aggregates
    for (counter_id, instance), data in grouped.items():
        values = data['values']
        if not values:
            continue
        
        perf_agg_records.append({
            "data_type": "vmware_host_perf_agg",
            "collection_timestamp": collection_timestamp,
            "vcenter_uuid": vcenter_uuid,
            "host_moid": data['host_moid'],
            
            # Aggregation window
            "window_start": start_time.isoformat(),
            "window_end": end_time.isoformat(),
            "window_duration_seconds": int((end_time - start_time).total_seconds()),
            "sample_count": len(values),
            
            # Counter metadata
            "counter_id": counter_id,
            "counter_name": data['counter_info']['counter_name'],
            "counter_group": data['counter_info']['counter_group'],
            "counter_rollup_type": data['counter_info']['counter_rollup_type'],
            "counter_unit_key": data['counter_info']['counter_unit_key'],
            "instance": instance,
            
            # Aggregated values
            "value_avg": sum(values) / len(values),
            "value_min": min(values),
            "value_max": max(values),
            "value_stddev": None,
            "value_first": values[0],
            "value_last": values[-1],
        })
    
    return perf_agg_records


def process_one_host(host, hierarchy, vcenter_uuid, collection_timestamp, perf_mgr, counter_ids,
                     start_time, end_time, interval_id):
    """
    Process a single host: extract hardware, runtime, storage, perf raw, perf agg.
    Used by ThreadPoolExecutor for parallel collection (same pattern as vmware_host_performance_metrics).
    """
    records = []
    records.append(extract_host_hardware(host, vcenter_uuid, collection_timestamp, hierarchy))
    records.append(extract_host_runtime(host, vcenter_uuid, collection_timestamp))
    records.extend(extract_host_storage(host, vcenter_uuid, collection_timestamp))
    perf_raw = extract_host_perf_raw(
        host, vcenter_uuid, collection_timestamp, perf_mgr,
        counter_ids, start_time, end_time, interval_id
    )
    records.extend(perf_raw)
    perf_agg = calculate_host_perf_agg(
        perf_raw, vcenter_uuid, collection_timestamp,
        start_time, end_time
    )
    records.extend(perf_agg)
    return records


def main():
    """Main execution."""
    args = parse_args()
    
    collection_timestamp = datetime.now(timezone.utc).isoformat()
    all_records = []
    si = None
    
    # Calculate performance time window
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(seconds=args.perf_window)
    
    # Common performance counters
    desired_counters = [
        'cpu.usage.average',
        'mem.usage.average',
        'disk.read.average',
        'disk.write.average',
        'net.usage.average',
        'power.power.average'
    ]
    
    try:
        # Apply socket timeout so connect and API calls do not hang indefinitely
        if args.timeout > 0:
            socket.setdefaulttimeout(args.timeout)

        # Connect to vCenter
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
        
        # Get counter IDs
        counter_ids = []
        for pc in perf_mgr.perfCounter:
            counter_name = f"{pc.groupInfo.key}.{pc.nameInfo.key}.{pc.rollupType}"
            if counter_name in desired_counters:
                counter_ids.append(pc.key)
        
        # Build list of (host, hierarchy) for parallel processing (same pattern as vmware_host_performance_metrics)
        jobs = []
        for datacenter in content.rootFolder.childEntity:
            if not hasattr(datacenter, 'hostFolder'):
                continue
            datacenter_moid = datacenter._moId
            for entity in datacenter.hostFolder.childEntity:
                if not isinstance(entity, vim.ClusterComputeResource):
                    continue
                cluster_moid = entity._moId
                hierarchy = {
                    'datacenter': datacenter_moid,
                    'cluster': cluster_moid
                }
                for host in entity.host:
                    jobs.append((host, hierarchy, vcenter_uuid, collection_timestamp, perf_mgr,
                                 counter_ids, start_time, end_time, args.perf_interval))
                    if args.max_hosts > 0 and len(jobs) >= args.max_hosts:
                        break
                if args.max_hosts > 0 and len(jobs) >= args.max_hosts:
                    break
            if args.max_hosts > 0 and len(jobs) >= args.max_hosts:
                break

        if args.max_hosts > 0:
            print(f"Limiting to first {len(jobs)} hosts (--max-hosts={args.max_hosts})", file=sys.stderr)

        # Process hosts in parallel (with optional total timeout)
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            futures = [
                executor.submit(process_one_host, *job)
                for job in jobs
            ]
            try:
                completion = as_completed(futures, timeout=args.timeout if args.timeout > 0 else None)
                for f in completion:
                    all_records.extend(f.result())
            except FuturesTimeoutError:
                print("Timeout reached; outputting partial results.", file=sys.stderr)

        # Output single JSON array
        print(json.dumps(all_records, default=str, indent=2))
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        if si:
            Disconnect(si)


if __name__ == '__main__':
    main()
