-- VMware Datacenter Metrics View (Enhanced with Discovery Integration)
-- Combines raw_vmware_datacenter_metrics_agg + entity names from discovery tables
-- Purpose: Datacenter aggregated metrics with human-readable vcenter/datacenter names (all timestamps; for time series and reporting)

CREATE OR REPLACE VIEW vmware_datacenter_metrics AS
SELECT
    -- Identification
    m.collection_timestamp,
    m.vcenter_uuid,
    m.datacenter_moid,

    -- Entity Names (from discovery tables)
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    vc.vcenter_hostname AS vcenter_hostname,

    -- Raw metrics columns
    m.data_type,
    m.datacenter_name AS datacenter_name_raw,
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

    -- Computed (human-readable capacity; aligned with mv_vmware_cluster_metrics_latest)
    ROUND((m.total_cpu_mhz_capacity / 1000.0)::numeric, 2) AS total_cpu_ghz,
    ROUND((m.total_memory_bytes_capacity::numeric / (1024.0^3)), 2) AS total_memory_gb

FROM raw_vmware_datacenter_metrics_agg m

LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON m.vcenter_uuid::text = vc.vcenter_uuid::text

LEFT JOIN discovery_vmware_inventory_datacenter dc
    ON m.vcenter_uuid::text = dc.vcenter_uuid::text
    AND m.datacenter_moid = dc.component_moid

WHERE m.data_type = 'vmware_datacenter_metrics_agg';

COMMENT ON VIEW vmware_datacenter_metrics IS 'Datacenter aggregated metrics with discovery entity names; use for time series and reporting. Source: raw_vmware_datacenter_metrics_agg.';
