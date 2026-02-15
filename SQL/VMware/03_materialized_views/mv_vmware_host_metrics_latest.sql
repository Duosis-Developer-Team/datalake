-- Materialized View: Latest Host Performance Metrics
-- Contains performance metrics for the most recent collection window
-- Refreshed every 15 minutes

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vmware_host_metrics_latest AS
SELECT 
    m.*,
    
    -- Add entity names via discovery
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    cl.name AS cluster_name,
    h_disc.name AS host_name,
    
    -- Power metrics (if available)
    pm.power_avg_watts,
    pm.power_min_watts,
    pm.power_max_watts,
    
    NOW() AS materialized_at
    
FROM vmware_host_metrics m

-- Get host hardware for hierarchy
LEFT JOIN raw_vmware_host_hardware h
    ON m.host_moid = h.host_moid
    AND m.vcenter_uuid = h.vcenter_uuid
    AND m.collection_timestamp = h.collection_timestamp

-- Discovery JOINs
LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON h.vcenter_uuid::text = vc.vcenter_uuid::text

LEFT JOIN discovery_vmware_inventory_datacenter dc
    ON h.vcenter_uuid::text = dc.vcenter_uuid::text
    AND h.datacenter_moid = dc.component_moid

LEFT JOIN discovery_vmware_inventory_cluster cl
    ON h.vcenter_uuid::text = cl.vcenter_uuid::text
    AND h.cluster_moid = cl.component_moid

LEFT JOIN discovery_vmware_inventory_host h_disc
    ON h.vcenter_uuid::text = h_disc.vcenter_uuid::text
    AND h.host_moid = h_disc.component_moid

-- Power metrics (from perf_agg table)
LEFT JOIN LATERAL (
    SELECT 
        AVG(value_avg) FILTER (WHERE counter_name = 'power.power.average') AS power_avg_watts,
        MIN(value_min) FILTER (WHERE counter_name = 'power.power.average') AS power_min_watts,
        MAX(value_max) FILTER (WHERE counter_name = 'power.power.average') AS power_max_watts
    FROM raw_vmware_host_perf_agg
    WHERE host_moid = m.host_moid
      AND collection_timestamp = m.collection_timestamp
      AND vcenter_uuid = m.vcenter_uuid
      AND counter_name = 'power.power.average'
) pm ON TRUE

WHERE m.collection_timestamp = (
    SELECT MAX(collection_timestamp) 
    FROM raw_vmware_host_perf_agg
)
WITH DATA;

-- Unique index for CONCURRENTLY refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_host_metrics_latest_pk 
    ON mv_vmware_host_metrics_latest(vcenter_uuid, host_moid);

-- Additional indexes
CREATE INDEX IF NOT EXISTS idx_mv_host_metrics_latest_vcenter 
    ON mv_vmware_host_metrics_latest(vcenter_name);

CREATE INDEX IF NOT EXISTS idx_mv_host_metrics_latest_datacenter 
    ON mv_vmware_host_metrics_latest(datacenter_name);

CREATE INDEX IF NOT EXISTS idx_mv_host_metrics_latest_cluster 
    ON mv_vmware_host_metrics_latest(cluster_name);

CREATE INDEX IF NOT EXISTS idx_mv_host_metrics_latest_name 
    ON mv_vmware_host_metrics_latest(host_name);

COMMENT ON MATERIALIZED VIEW mv_vmware_host_metrics_latest IS 
    'Latest host performance metrics with entity names and power data (refreshed every 15 minutes). 
     Use this for host performance dashboards.';

-- Example Usage:
-- SELECT host_name, cpu_usage_avg_mhz, mem_usage_avg_percent, power_avg_watts 
-- FROM mv_vmware_host_metrics_latest 
-- ORDER BY cpu_usage_avg_mhz DESC LIMIT 10;
