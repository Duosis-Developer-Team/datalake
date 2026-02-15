-- VMware Host Storage Detail View
-- Provides detailed storage information per datastore per host
-- Purpose: Storage capacity analysis and datastore-level monitoring

CREATE OR REPLACE VIEW vmware_host_storage_detail AS
SELECT 
    s.collection_timestamp,
    s.vcenter_uuid,
    s.datacenter_moid,
    s.cluster_moid,
    s.host_moid,
    
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
    s.datastore_maintenance_mode,
    
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
    
    -- Uncommitted Space
    s.datastore_uncommitted AS uncommitted_bytes,
    ROUND((s.datastore_uncommitted / (1024.0^3))::numeric, 2) AS uncommitted_gb,
    ROUND((s.datastore_uncommitted / (1024.0^4))::numeric, 2) AS uncommitted_tb,
    
    -- Provisioned Space (Capacity - Free + Uncommitted)
    (s.datastore_capacity - s.datastore_free_space + s.datastore_uncommitted) AS provisioned_bytes,
    ROUND(((s.datastore_capacity - s.datastore_free_space + s.datastore_uncommitted) / (1024.0^3))::numeric, 2) AS provisioned_gb,
    ROUND(((s.datastore_capacity - s.datastore_free_space + s.datastore_uncommitted) / (1024.0^4))::numeric, 2) AS provisioned_tb,
    
    -- Thin Provisioning Ratio (Provisioned / Capacity)
    CASE 
        WHEN s.datastore_capacity > 0 THEN
            ROUND((((s.datastore_capacity - s.datastore_free_space + s.datastore_uncommitted)::numeric / s.datastore_capacity))::numeric, 2)
        ELSE NULL
    END AS thin_provisioning_ratio,
    
    -- Over-provisioned Flag (if provisioned > capacity)
    CASE 
        WHEN (s.datastore_capacity - s.datastore_free_space + s.datastore_uncommitted) > s.datastore_capacity THEN true
        ELSE false
    END AS is_overprovisioned,
    
    -- Storage Health Status
    CASE 
        WHEN s.datastore_accessible = false THEN 'CRITICAL_INACCESSIBLE'
        WHEN s.datastore_maintenance_mode = 'inMaintenance' THEN 'MAINTENANCE'
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
    AND s.vcenter_uuid = h.vcenter_uuid;

-- Example Usage:
-- Show datastores with low free space:
-- SELECT datastore_name, hostname, usage_percent, free_gb, storage_health_status FROM vmware_host_storage_detail WHERE storage_health_status LIKE 'CRITICAL%' OR storage_health_status LIKE 'WARNING%';

-- Show over-provisioned datastores:
-- SELECT datastore_name, hostname, thin_provisioning_ratio, provisioned_tb, capacity_tb FROM vmware_host_storage_detail WHERE is_overprovisioned = true;

-- Show inaccessible datastores:
-- SELECT datastore_name, hostname, datastore_accessible, storage_health_status FROM vmware_host_storage_detail WHERE datastore_accessible = false;

-- Storage summary by datastore:
-- SELECT datastore_name, COUNT(DISTINCT host_moid) AS host_count, AVG(usage_percent) AS avg_usage_percent FROM vmware_host_storage_detail GROUP BY datastore_name ORDER BY avg_usage_percent DESC;
