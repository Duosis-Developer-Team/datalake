-- VMware Host Inventory View
-- Combines hardware, runtime, and storage data for each host at each collection timestamp
-- Purpose: Single view for all inventory/configuration data per host

CREATE OR REPLACE VIEW vmware_host_inventory AS
SELECT 
    -- Identification
    h.collection_timestamp,
    h.vcenter_uuid,
    h.datacenter_moid,
    h.cluster_moid,
    h.host_moid,
    
    -- Hardware Info
    h.vendor,
    h.model,
    h.uuid AS host_uuid,
    h.system_info_uuid AS bios_uuid,
    
    -- CPU Configuration
    h.cpu_model,
    h.cpu_mhz,
    h.num_cpu_pkgs AS cpu_sockets,
    h.num_cpu_cores,
    h.num_cpu_threads,
    ROUND((h.num_cpu_cores * h.cpu_mhz / 1000.0)::numeric, 2) AS total_cpu_ghz,
    
    -- Memory Configuration
    h.memory_size AS memory_bytes,
    ROUND((h.memory_size / (1024.0^3))::numeric, 2) AS memory_gb,
    
    -- Network & Storage Hardware
    h.num_nics,
    h.num_hbas,
    
    -- ESXi Software
    h.product_name AS esxi_name,
    h.product_full_name AS esxi_full_name,
    h.product_version AS esxi_version,
    h.product_build AS esxi_build,
    h.product_api_version AS api_version,
    
    -- Runtime State
    r.connection_state,
    r.power_state,
    r.standby_mode,
    r.in_maintenance_mode,
    r.in_quarantine_mode,
    r.boot_time,
    r.health_system_runtime_system_health_info AS health_status,
    r.config_name AS hostname,
    r.config_port AS management_port,
    
    -- Current Usage (QuickStats - Raw values from VMware)
    r.quick_stats_overall_cpu_usage AS current_cpu_mhz,
    r.quick_stats_overall_memory_usage AS current_memory_mb,
    r.quick_stats_uptime AS uptime_seconds,
    
    -- Calculated Usage Percentages
    CASE 
        WHEN h.num_cpu_cores > 0 AND h.cpu_mhz > 0 THEN
            ROUND(((r.quick_stats_overall_cpu_usage::numeric / (h.num_cpu_cores * h.cpu_mhz)) * 100)::numeric, 2)
        ELSE NULL
    END AS cpu_usage_percent,
    
    CASE 
        WHEN h.memory_size > 0 THEN
            ROUND(((r.quick_stats_overall_memory_usage::numeric * 1024 * 1024 / h.memory_size) * 100)::numeric, 2)
        ELSE NULL
    END AS memory_usage_percent,
    
    -- Calculated Free Resources
    CASE 
        WHEN h.num_cpu_cores > 0 AND h.cpu_mhz > 0 THEN
            ROUND(((h.num_cpu_cores * h.cpu_mhz - r.quick_stats_overall_cpu_usage) / 1000.0)::numeric, 2)
        ELSE NULL
    END AS free_cpu_ghz,
    
    CASE 
        WHEN h.memory_size > 0 THEN
            ROUND(((h.memory_size / (1024.0^3)) - (r.quick_stats_overall_memory_usage / 1024.0))::numeric, 2)
        ELSE NULL
    END AS free_memory_gb,
    
    -- Uptime (Human Readable)
    CASE 
        WHEN r.quick_stats_uptime > 0 THEN
            ROUND((r.quick_stats_uptime / 86400.0)::numeric, 1)
        ELSE NULL
    END AS uptime_days,
    
    -- Storage Summary (aggregated across all datastores)
    COUNT(DISTINCT s.datastore_moid) AS datastore_count,
    SUM(s.datastore_capacity) AS total_storage_bytes,
    SUM(s.datastore_free_space) AS total_storage_free_bytes,
    ROUND((SUM(s.datastore_capacity) / (1024.0^4))::numeric, 2) AS total_storage_tb,
    ROUND((SUM(s.datastore_free_space) / (1024.0^4))::numeric, 2) AS total_storage_free_tb,
    ROUND((SUM(s.datastore_capacity - s.datastore_free_space) / (1024.0^4))::numeric, 2) AS total_storage_used_tb,
    
    -- Storage Usage Percentage
    CASE 
        WHEN SUM(s.datastore_capacity) > 0 THEN
            ROUND((((SUM(s.datastore_capacity - s.datastore_free_space)::numeric / SUM(s.datastore_capacity)) * 100))::numeric, 2)
        ELSE NULL
    END AS storage_usage_percent,
    
    -- Datastore List (comma-separated)
    STRING_AGG(DISTINCT s.datastore_name, ', ' ORDER BY s.datastore_name) AS datastores

FROM 
    raw_vmware_host_hardware h
LEFT JOIN 
    raw_vmware_host_runtime r
    ON h.host_moid = r.host_moid 
    AND h.collection_timestamp = r.collection_timestamp
    AND h.vcenter_uuid = r.vcenter_uuid
LEFT JOIN 
    raw_vmware_host_storage s
    ON h.host_moid = s.host_moid 
    AND h.collection_timestamp = s.collection_timestamp
    AND h.vcenter_uuid = s.vcenter_uuid

GROUP BY 
    h.collection_timestamp,
    h.vcenter_uuid,
    h.datacenter_moid,
    h.cluster_moid,
    h.host_moid,
    h.vendor,
    h.model,
    h.uuid,
    h.system_info_uuid,
    h.cpu_model,
    h.cpu_mhz,
    h.num_cpu_pkgs,
    h.num_cpu_cores,
    h.num_cpu_threads,
    h.memory_size,
    h.num_nics,
    h.num_hbas,
    h.product_name,
    h.product_full_name,
    h.product_version,
    h.product_build,
    h.product_api_version,
    r.connection_state,
    r.power_state,
    r.standby_mode,
    r.in_maintenance_mode,
    r.in_quarantine_mode,
    r.boot_time,
    r.health_system_runtime_system_health_info,
    r.config_name,
    r.config_port,
    r.quick_stats_overall_cpu_usage,
    r.quick_stats_overall_memory_usage,
    r.quick_stats_uptime;

-- Example Usage:
-- SELECT * FROM vmware_host_inventory WHERE hostname = 'esxi01.example.com' ORDER BY collection_timestamp DESC LIMIT 1;
-- SELECT hostname, power_state, cpu_usage_percent, memory_usage_percent, storage_usage_percent FROM vmware_host_inventory WHERE power_state = 'poweredOn';
