-- Materialized View: Latest Datacenter Performance Metrics
-- One row per datacenter for the most recent collection_timestamp from raw_vmware_datacenter_metrics_agg
-- Refreshed every 15 minutes; use for datacenter metrics dashboards and Grafana "current" snapshot

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vmware_datacenter_metrics_latest AS
SELECT
    m.collection_timestamp,
    m.vcenter_uuid,
    m.datacenter_moid,
    m.datacenter_name,

    vc.name AS vcenter_name,
    dc.name AS datacenter_name_discovery,
    vc.vcenter_hostname AS vcenter_hostname,

    m.window_start,
    m.window_end,

    m.total_cluster_count,
    m.total_host_count,
    m.total_vm_count,

    m.total_cpu_cores,
    m.total_cpu_threads,
    m.total_cpu_mhz_capacity,
    m.total_cpu_mhz_used,
    m.total_memory_bytes_capacity,
    m.total_memory_bytes_used,
    m.total_storage_bytes_capacity,
    m.total_storage_bytes_used,

    m.cpu_usage_avg_percent,
    m.cpu_usage_min_percent,
    m.cpu_usage_max_percent,
    m.memory_usage_avg_percent,
    m.memory_usage_min_percent,
    m.memory_usage_max_percent,

    m.disk_usage_avg_kbps,
    m.disk_usage_min_kbps,
    m.disk_usage_max_kbps,
    m.network_usage_avg_kbps,
    m.network_usage_min_kbps,
    m.network_usage_max_kbps,

    ROUND((m.total_cpu_mhz_capacity / 1000.0)::numeric, 2) AS total_cpu_ghz,
    ROUND((m.total_memory_bytes_capacity::numeric / (1024.0^3)), 2) AS total_memory_gb,

    NOW() AS materialized_at
FROM raw_vmware_datacenter_metrics_agg m
LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON m.vcenter_uuid::text = vc.vcenter_uuid::text
LEFT JOIN discovery_vmware_inventory_datacenter dc
    ON m.vcenter_uuid::text = dc.vcenter_uuid::text
    AND m.datacenter_moid = dc.component_moid
WHERE m.data_type = 'vmware_datacenter_metrics_agg'
  AND m.collection_timestamp = (
    SELECT MAX(collection_timestamp)
    FROM raw_vmware_datacenter_metrics_agg
    WHERE data_type = 'vmware_datacenter_metrics_agg'
  )
WITH DATA;

-- Unique index for REFRESH MATERIALIZED VIEW CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_datacenter_metrics_latest_pk
    ON mv_vmware_datacenter_metrics_latest(vcenter_uuid, datacenter_moid);

CREATE INDEX IF NOT EXISTS idx_mv_datacenter_metrics_latest_vcenter
    ON mv_vmware_datacenter_metrics_latest(vcenter_name);
CREATE INDEX IF NOT EXISTS idx_mv_datacenter_metrics_latest_datacenter
    ON mv_vmware_datacenter_metrics_latest(datacenter_name_discovery);

COMMENT ON MATERIALIZED VIEW mv_vmware_datacenter_metrics_latest IS
    'Latest datacenter aggregated metrics with entity names (refreshed every 15 minutes). Source: raw_vmware_datacenter_metrics_agg.';
