#!/usr/bin/env python3
"""
VMware VM Collector - Raw Data Extraction (Zero Transformation)

This script extracts raw data from VMware vCenter API with NO calculations
or conversions. It produces multiple data_type records for each VM:
- vmware_vm_config: Configuration data
- vmware_vm_runtime: Runtime state
- vmware_vm_storage: VM-Datastore relationships (one row per datastore)
- vmware_vm_perf_raw: Raw performance samples
- vmware_vm_perf_agg: Aggregated performance (optimization)

Output: Single JSON array to stdout containing all data_types
"""

import json
import ssl
import argparse
import sys
from datetime import datetime, timezone, timedelta
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='VMware VM Collector - Raw Data Extraction'
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


def extract_vm_config(vm, vcenter_uuid, collection_timestamp, hierarchy):
    """
    Extract VM configuration data AS-IS from VMware API.
    Source: vm.summary.config, vm.config
    """
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
        
        # vm.summary.config fields (AS-IS)
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
        
        # vm.config fields (AS-IS)
        "change_version": safe_get_attr(vm_config, 'changeVersion'),
        "modified": safe_timestamp(safe_get_attr(vm_config, 'modified')),
        "change_tracking_enabled": safe_get_attr(vm_config, 'changeTrackingEnabled'),
        "firmware": safe_get_attr(vm_config, 'firmware'),
        "max_mks_connections": safe_get_attr(vm_config, 'maxMksConnections'),
        "guest_auto_lock_enabled": safe_get_attr(vm_config, 'guestAutoLockEnabled'),
        "managed_by_extension_key": safe_get_attr(vm_config, 'managedBy.extensionKey'),
        "managed_by_type": safe_get_attr(vm_config, 'managedBy.type'),
        "version": safe_get_attr(vm_config, 'version'),
    }
    return serialize_record(record)


def extract_vm_runtime(vm, vcenter_uuid, collection_timestamp):
    """
    Extract VM runtime state AS-IS from VMware API.
    Source: vm.runtime, vm.guest, vm.summary.quickStats
    """
    runtime = vm.runtime
    guest = vm.guest
    qs = vm.summary.quickStats
    
    # Handle array fields - serialize to JSON strings for PostgreSQL compatibility
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
        
        # vm.runtime fields (AS-IS)
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
        
        # vm.guest fields (AS-IS)
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
        
        # vm.summary.quickStats (AS-IS, NO CONVERSION)
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
    """
    Extract VM-Datastore relationships AS-IS.
    Source: vm.datastore[], vm.summary.storage
    Returns: List of records (one per datastore)
    """
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
            
            # Datastore info (AS-IS)
            "datastore_name": safe_get_attr(ds, 'name'),
            "datastore_url": safe_get_attr(ds, 'summary.url'),
            "datastore_capacity": safe_get_attr(ds, 'summary.capacity'),
            "datastore_free_space": safe_get_attr(ds, 'summary.freeSpace'),
            "datastore_type": safe_get_attr(ds, 'summary.type'),
            "datastore_accessible": safe_get_attr(ds, 'summary.accessible'),
            "datastore_multiple_host_access": safe_get_attr(ds, 'summary.multipleHostAccess'),
            
            # VM storage usage (AS-IS)
            "committed": safe_get_attr(storage, 'committed'),
            "uncommitted": safe_get_attr(storage, 'uncommitted'),
            "unshared": safe_get_attr(storage, 'unshared'),
        }
        storage_records.append(serialize_record(record))
    
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


def extract_vm_perf_raw(vm, vcenter_uuid, collection_timestamp, perf_mgr, counter_ids, start_time, end_time, interval_id):
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
            entity=vm,
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
            
            # Calculate sample timestamps
            interval_seconds = interval_id
            for i, value in enumerate(perf_metric.value):
                sample_time = start_time + timedelta(seconds=i * interval_seconds)
                
                record = {
                    "data_type": "vmware_vm_perf_raw",
                    "collection_timestamp": collection_timestamp,
                    "vcenter_uuid": vcenter_uuid,
                    "vm_moid": vm._moId,
                    
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
                }
                perf_raw_records.append(serialize_record(record))
    
    except Exception as e:
        print(f"Warning: Failed to extract perf data for VM {vm._moId}: {e}", file=sys.stderr)
    
    return perf_raw_records


def calculate_vm_perf_agg(perf_raw_records, vcenter_uuid, collection_timestamp, start_time, end_time):
    """
    Calculate aggregated performance metrics from raw samples.
    This is an OPTIMIZATION table - same data can be derived from perf_raw via SQL.
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
                'vm_moid': record['vm_moid']
            }
        grouped[key]['values'].append(record['value'])
    
    # Calculate aggregates
    for (counter_id, instance), data in grouped.items():
        values = data['values']
        if not values:
            continue
        
        record = {
            "data_type": "vmware_vm_perf_agg",
            "collection_timestamp": collection_timestamp,
            "vcenter_uuid": vcenter_uuid,
            "vm_moid": data['vm_moid'],
            
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
            "value_stddev": None,  # Could calculate if needed
            "value_first": values[0],
            "value_last": values[-1],
        }
        perf_agg_records.append(serialize_record(record))
    
    return perf_agg_records


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
    # These will be retrieved dynamically from perfManager
    desired_counters = [
        'cpu.usage.average',
        'mem.usage.average',
        'disk.read.average',
        'disk.write.average',
        'net.usage.average'
    ]
    
    try:
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
        
        # Iterate through datacenter hierarchy
        for datacenter in content.rootFolder.childEntity:
            if not hasattr(datacenter, 'hostFolder'):
                continue
            
            datacenter_moid = datacenter._moId
            
            for entity in datacenter.hostFolder.childEntity:
                if not isinstance(entity, vim.ClusterComputeResource):
                    continue
                
                cluster_moid = entity._moId
                
                for host in entity.host:
                    host_moid = host._moId
                    hierarchy = {
                        'datacenter': datacenter_moid,
                        'cluster': cluster_moid,
                        'host': host_moid
                    }
                    
                    for vm in host.vm:
                        # Skip templates
                        if vm.config.template:
                            continue
                        
                        # Extract all data types for this VM
                        all_records.append(extract_vm_config(vm, vcenter_uuid, collection_timestamp, hierarchy))
                        all_records.append(extract_vm_runtime(vm, vcenter_uuid, collection_timestamp))
                        all_records.extend(extract_vm_storage(vm, vcenter_uuid, collection_timestamp))
                        
                        # Extract performance data
                        perf_raw = extract_vm_perf_raw(
                            vm, vcenter_uuid, collection_timestamp, perf_mgr,
                            counter_ids, start_time, end_time, args.perf_interval
                        )
                        all_records.extend(perf_raw)
                        
                        # Calculate aggregates
                        perf_agg = calculate_vm_perf_agg(
                            perf_raw, vcenter_uuid, collection_timestamp,
                            start_time, end_time
                        )
                        all_records.extend(perf_agg)
        
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
