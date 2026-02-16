-- VMware VM Inventory View (Enhanced with Discovery Integration)
-- Combines config, runtime, storage data + entity names from discovery tables
-- Purpose: Complete VM inventory view with human-readable entity names

CREATE OR REPLACE VIEW vmware_vm_inventory AS
SELECT 
    -- Identification
    c.collection_timestamp,
    c.vcenter_uuid,
    c.datacenter_moid,
    c.cluster_moid,
    c.host_moid,
    c.vm_moid,
    
    -- Entity Names (from discovery tables)
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    vc.vcenter_hostname AS vcenter_hostname,
    COALESCE(SPLIT_PART(cl.name, '-', 1), SPLIT_PART(cluster_cfg.name, '-', 1)) AS location,
    COALESCE(cl.name, cluster_cfg.name) AS cluster_name,
    h.name AS host_name,
    h.component_uuid AS host_uuid,
    
    -- Config Data
    c.name AS vm_name,
    c.folder_path,
    c.template,
    c.vm_path_name,
    c.num_cpu,
    c.memory_size_mb,
    c.cpu_reservation,
    c.memory_reservation,
    c.num_ethernet_cards,
    c.num_virtual_disks,
    c.uuid,
    c.instance_uuid,
    c.guest_id,
    c.guest_full_name AS configured_guest_os,
    c.annotation,
    c.firmware,
    c.version AS vm_hardware_version,
    
    -- Runtime State
    r.power_state,
    r.connection_state,
    r.boot_time,
    r.suspend_time,
    r.suspend_interval,
    r.consolidation_needed,
    
    -- Guest Tools
    r.guest_tools_status,
    r.guest_tools_version,
    r.guest_tools_running_status,
    r.guest_tools_version_status,
    
    -- Guest Info (from tools)
    r.guest_guest_id AS actual_guest_id,
    r.guest_guest_family,
    r.guest_guest_full_name AS actual_guest_os,
    r.guest_host_name,
    r.guest_ip_address,
    r.guest_guest_state,
    
    -- Resource Limits
    r.max_cpu_usage AS max_cpu_mhz,
    r.max_memory_usage AS max_memory_mb,
    
    -- Quick Stats (Current Usage)
    r.quick_stats_overall_cpu_usage AS current_cpu_mhz,
    r.quick_stats_overall_cpu_demand AS current_cpu_demand_mhz,
    r.quick_stats_guest_memory_usage AS current_guest_memory_mb,
    r.quick_stats_host_memory_usage AS current_host_memory_mb,
    r.quick_stats_guest_heartbeat_status,
    r.quick_stats_private_memory AS private_memory_mb,
    r.quick_stats_shared_memory AS shared_memory_mb,
    r.quick_stats_swapped_memory AS swapped_memory_mb,
    r.quick_stats_ballooned_memory AS ballooned_memory_mb,
    r.quick_stats_compressed_memory AS compressed_memory_mb,
    r.quick_stats_uptime_seconds AS uptime_seconds,
    
    -- Storage Summary (aggregated across all datastores)
    SUM(s.committed) AS total_committed_bytes,
    SUM(s.uncommitted) AS total_uncommitted_bytes,
    SUM(s.unshared) AS total_unshared_bytes,
    SUM(s.committed + s.uncommitted) AS total_provisioned_bytes,
    
    -- Calculated Fields (Human Readable)
    ROUND((c.memory_size_mb / 1024.0)::numeric, 2) AS memory_size_gb,
    ROUND((SUM(s.committed) / (1024.0^3))::numeric, 2) AS committed_gb,
    ROUND((SUM(s.uncommitted) / (1024.0^3))::numeric, 2) AS uncommitted_gb,
    ROUND((SUM(s.committed + s.uncommitted) / (1024.0^3))::numeric, 2) AS provisioned_gb,
    
    -- CPU Usage Percentage
    CASE 
        WHEN r.max_cpu_usage > 0 THEN 
            ROUND((r.quick_stats_overall_cpu_usage::numeric / r.max_cpu_usage) * 100, 2)
        ELSE NULL 
    END AS cpu_usage_percent,
    
    -- Memory Usage Percentage
    CASE 
        WHEN c.memory_size_mb > 0 THEN 
            ROUND((r.quick_stats_host_memory_usage::numeric / c.memory_size_mb) * 100, 2)
        ELSE NULL 
    END AS memory_usage_percent,
    
    -- Datastore List (comma-separated)
    STRING_AGG(DISTINCT s.datastore_name, ', ' ORDER BY s.datastore_name) AS datastores,
    COUNT(DISTINCT s.datastore_moid) AS datastore_count

