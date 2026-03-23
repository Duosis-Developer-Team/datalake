-- VMware Datacenter Inventory View (Enhanced with Discovery Integration)
-- Combines raw_vmware_datacenter_config + entity names from discovery tables
-- Purpose: Datacenter config with human-readable vcenter/datacenter names

CREATE OR REPLACE VIEW vmware_datacenter_inventory AS
SELECT
    -- Identification
    c.collection_timestamp,
    c.vcenter_uuid,
    c.datacenter_moid,

    -- Entity Names (from discovery tables)
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    vc.vcenter_hostname AS vcenter_hostname,

    -- Config (from raw_vmware_datacenter_config)
    c.name AS name,
    c.overall_status,
    c.data_type

FROM raw_vmware_datacenter_config c

LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON c.vcenter_uuid::text = vc.vcenter_uuid::text

LEFT JOIN discovery_vmware_inventory_datacenter dc
    ON c.vcenter_uuid::text = dc.vcenter_uuid::text
    AND c.datacenter_moid = dc.component_moid;

COMMENT ON VIEW vmware_datacenter_inventory IS 'Datacenter config with discovery entity names; use for datacenter inventory and config dashboards.';
