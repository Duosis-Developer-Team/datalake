-- Materialized View: Latest VM Performance Metrics
-- Contains performance metrics for the most recent collection window
-- Refreshed every 15 minutes

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vmware_vm_metrics_latest AS
SELECT 
    m.*,
    
    -- Add entity names via discovery
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    cl.name AS cluster_name,
    h.name AS host_name,
    
    -- VM name from config
    c.name AS vm_name,
    c.folder_path,
    
    NOW() AS materialized_at
    
FROM vmware_vm_metrics m

-- Get VM config for names and hierarchy
LEFT JOIN raw_vmware_vm_config c
    ON m.vm_moid = c.vm_moid
    AND m.vcenter_uuid = c.vcenter_uuid
    AND m.collection_timestamp = c.collection_timestamp

-- Discovery JOINs
LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON c.vcenter_uuid::text = vc.vcenter_uuid::text

LEFT JOIN discovery_vmware_inventory_datacenter dc
    ON c.vcenter_uuid::text = dc.vcenter_uuid::text
    AND c.datacenter_moid = dc.component_moid

LEFT JOIN discovery_vmware_inventory_cluster cl
    ON c.vcenter_uuid::text = cl.vcenter_uuid::text
    AND c.cluster_moid = cl.component_moid

LEFT JOIN discovery_vmware_inventory_host h
    ON c.vcenter_uuid::text = h.vcenter_uuid::text
    AND c.host_moid = h.component_moid

WHERE m.collection_timestamp = (
    SELECT MAX(collection_timestamp) 
    FROM raw_vmware_vm_perf_agg
)
WITH DATA;

-- Unique index for CONCURRENTLY refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_vm_metrics_latest_pk 
    ON mv_vmware_vm_metrics_latest(vcenter_uuid, vm_moid);

-- Additional indexes
CREATE INDEX IF NOT EXISTS idx_mv_vm_metrics_latest_vcenter 
    ON mv_vmware_vm_metrics_latest(vcenter_name);

CREATE INDEX IF NOT EXISTS idx_mv_vm_metrics_latest_datacenter 
    ON mv_vmware_vm_metrics_latest(datacenter_name);

CREATE INDEX IF NOT EXISTS idx_mv_vm_metrics_latest_cluster 
    ON mv_vmware_vm_metrics_latest(cluster_name);

CREATE INDEX IF NOT EXISTS idx_mv_vm_metrics_latest_name 
    ON mv_vmware_vm_metrics_latest(vm_name);

CREATE INDEX IF NOT EXISTS idx_mv_vm_metrics_latest_folder 
    ON mv_vmware_vm_metrics_latest(folder_path);

COMMENT ON MATERIALIZED VIEW mv_vmware_vm_metrics_latest IS 
    'Latest VM performance metrics with entity names (refreshed every 15 minutes). 
     Use this for performance dashboards showing current metrics.';

-- Example Usage:
-- SELECT vm_name, cpu_usage_avg_mhz, mem_usage_avg_percent, disk_usage_avg_kbps 
-- FROM mv_vmware_vm_metrics_latest 
-- ORDER BY cpu_usage_avg_mhz DESC LIMIT 10;
