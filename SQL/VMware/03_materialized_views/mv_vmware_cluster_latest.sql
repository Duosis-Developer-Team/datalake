-- Materialized View: Latest Cluster Summary
-- Aggregates host-level data to provide cluster-level metrics
-- Refreshed every 15 minutes

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vmware_cluster_latest AS
SELECT 
    cl.vcenter_uuid,
    cl.component_moid AS cluster_moid,
    
    -- Entity Names
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    vc.vcenter_hostname AS vcenter_hostname,
    SPLIT_PART(cl.name, '-', 1) AS location,
    cl.name AS cluster_name,
    
    -- Cluster Status
    cl.status AS cluster_status,
    cl.last_observed AS discovery_last_observed,
    
    -- Host Counts
    COUNT(DISTINCT h.host_moid) AS total_hosts,
    COUNT(DISTINCT h.host_moid) FILTER (WHERE rt.connection_state = 'connected') AS connected_hosts,
    COUNT(DISTINCT h.host_moid) FILTER (WHERE rt.in_maintenance_mode = TRUE) AS maintenance_hosts,
    COUNT(DISTINCT h.host_moid) FILTER (WHERE rt.connection_state != 'connected') AS disconnected_hosts,
    
    -- CPU Capacity
    SUM(h.num_cpu_cores) AS total_cpu_cores,
    SUM(h.num_cpu_pkgs) AS total_cpu_sockets,
    SUM(h.num_cpu_cores * h.cpu_mhz) AS total_cpu_mhz,
    ROUND((SUM(h.num_cpu_cores * h.cpu_mhz) / 1000.0)::numeric, 2) AS total_cpu_ghz,
    
    -- Memory Capacity
    SUM(h.memory_size) AS total_memory_bytes,
    ROUND((SUM(h.memory_size) / (1024.0^3))::numeric, 2) AS total_memory_gb,
    
    -- Current CPU Usage
    SUM(rt.quick_stats_overall_cpu_usage) AS current_cpu_usage_mhz,
    ROUND((SUM(rt.quick_stats_overall_cpu_usage) / 1000.0)::numeric, 2) AS current_cpu_usage_ghz,
    
    -- Current Memory Usage
    SUM(rt.quick_stats_overall_memory_usage) AS current_memory_usage_mb,
    ROUND((SUM(rt.quick_stats_overall_memory_usage) / 1024.0)::numeric, 2) AS current_memory_usage_gb,
    
    -- Free Resources
    ROUND(((SUM(h.num_cpu_cores * h.cpu_mhz) - SUM(rt.quick_stats_overall_cpu_usage)) / 1000.0)::numeric, 2) AS free_cpu_ghz,
    ROUND(((SUM(h.memory_size) / (1024.0^3)) - (SUM(rt.quick_stats_overall_memory_usage) / 1024.0))::numeric, 2) AS free_memory_gb,
    
    -- Usage Percentages
    CASE 
        WHEN SUM(h.num_cpu_cores * h.cpu_mhz) > 0 THEN 
            ROUND((SUM(rt.quick_stats_overall_cpu_usage)::numeric / SUM(h.num_cpu_cores * h.cpu_mhz)) * 100, 2)
        ELSE NULL 
    END AS cpu_usage_percent,
    
    CASE 
        WHEN SUM(h.memory_size) > 0 THEN 
            ROUND(((SUM(rt.quick_stats_overall_memory_usage) * 1024.0 * 1024.0)::numeric / SUM(h.memory_size)) * 100, 2)
        ELSE NULL 
    END AS memory_usage_percent,
    
    -- Timing
    MAX(h.collection_timestamp) AS collection_timestamp,
    NOW() AS materialized_at
    
FROM discovery_vmware_inventory_cluster cl

-- Discovery hierarchy
LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON cl.vcenter_uuid = vc.vcenter_uuid

LEFT JOIN discovery_vmware_inventory_datacenter dc
    ON cl.vcenter_uuid = dc.vcenter_uuid
    AND cl.parent_component_moid = dc.component_moid

-- Host hardware (from collectors)
LEFT JOIN raw_vmware_host_hardware h
    ON cl.vcenter_uuid::text = h.vcenter_uuid
    AND cl.component_moid = h.cluster_moid
    AND h.collection_timestamp = (
        SELECT MAX(collection_timestamp) 
        FROM raw_vmware_host_hardware
    )

-- Host runtime (from collectors)
LEFT JOIN raw_vmware_host_runtime rt
    ON h.host_moid = rt.host_moid
    AND h.collection_timestamp = rt.collection_timestamp
    AND h.vcenter_uuid = rt.vcenter_uuid

GROUP BY 
    cl.vcenter_uuid,
    cl.component_moid,
    vc.vcenter_hostname,
    vc.name,
    dc.name,
    cl.name,
    cl.status,
    cl.last_observed
WITH DATA;

-- Unique index for CONCURRENTLY refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_cluster_latest_pk 
    ON mv_vmware_cluster_latest(vcenter_uuid, cluster_moid);

-- Additional indexes
CREATE INDEX IF NOT EXISTS idx_mv_cluster_latest_vcenter 
    ON mv_vmware_cluster_latest(vcenter_name);

CREATE INDEX IF NOT EXISTS idx_mv_cluster_latest_datacenter 
    ON mv_vmware_cluster_latest(datacenter_name);

CREATE INDEX IF NOT EXISTS idx_mv_cluster_latest_location 
    ON mv_vmware_cluster_latest(location);

CREATE INDEX IF NOT EXISTS idx_mv_cluster_latest_name 
    ON mv_vmware_cluster_latest(cluster_name);

COMMENT ON MATERIALIZED VIEW mv_vmware_cluster_latest IS 
    'Latest cluster summary with aggregated host metrics (refreshed every 15 minutes). 
     Use this for cluster capacity planning and overview dashboards.';

-- Example Usage:
-- SELECT * FROM mv_vmware_cluster_latest ORDER BY datacenter_name, cluster_name;
-- SELECT cluster_name, total_hosts, cpu_usage_percent, memory_usage_percent FROM mv_vmware_cluster_latest WHERE cpu_usage_percent > 80;
