-- VMware Host Storage Detail View
-- Provides detailed storage information per datastore per host
-- Purpose: Storage capacity analysis and datastore-level monitoring

CREATE OR REPLACE VIEW vmware_host_storage_detail AS
SELECT 
    s.collection_timestamp,
    s.vcenter_uuid,
    h.datacenter_moid,
    h.cluster_moid,
    s.host_moid,
    
    -- Entity Names (from discovery)
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    vc.vcenter_hostname AS vcenter_hostname,
    SPLIT_PART(cl.name, '-', 1) AS location,
    cl.name AS cluster_name,
    
    -- Host Info
    r.config_name AS hostname,
    r.connection_state AS host_connection_state,
    r.power_state AS host_power_state,
    
    -- Datastore Info
    s.datastore_moid,
    s.datastore_name,
    s.datastore_type,
    s.datastore_url,
    s.datastore_accessible,
    s.datastore_multiple_host_access,
    
    -- Datastore Capacity (Raw bytes)
    s.datastore_capacity AS capacity_bytes,
    s.datastore_free_space AS free_bytes,
    (s.datastore_capacity - s.datastore_free_space) AS used_bytes,
    
    -- Datastore Capacity (GB)
    ROUND((s.datastore_capacity / (1024.0^3))::numeric, 2) AS capacity_gb,
    ROUND((s.datastore_free_space / (1024.0^3))::numeric, 2) AS free_gb,
    ROUND(((s.datastore_capacity - s.datastore_free_space) / (1024.0^3))::numeric, 2) AS used_gb,
    
    -- Datastore Capacity (TB)
    ROUND((s.datastore_capacity / (1024.0^4))::numeric, 2) AS capacity_tb,
    ROUND((s.datastore_free_space / (1024.0^4))::numeric, 2) AS free_tb,
    ROUND(((s.datastore_capacity - s.datastore_free_space) / (1024.0^4))::numeric, 2) AS used_tb,
    
    -- Usage Percentage
    CASE 
        WHEN s.datastore_capacity > 0 THEN
            ROUND((((s.datastore_capacity - s.datastore_free_space)::numeric / s.datastore_capacity * 100))::numeric, 2)
        ELSE NULL
    END AS usage_percent,
    
    -- Free Space Percentage
    CASE 
        WHEN s.datastore_capacity > 0 THEN
            ROUND(((s.datastore_free_space::numeric / s.datastore_capacity * 100))::numeric, 2)
        ELSE NULL
    END AS free_percent,
    
    -- Note: datastore_uncommitted is not available in raw_vmware_host_storage
    -- Uncommitted space would come from VM storage info (raw_vmware_vm_storage)
    
    -- Storage Health Status
    CASE 
        WHEN s.datastore_accessible = false THEN 'CRITICAL_INACCESSIBLE'
        WHEN s.datastore_capacity > 0 AND ((s.datastore_capacity - s.datastore_free_space)::numeric / s.datastore_capacity * 100) >= 95 THEN 'CRITICAL_FULL'
        WHEN s.datastore_capacity > 0 AND ((s.datastore_capacity - s.datastore_free_space)::numeric / s.datastore_capacity * 100) >= 85 THEN 'WARNING_HIGH'
        WHEN s.datastore_capacity > 0 AND ((s.datastore_capacity - s.datastore_free_space)::numeric / s.datastore_capacity * 100) >= 75 THEN 'WARNING_MEDIUM'
        ELSE 'OK'
    END AS storage_health_status,
    
    -- Threshold Flags (for alerting)
    CASE 
        WHEN s.datastore_capacity > 0 AND s.datastore_free_space < (s.datastore_capacity * 0.05) THEN 'CRITICAL_5%_FREE'
        WHEN s.datastore_capacity > 0 AND s.datastore_free_space < (s.datastore_capacity * 0.10) THEN 'WARNING_10%_FREE'
        WHEN s.datastore_capacity > 0 AND s.datastore_free_space < (s.datastore_capacity * 0.15) THEN 'WARNING_15%_FREE'
        ELSE 'OK'
    END AS free_space_threshold,
    
    -- SSD Flag (if VSAN or SSD type)
    CASE 
        WHEN s.datastore_type IN ('vsan', 'VSAN') THEN true
        WHEN s.datastore_name LIKE '%SSD%' OR s.datastore_name LIKE '%ssd%' THEN true
        ELSE false
    END AS is_ssd_datastore,
    
    -- Hardware Info (for context)
    h.vendor AS host_vendor,
    h.model AS host_model,
    h.num_hbas AS host_hba_count

FROM 
    raw_vmware_host_storage s
LEFT JOIN 
    raw_vmware_host_runtime r
    ON s.host_moid = r.host_moid 
    AND s.collection_timestamp = r.collection_timestamp
    AND s.vcenter_uuid = r.vcenter_uuid
LEFT JOIN 
    raw_vmware_host_hardware h
    ON s.host_moid = h.host_moid 
    AND s.collection_timestamp = h.collection_timestamp
    AND s.vcenter_uuid = h.vcenter_uuid
LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON h.vcenter_uuid::text = vc.vcenter_uuid::text
LEFT JOIN discovery_vmware_inventory_datacenter dc
    ON h.vcenter_uuid::text = dc.vcenter_uuid::text
    AND h.datacenter_moid = dc.component_moid
LEFT JOIN discovery_vmware_inventory_cluster cl
    ON h.vcenter_uuid::text = cl.vcenter_uuid::text
    AND h.cluster_moid = cl.component_moid;

-- Example Usage:
-- Show datastores with low free space:
-- SELECT datastore_name, hostname, usage_percent, free_gb, storage_health_status FROM vmware_host_storage_detail WHERE storage_health_status LIKE 'CRITICAL%' OR storage_health_status LIKE 'WARNING%';

-- Show inaccessible datastores:
-- SELECT datastore_name, hostname, datastore_accessible, storage_health_status FROM vmware_host_storage_detail WHERE datastore_accessible = false;

-- Storage summary by datastore:
-- SELECT datastore_name, COUNT(DISTINCT host_moid) AS host_count, AVG(usage_percent) AS avg_usage_percent FROM vmware_host_storage_detail GROUP BY datastore_name ORDER BY avg_usage_percent DESC;