FROM 
    raw_vmware_vm_config c

-- Discovery JOINs (entity names)
LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON c.vcenter_uuid::text = vc.vcenter_uuid::text

LEFT JOIN discovery_vmware_inventory_datacenter dc
    ON c.vcenter_uuid::text = dc.vcenter_uuid::text
    AND c.datacenter_moid = dc.component_moid

LEFT JOIN discovery_vmware_inventory_cluster cl
    ON c.vcenter_uuid::text = cl.vcenter_uuid::text
    AND c.cluster_moid = cl.component_moid
LEFT JOIN (
    SELECT DISTINCT ON (vcenter_uuid, cluster_moid) vcenter_uuid, cluster_moid, name
    FROM raw_vmware_cluster_config
    ORDER BY vcenter_uuid, cluster_moid, collection_timestamp DESC
) cluster_cfg
    ON c.vcenter_uuid::text = cluster_cfg.vcenter_uuid
    AND c.cluster_moid = cluster_cfg.cluster_moid

LEFT JOIN discovery_vmware_inventory_host h
    ON c.vcenter_uuid::text = h.vcenter_uuid::text
    AND c.host_moid = h.component_moid

-- Collector data JOINs
LEFT JOIN 
    raw_vmware_vm_runtime r 
    ON c.vm_moid = r.vm_moid 
    AND c.collection_timestamp = r.collection_timestamp
    AND c.vcenter_uuid = r.vcenter_uuid
LEFT JOIN 
    raw_vmware_vm_storage s 
    ON c.vm_moid = s.vm_moid 
    AND c.collection_timestamp = s.collection_timestamp
    AND c.vcenter_uuid = s.vcenter_uuid

GROUP BY 
    c.collection_timestamp,
    c.vcenter_uuid,
    c.datacenter_moid,
    c.cluster_moid,
    c.host_moid,
    c.vm_moid,
    vc.name,
    vc.vcenter_hostname,
    dc.name,
    cl.name,
    cluster_cfg.name,
    h.name,
    h.component_uuid,
    c.name,
    c.folder_path,
    c.template,
    c.vm_path_name,
    c.num_cpu,
    c.memory_size_mb,
    c.cpu_reservation,
    c.memory_reservation,
    c.num_ethernet_cards,
    c.num_virtual_disks,
    c.uuid,
    c.instance_uuid,
    c.guest_id,
    c.guest_full_name,
    c.annotation,
    c.firmware,
    c.version,
    r.power_state,
    r.connection_state,
    r.boot_time,
    r.suspend_time,
    r.suspend_interval,
    r.consolidation_needed,
    r.guest_tools_status,
    r.guest_tools_version,
    r.guest_tools_running_status,
    r.guest_tools_version_status,
    r.guest_guest_id,
    r.guest_guest_family,
    r.guest_guest_full_name,
    r.guest_host_name,
    r.guest_ip_address,
    r.guest_guest_state,
    r.max_cpu_usage,
    r.max_memory_usage,
    r.quick_stats_overall_cpu_usage,
    r.quick_stats_overall_cpu_demand,
    r.quick_stats_guest_memory_usage,
    r.quick_stats_host_memory_usage,
    r.quick_stats_guest_heartbeat_status,
    r.quick_stats_private_memory,
    r.quick_stats_shared_memory,
    r.quick_stats_swapped_memory,
    r.quick_stats_ballooned_memory,
    r.quick_stats_compressed_memory,
    r.quick_stats_uptime_seconds;

-- Example Usage:
-- Latest snapshot with entity names:
-- SELECT * FROM vmware_vm_inventory 
-- WHERE collection_timestamp = (SELECT MAX(collection_timestamp) FROM raw_vmware_vm_config)
-- ORDER BY datacenter_name, cluster_name, folder_path, vm_name;
--
-- Filter by folder:
-- SELECT datacenter_name, cluster_name, folder_path, vm_name, power_state, cpu_usage_percent
-- FROM vmware_vm_inventory 
-- WHERE folder_path LIKE 'production/%' AND power_state = 'poweredOn';
