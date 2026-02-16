-- VMware Cluster Inventory View (Enhanced with Discovery Integration)
-- Combines raw_vmware_cluster_config + entity names from discovery tables
-- Purpose: Cluster config with human-readable vcenter/datacenter/cluster names

CREATE OR REPLACE VIEW vmware_cluster_inventory AS
SELECT
    -- Identification
    c.collection_timestamp,
    c.vcenter_uuid,
    c.datacenter_moid,
    c.cluster_moid,

    -- Entity Names (from discovery tables)
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    vc.vcenter_hostname AS vcenter_hostname,
    COALESCE(SPLIT_PART(cl.name, '-', 1), SPLIT_PART(c.name, '-', 1)) AS location,
    COALESCE(cl.name, c.name) AS cluster_name,

    -- Config (from raw_vmware_cluster_config)
    c.name AS name,
    c.summary_num_hosts,
    c.summary_num_cpu_cores,
    c.summary_num_cpu_threads,
    c.summary_effective_cpu,
    c.summary_total_cpu,
    c.summary_num_effective_hosts,
    c.summary_total_memory,
    c.summary_effective_memory,
    c.summary_overall_status,

    -- HA / DRS / DPM
    c.config_das_enabled,
    c.config_das_vm_monitoring,
    c.config_das_host_monitoring,
    c.config_drs_enabled,
    c.config_drs_default_vm_behavior,
    c.config_drs_vmotion_rate,
    c.config_dpm_enabled,

    -- Computed (human-readable capacity; NULL when denominator 0)
    CASE
        WHEN c.summary_total_cpu > 0 THEN ROUND((c.summary_total_cpu / 1000.0)::numeric, 2)
        ELSE NULL
    END AS total_cpu_ghz,
    CASE
        WHEN c.summary_total_memory IS NOT NULL AND c.summary_total_memory > 0 THEN
            ROUND((c.summary_total_memory::numeric / (1024.0^3)), 2)
        ELSE NULL
    END AS total_memory_gb
FROM raw_vmware_cluster_config c

LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON c.vcenter_uuid::text = vc.vcenter_uuid::text

LEFT JOIN discovery_vmware_inventory_datacenter dc
    ON c.vcenter_uuid::text = dc.vcenter_uuid::text
    AND c.datacenter_moid = dc.component_moid

LEFT JOIN discovery_vmware_inventory_cluster cl
    ON c.vcenter_uuid::text = cl.vcenter_uuid::text
    AND c.cluster_moid = cl.component_moid;

COMMENT ON VIEW vmware_cluster_inventory IS 'Cluster config with discovery entity names; use for cluster inventory and config dashboards.';
