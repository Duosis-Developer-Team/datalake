-- Materialized View: Latest Datacenter Summary
-- Aggregates cluster and host data to provide datacenter-level metrics
-- Refreshed every 15 minutes

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vmware_datacenter_latest AS
SELECT 
    dc.vcenter_uuid,
    dc.component_moid AS datacenter_moid,
    
    -- Entity Names
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    vc.vcenter_hostname AS vcenter_hostname,
    array_agg(DISTINCT SPLIT_PART(cl.name, '-', 1)) FILTER (WHERE cl.name IS NOT NULL) AS locations,
    
    -- Datacenter Status
    dc.status AS datacenter_status,
    dc.last_observed AS discovery_last_observed,
    
    -- Cluster Counts
    COUNT(DISTINCT cl.component_moid) AS total_clusters,
    
    -- Host Counts
    COUNT(DISTINCT h.host_moid) AS total_hosts,
    COUNT(DISTINCT h.host_moid) FILTER (WHERE rt.connection_state = 'connected') AS connected_hosts,
    COUNT(DISTINCT h.host_moid) FILTER (WHERE rt.in_maintenance_mode = TRUE) AS maintenance_hosts,
    
    -- CPU Capacity
    SUM(h.num_cpu_cores) AS total_cpu_cores,
    ROUND((SUM(h.num_cpu_cores * h.cpu_mhz) / 1000.0)::numeric, 2) AS total_cpu_ghz,
    
    -- Memory Capacity
    ROUND((SUM(h.memory_size) / (1024.0^3))::numeric, 2) AS total_memory_gb,
    
    -- Current Usage
    ROUND((SUM(rt.quick_stats_overall_cpu_usage) / 1000.0)::numeric, 2) AS current_cpu_usage_ghz,
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
    
FROM discovery_vmware_inventory_datacenter dc

-- vCenter info
LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON dc.vcenter_uuid = vc.vcenter_uuid

-- Clusters in this datacenter
LEFT JOIN discovery_vmware_inventory_cluster cl
    ON dc.vcenter_uuid = cl.vcenter_uuid
    AND dc.component_moid = cl.parent_component_moid

-- Hosts in these clusters
LEFT JOIN raw_vmware_host_hardware h
    ON cl.vcenter_uuid::text = h.vcenter_uuid
    AND cl.component_moid = h.cluster_moid
    AND h.collection_timestamp = (
        SELECT MAX(collection_timestamp) 
        FROM raw_vmware_host_hardware
    )

-- Host runtime
LEFT JOIN raw_vmware_host_runtime rt
    ON h.host_moid = rt.host_moid
    AND h.collection_timestamp = rt.collection_timestamp
    AND h.vcenter_uuid = rt.vcenter_uuid

GROUP BY 
    dc.vcenter_uuid,
    dc.component_moid,
    vc.vcenter_hostname,
    vc.name,
    dc.name,
    dc.status,
    dc.last_observed
WITH DATA;

-- Unique index for CONCURRENTLY refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_datacenter_latest_pk 
    ON mv_vmware_datacenter_latest(vcenter_uuid, datacenter_moid);

-- Additional indexes
CREATE INDEX IF NOT EXISTS idx_mv_datacenter_latest_vcenter 
    ON mv_vmware_datacenter_latest(vcenter_name);

CREATE INDEX IF NOT EXISTS idx_mv_datacenter_latest_name 
    ON mv_vmware_datacenter_latest(datacenter_name);

COMMENT ON MATERIALIZED VIEW mv_vmware_datacenter_latest IS 
    'Latest datacenter summary with aggregated metrics (refreshed every 15 minutes). 
     Use this for datacenter-level capacity planning and overview dashboards.';

-- Example Usage:
-- SELECT * FROM mv_vmware_datacenter_latest ORDER BY vcenter_name, datacenter_name;
-- SELECT datacenter_name, total_clusters, total_hosts, cpu_usage_percent, memory_usage_percent FROM mv_vmware_datacenter_latest;
