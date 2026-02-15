-- Materialized View: Latest Host Inventory Snapshot
-- Refreshed every 15 minutes for fast dashboard queries
-- Contains only the most recent collection timestamp

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vmware_host_latest AS
SELECT 
    h.*,
    NOW() AS materialized_at
FROM vmware_host_inventory h
WHERE h.collection_timestamp = (
    SELECT MAX(collection_timestamp) 
    FROM raw_vmware_host_hardware
)
WITH DATA;

-- Unique index for CONCURRENTLY refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_host_latest_pk 
    ON mv_vmware_host_latest(vcenter_uuid, host_moid);

-- Additional indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_mv_host_latest_vcenter 
    ON mv_vmware_host_latest(vcenter_name);

CREATE INDEX IF NOT EXISTS idx_mv_host_latest_datacenter 
    ON mv_vmware_host_latest(datacenter_name);

CREATE INDEX IF NOT EXISTS idx_mv_host_latest_cluster 
    ON mv_vmware_host_latest(cluster_name);

CREATE INDEX IF NOT EXISTS idx_mv_host_latest_name 
    ON mv_vmware_host_latest(host_name);

CREATE INDEX IF NOT EXISTS idx_mv_host_latest_connection 
    ON mv_vmware_host_latest(connection_state);

CREATE INDEX IF NOT EXISTS idx_mv_host_latest_maintenance 
    ON mv_vmware_host_latest(in_maintenance_mode) WHERE in_maintenance_mode = TRUE;

COMMENT ON MATERIALIZED VIEW mv_vmware_host_latest IS 
    'Latest snapshot of Host inventory (refreshed every 15 minutes). 
     Use this for dashboards requiring current state only.';

-- Example Usage:
-- SELECT * FROM mv_vmware_host_latest ORDER BY datacenter_name, cluster_name, host_name;
-- SELECT COUNT(*) FROM mv_vmware_host_latest WHERE connection_state = 'connected' AND in_maintenance_mode = FALSE;
