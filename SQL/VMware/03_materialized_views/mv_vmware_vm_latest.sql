-- Materialized View: Latest VM Inventory Snapshot
-- Refreshed every 15 minutes for fast dashboard queries
-- Contains only the most recent collection timestamp

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vmware_vm_latest AS
SELECT 
    v.*,
    NOW() AS materialized_at
FROM vmware_vm_inventory v
WHERE v.collection_timestamp = (
    SELECT MAX(collection_timestamp) 
    FROM raw_vmware_vm_config
)
WITH DATA;

-- Unique index for CONCURRENTLY refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_vm_latest_pk 
    ON mv_vmware_vm_latest(vcenter_uuid, vm_moid);

-- Additional indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_mv_vm_latest_vcenter 
    ON mv_vmware_vm_latest(vcenter_name);

CREATE INDEX IF NOT EXISTS idx_mv_vm_latest_datacenter 
    ON mv_vmware_vm_latest(datacenter_name);

CREATE INDEX IF NOT EXISTS idx_mv_vm_latest_cluster 
    ON mv_vmware_vm_latest(cluster_name);

CREATE INDEX IF NOT EXISTS idx_mv_vm_latest_host 
    ON mv_vmware_vm_latest(host_name);

CREATE INDEX IF NOT EXISTS idx_mv_vm_latest_name 
    ON mv_vmware_vm_latest(vm_name);

CREATE INDEX IF NOT EXISTS idx_mv_vm_latest_folder 
    ON mv_vmware_vm_latest(folder_path);

CREATE INDEX IF NOT EXISTS idx_mv_vm_latest_power 
    ON mv_vmware_vm_latest(power_state);

CREATE INDEX IF NOT EXISTS idx_mv_vm_latest_template 
    ON mv_vmware_vm_latest(template) WHERE template = FALSE;

COMMENT ON MATERIALIZED VIEW mv_vmware_vm_latest IS 
    'Latest snapshot of VM inventory (refreshed every 15 minutes). 
     Use this for dashboards requiring current state only.';

-- Example Usage:
-- SELECT * FROM mv_vmware_vm_latest ORDER BY datacenter_name, cluster_name, vm_name;
-- SELECT COUNT(*) FROM mv_vmware_vm_latest WHERE power_state = 'poweredOn' AND template = FALSE;
