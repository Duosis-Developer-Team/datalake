-- VMware Host Capacity Planning View
-- Provides capacity metrics for resource planning and threshold alerting
-- Purpose: Monitor resource utilization trends for capacity management

CREATE OR REPLACE VIEW vmware_host_capacity AS
SELECT 
    h.collection_timestamp,
    h.vcenter_uuid,
    h.datacenter_moid,
    h.cluster_moid,
    h.host_moid,
    r.config_name AS hostname,
    r.power_state,
    r.connection_state,
    
    -- Entity Names (from discovery)
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    vc.vcenter_hostname AS vcenter_hostname,
    COALESCE(SPLIT_PART(cl.name, '-', 1), SPLIT_PART(cluster_cfg.name, '-', 1)) AS location,
    COALESCE(cl.name, cluster_cfg.name) AS cluster_name,
    
    -- CPU Capacity
    h.num_cpu_cores AS cpu_total_cores,
    h.num_cpu_threads AS cpu_total_threads,
    h.cpu_mhz AS cpu_core_mhz,
    (h.num_cpu_cores * h.cpu_mhz) AS cpu_total_capacity_mhz,
    ROUND((h.num_cpu_cores * h.cpu_mhz / 1000.0)::numeric, 2) AS cpu_total_capacity_ghz,
    
    -- CPU Current Usage
    r.quick_stats_overall_cpu_usage AS cpu_current_usage_mhz,
    ROUND((r.quick_stats_overall_cpu_usage / 1000.0)::numeric, 2) AS cpu_current_usage_ghz,
    
    -- CPU Capacity Metrics
    CASE 
        WHEN h.num_cpu_cores > 0 AND h.cpu_mhz > 0 THEN
            ROUND(((r.quick_stats_overall_cpu_usage::numeric / (h.num_cpu_cores * h.cpu_mhz)) * 100)::numeric, 2)
        ELSE NULL
    END AS cpu_usage_percent,
    
    CASE 
        WHEN h.num_cpu_cores > 0 AND h.cpu_mhz > 0 THEN
            (h.num_cpu_cores * h.cpu_mhz) - r.quick_stats_overall_cpu_usage
        ELSE NULL
    END AS cpu_free_mhz,
    
    CASE 
        WHEN h.num_cpu_cores > 0 AND h.cpu_mhz > 0 THEN
            ROUND(((h.num_cpu_cores * h.cpu_mhz - r.quick_stats_overall_cpu_usage) / 1000.0)::numeric, 2)
        ELSE NULL
    END AS cpu_free_ghz,
    
    -- CPU Threshold Flags (80% warning, 90% critical)
    CASE 
        WHEN h.num_cpu_cores > 0 AND h.cpu_mhz > 0 THEN
            CASE 
                WHEN (r.quick_stats_overall_cpu_usage::numeric / (h.num_cpu_cores * h.cpu_mhz)) * 100 >= 90 THEN 'CRITICAL'
                WHEN (r.quick_stats_overall_cpu_usage::numeric / (h.num_cpu_cores * h.cpu_mhz)) * 100 >= 80 THEN 'WARNING'
                ELSE 'OK'
            END
        ELSE 'UNKNOWN'
    END AS cpu_threshold_status,
    
    -- Memory Capacity
    h.memory_size AS memory_total_bytes,
    ROUND((h.memory_size / (1024.0^2))::numeric, 2) AS memory_total_mb,
    ROUND((h.memory_size / (1024.0^3))::numeric, 2) AS memory_total_gb,
    
    -- Memory Current Usage
    (r.quick_stats_overall_memory_usage * 1024 * 1024) AS memory_current_usage_bytes,
    r.quick_stats_overall_memory_usage AS memory_current_usage_mb,
    ROUND((r.quick_stats_overall_memory_usage / 1024.0)::numeric, 2) AS memory_current_usage_gb,
    
    -- Memory Capacity Metrics
    CASE 
        WHEN h.memory_size > 0 THEN
            ROUND(((r.quick_stats_overall_memory_usage::numeric * 1024 * 1024 / h.memory_size) * 100)::numeric, 2)
        ELSE NULL
    END AS memory_usage_percent,
    
    CASE 
        WHEN h.memory_size > 0 THEN
            h.memory_size - (r.quick_stats_overall_memory_usage * 1024 * 1024)
        ELSE NULL
    END AS memory_free_bytes,
    
    CASE 
        WHEN h.memory_size > 0 THEN
            ROUND(((h.memory_size - (r.quick_stats_overall_memory_usage * 1024 * 1024)) / (1024.0^3))::numeric, 2)
        ELSE NULL
    END AS memory_free_gb,
    
    -- Memory Threshold Flags (80% warning, 90% critical)
    CASE 
        WHEN h.memory_size > 0 THEN
            CASE 
                WHEN (r.quick_stats_overall_memory_usage::numeric * 1024 * 1024 / h.memory_size) * 100 >= 90 THEN 'CRITICAL'
                WHEN (r.quick_stats_overall_memory_usage::numeric * 1024 * 1024 / h.memory_size) * 100 >= 80 THEN 'WARNING'
                ELSE 'OK'
            END
        ELSE 'UNKNOWN'
    END AS memory_threshold_status,
    
    -- Storage Capacity (aggregated)
    SUM(s.datastore_capacity) AS storage_total_bytes,
    ROUND((SUM(s.datastore_capacity) / (1024.0^4))::numeric, 2) AS storage_total_tb,
    
    -- Storage Usage
    SUM(s.datastore_capacity - s.datastore_free_space) AS storage_used_bytes,
    ROUND((SUM(s.datastore_capacity - s.datastore_free_space) / (1024.0^4))::numeric, 2) AS storage_used_tb,
    
    SUM(s.datastore_free_space) AS storage_free_bytes,
    ROUND((SUM(s.datastore_free_space) / (1024.0^4))::numeric, 2) AS storage_free_tb,
    
    -- Storage Capacity Metrics
    CASE 
        WHEN SUM(s.datastore_capacity) > 0 THEN
            ROUND((((SUM(s.datastore_capacity - s.datastore_free_space)::numeric / SUM(s.datastore_capacity)) * 100))::numeric, 2)
        ELSE NULL
    END AS storage_usage_percent,
    
    -- Storage Threshold Flags (80% warning, 90% critical)
    CASE 
        WHEN SUM(s.datastore_capacity) > 0 THEN
            CASE 
                WHEN ((SUM(s.datastore_capacity - s.datastore_free_space)::numeric / SUM(s.datastore_capacity)) * 100) >= 90 THEN 'CRITICAL'
                WHEN ((SUM(s.datastore_capacity - s.datastore_free_space)::numeric / SUM(s.datastore_capacity)) * 100) >= 80 THEN 'WARNING'
                ELSE 'OK'
            END
        ELSE 'UNKNOWN'
    END AS storage_threshold_status,
    
    -- Overall Capacity Status (worst of CPU/Memory/Storage)
    CASE 
        WHEN 
            (h.num_cpu_cores > 0 AND h.cpu_mhz > 0 AND (r.quick_stats_overall_cpu_usage::numeric / (h.num_cpu_cores * h.cpu_mhz)) * 100 >= 90)
            OR (h.memory_size > 0 AND (r.quick_stats_overall_memory_usage::numeric * 1024 * 1024 / h.memory_size) * 100 >= 90)
            OR (SUM(s.datastore_capacity) > 0 AND ((SUM(s.datastore_capacity - s.datastore_free_space)::numeric / SUM(s.datastore_capacity)) * 100) >= 90)
        THEN 'CRITICAL'
        WHEN 
            (h.num_cpu_cores > 0 AND h.cpu_mhz > 0 AND (r.quick_stats_overall_cpu_usage::numeric / (h.num_cpu_cores * h.cpu_mhz)) * 100 >= 80)
            OR (h.memory_size > 0 AND (r.quick_stats_overall_memory_usage::numeric * 1024 * 1024 / h.memory_size) * 100 >= 80)
            OR (SUM(s.datastore_capacity) > 0 AND ((SUM(s.datastore_capacity - s.datastore_free_space)::numeric / SUM(s.datastore_capacity)) * 100) >= 80)
        THEN 'WARNING'
        ELSE 'OK'
    END AS overall_capacity_status,
    
    -- Datastore Count
    COUNT(DISTINCT s.datastore_moid) AS datastore_count

FROM 
    raw_vmware_host_hardware h
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
    r.config_name,
    vc.vcenter_hostname,
    vc.name,
    cl.name,
    cluster_cfg.name,
    dc.name,
    r.power_state,
    r.connection_state,
    h.num_cpu_cores,
    h.num_cpu_threads,
    h.cpu_mhz,
    h.memory_size,
    r.quick_stats_overall_cpu_usage,
    r.quick_stats_overall_memory_usage;

-- Example Usage:
-- Show hosts with critical capacity issues:
-- SELECT hostname, overall_capacity_status, cpu_usage_percent, memory_usage_percent, storage_usage_percent FROM vmware_host_capacity WHERE overall_capacity_status = 'CRITICAL';

-- Show hosts needing capacity planning:
-- SELECT hostname, cpu_free_ghz, memory_free_gb, storage_free_tb FROM vmware_host_capacity WHERE overall_capacity_status IN ('WARNING', 'CRITICAL');
