-- VMware Host Inventory View (Enhanced with Discovery Integration)
-- Combines hardware, runtime, storage data + entity names from discovery tables
-- Purpose: Complete host inventory view with human-readable entity names

CREATE OR REPLACE VIEW vmware_host_inventory AS
SELECT 
    -- Identification
    h.collection_timestamp,
    h.vcenter_uuid,
    h.datacenter_moid,
    h.cluster_moid,
    h.host_moid,
    
    -- Entity Names (from discovery tables)
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    vc.vcenter_hostname AS vcenter_hostname,
    COALESCE(SPLIT_PART(cl.name, '-', 1), SPLIT_PART(cluster_cfg.name, '-', 1)) AS location,
    COALESCE(cl.name, cluster_cfg.name) AS cluster_name,
    host_disc.name AS host_name,
    
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

-- Discovery JOINs (entity names)
LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON h.vcenter_uuid::text = vc.vcenter_uuid::text

LEFT JOIN discovery_vmware_inventory_datacenter dc
    ON h.vcenter_uuid::text = dc.vcenter_uuid::text
    AND h.datacenter_moid = dc.component_moid

LEFT JOIN discovery_vmware_inventory_cluster cl
    ON h.vcenter_uuid::text = cl.vcenter_uuid::text
    AND h.cluster_moid = cl.component_moid
LEFT JOIN (
    SELECT DISTINCT ON (vcenter_uuid, cluster_moid) vcenter_uuid, cluster_moid, name
    FROM raw_vmware_cluster_config
    ORDER BY vcenter_uuid, cluster_moid, collection_timestamp DESC
) cluster_cfg
    ON h.vcenter_uuid::text = cluster_cfg.vcenter_uuid
    AND h.cluster_moid = cluster_cfg.cluster_moid

LEFT JOIN discovery_vmware_inventory_host host_disc
    ON h.vcenter_uuid::text = host_disc.vcenter_uuid::text
    AND h.host_moid = host_disc.component_moid

-- Collector data JOINs
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
    vc.name,
    vc.vcenter_hostname,
    dc.name,
    cl.name,
    cluster_cfg.name,
    host_disc.name,
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
-- Latest snapshot with entity names:
-- SELECT * FROM vmware_host_inventory 
-- WHERE collection_timestamp = (SELECT MAX(collection_timestamp) FROM raw_vmware_host_hardware)
-- ORDER BY datacenter_name, cluster_name, host_name;
--
-- Find hosts with issues:
-- SELECT datacenter_name, cluster_name, host_name, connection_state, in_maintenance_mode
-- FROM vmware_host_inventory 
-- WHERE connection_state != 'connected' OR in_maintenance_mode = TRUE;
