-- VMware Cluster Metrics View (Thin layer over raw_vmware_cluster_metrics_agg)
-- Adds discovery entity names for Grafana and reporting
-- Data is pre-calculated in collector; use time filter for Grafana time range

CREATE OR REPLACE VIEW vmware_cluster_metrics AS
SELECT
    m.collection_timestamp,
    m.vcenter_uuid,
    m.datacenter_moid,
    m.cluster_moid,
    m.cluster_name,

    -- Entity Names (from discovery)
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    vc.vcenter_hostname AS vcenter_hostname,
    SPLIT_PART(cl.name, '-', 1) AS location,
    cl.name AS cluster_name_discovery,

    m.window_start,
    m.window_end,

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

    -- Human-readable (optional)
    ROUND((m.total_cpu_mhz_capacity / 1000.0)::numeric, 2) AS total_cpu_ghz,
    ROUND((m.total_memory_bytes_capacity::numeric / (1024.0^3)), 2) AS total_memory_gb
FROM raw_vmware_cluster_metrics_agg m

LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON m.vcenter_uuid::text = vc.vcenter_uuid::text

LEFT JOIN discovery_vmware_inventory_datacenter dc
    ON m.vcenter_uuid::text = dc.vcenter_uuid::text
    AND m.datacenter_moid = dc.component_moid

LEFT JOIN discovery_vmware_inventory_cluster cl
    ON m.vcenter_uuid::text = cl.vcenter_uuid::text
    AND m.cluster_moid = cl.component_moid
WHERE m.data_type = 'vmware_cluster_metrics_agg';

COMMENT ON VIEW vmware_cluster_metrics IS 'Cluster aggregated metrics with entity names; source is raw_vmware_cluster_metrics_agg (filled by collector). Use collection_timestamp or window_end for Grafana time range.';
