-- VMware Host Health Monitoring View
-- Monitors host health status and operational metrics
-- Purpose: Quick health assessment and alerting for ESXi hosts

CREATE OR REPLACE VIEW vmware_host_health AS
SELECT 
    r.collection_timestamp,
    r.vcenter_uuid,
    r.datacenter_moid,
    r.cluster_moid,
    r.host_moid,
    r.config_name AS hostname,
    
    -- Connection & Power Status
    r.connection_state,
    r.power_state,
    r.standby_mode,
    
    -- Overall Health Status
    CASE 
        WHEN r.connection_state != 'connected' THEN 'CRITICAL'
        WHEN r.power_state != 'poweredOn' THEN 'WARNING'
        WHEN r.in_maintenance_mode = true THEN 'MAINTENANCE'
        WHEN r.in_quarantine_mode = true THEN 'QUARANTINE'
        WHEN r.health_system_runtime_system_health_info LIKE '%red%' THEN 'CRITICAL'
        WHEN r.health_system_runtime_system_health_info LIKE '%yellow%' THEN 'WARNING'
        WHEN r.health_system_runtime_system_health_info LIKE '%green%' THEN 'OK'
        ELSE 'UNKNOWN'
    END AS overall_health_status,
    
    -- Health Details
    r.health_system_runtime_system_health_info AS health_info,
    r.in_maintenance_mode,
    r.in_quarantine_mode,
    
    -- Uptime Information
    r.boot_time,
    r.quick_stats_uptime AS uptime_seconds,
    ROUND((r.quick_stats_uptime / 3600.0)::numeric, 1) AS uptime_hours,
    ROUND((r.quick_stats_uptime / 86400.0)::numeric, 1) AS uptime_days,
    
    -- Uptime Health (flag if recently rebooted < 1 hour)
    CASE 
        WHEN r.quick_stats_uptime < 3600 THEN 'RECENTLY_REBOOTED'
        WHEN r.quick_stats_uptime < 86400 THEN 'UPTIME_LOW'
        ELSE 'UPTIME_OK'
    END AS uptime_status,
    
    -- CPU Health
    h.num_cpu_cores AS cpu_cores,
    r.quick_stats_overall_cpu_usage AS cpu_usage_mhz,
    CASE 
        WHEN h.num_cpu_cores > 0 AND h.cpu_mhz > 0 THEN
            ROUND(((r.quick_stats_overall_cpu_usage::numeric / (h.num_cpu_cores * h.cpu_mhz)) * 100)::numeric, 2)
        ELSE NULL
    END AS cpu_usage_percent,
    
    CASE 
        WHEN h.num_cpu_cores > 0 AND h.cpu_mhz > 0 THEN
            CASE 
                WHEN (r.quick_stats_overall_cpu_usage::numeric / (h.num_cpu_cores * h.cpu_mhz)) * 100 >= 95 THEN 'CRITICAL'
                WHEN (r.quick_stats_overall_cpu_usage::numeric / (h.num_cpu_cores * h.cpu_mhz)) * 100 >= 85 THEN 'WARNING'
                ELSE 'OK'
            END
        ELSE 'UNKNOWN'
    END AS cpu_health_status,
    
    -- Memory Health
    ROUND((h.memory_size / (1024.0^3))::numeric, 2) AS memory_total_gb,
    ROUND((r.quick_stats_overall_memory_usage / 1024.0)::numeric, 2) AS memory_usage_gb,
    CASE 
        WHEN h.memory_size > 0 THEN
            ROUND(((r.quick_stats_overall_memory_usage::numeric * 1024 * 1024 / h.memory_size) * 100)::numeric, 2)
        ELSE NULL
    END AS memory_usage_percent,
    
    CASE 
        WHEN h.memory_size > 0 THEN
            CASE 
                WHEN (r.quick_stats_overall_memory_usage::numeric * 1024 * 1024 / h.memory_size) * 100 >= 95 THEN 'CRITICAL'
                WHEN (r.quick_stats_overall_memory_usage::numeric * 1024 * 1024 / h.memory_size) * 100 >= 85 THEN 'WARNING'
                ELSE 'OK'
            END
        ELSE 'UNKNOWN'
    END AS memory_health_status,
    
    -- ESXi Version Info
    h.product_name AS esxi_name,
    h.product_version AS esxi_version,
    h.product_build AS esxi_build,
    
    -- Hardware Info
    h.vendor AS hw_vendor,
    h.model AS hw_model,
    
    -- VM Count (distributed on this host)
    r.quick_stats_distributed_cpu_fairness,
    r.quick_stats_distributed_memory_fairness,
    
    -- Network & HBA Count (for connectivity health)
    h.num_nics,
    h.num_hbas,
    
    -- Aggregated Storage Health
    COUNT(DISTINCT s.datastore_moid) AS datastore_count,
    ROUND((SUM(s.datastore_capacity) / (1024.0^4))::numeric, 2) AS storage_total_tb,
    CASE 
        WHEN SUM(s.datastore_capacity) > 0 THEN
            ROUND((((SUM(s.datastore_capacity - s.datastore_free_space)::numeric / SUM(s.datastore_capacity)) * 100))::numeric, 2)
        ELSE NULL
    END AS storage_usage_percent,
    
    CASE 
        WHEN SUM(s.datastore_capacity) > 0 THEN
            CASE 
                WHEN ((SUM(s.datastore_capacity - s.datastore_free_space)::numeric / SUM(s.datastore_capacity)) * 100) >= 95 THEN 'CRITICAL'
                WHEN ((SUM(s.datastore_capacity - s.datastore_free_space)::numeric / SUM(s.datastore_capacity)) * 100) >= 85 THEN 'WARNING'
                ELSE 'OK'
            END
        ELSE 'UNKNOWN'
    END AS storage_health_status,
    
    -- Performance Metrics (if available)
    m.cpu_utilization_avg_percent AS cpu_utilization_avg,
    m.mem_usage_avg_percent AS mem_usage_avg,
    m.disk_total_latency_avg_ms AS disk_latency_avg_ms,
    
    -- Performance Health Flags
    CASE 
        WHEN m.cpu_utilization_avg_percent >= 90 THEN 'CRITICAL'
        WHEN m.cpu_utilization_avg_percent >= 75 THEN 'WARNING'
        WHEN m.cpu_utilization_avg_percent IS NOT NULL THEN 'OK'
        ELSE 'NO_DATA'
    END AS cpu_perf_status,
    
    CASE 
        WHEN m.disk_total_latency_avg_ms >= 50 THEN 'CRITICAL'
        WHEN m.disk_total_latency_avg_ms >= 20 THEN 'WARNING'
        WHEN m.disk_total_latency_avg_ms IS NOT NULL THEN 'OK'
        ELSE 'NO_DATA'
    END AS disk_latency_status,
    
    -- Summary Health Flag (worst of all checks)
    CASE 
        WHEN r.connection_state != 'connected' 
            OR r.power_state = 'poweredOff'
            OR (h.num_cpu_cores > 0 AND h.cpu_mhz > 0 AND (r.quick_stats_overall_cpu_usage::numeric / (h.num_cpu_cores * h.cpu_mhz)) * 100 >= 95)
            OR (h.memory_size > 0 AND (r.quick_stats_overall_memory_usage::numeric * 1024 * 1024 / h.memory_size) * 100 >= 95)
            OR (SUM(s.datastore_capacity) > 0 AND ((SUM(s.datastore_capacity - s.datastore_free_space)::numeric / SUM(s.datastore_capacity)) * 100) >= 95)
            OR m.cpu_utilization_avg_percent >= 90
            OR m.disk_total_latency_avg_ms >= 50
        THEN 'CRITICAL'
        WHEN r.in_maintenance_mode = true
            OR (h.num_cpu_cores > 0 AND h.cpu_mhz > 0 AND (r.quick_stats_overall_cpu_usage::numeric / (h.num_cpu_cores * h.cpu_mhz)) * 100 >= 85)
            OR (h.memory_size > 0 AND (r.quick_stats_overall_memory_usage::numeric * 1024 * 1024 / h.memory_size) * 100 >= 85)
            OR (SUM(s.datastore_capacity) > 0 AND ((SUM(s.datastore_capacity - s.datastore_free_space)::numeric / SUM(s.datastore_capacity)) * 100) >= 85)
            OR m.cpu_utilization_avg_percent >= 75
            OR m.disk_total_latency_avg_ms >= 20
        THEN 'WARNING'
        WHEN r.connection_state = 'connected' AND r.power_state = 'poweredOn' THEN 'OK'
        ELSE 'UNKNOWN'
    END AS summary_health_status

FROM 
    raw_vmware_host_runtime r
LEFT JOIN 
    raw_vmware_host_hardware h
    ON r.host_moid = h.host_moid 
    AND r.collection_timestamp = h.collection_timestamp
    AND r.vcenter_uuid = h.vcenter_uuid
LEFT JOIN 
    raw_vmware_host_storage s
    ON r.host_moid = s.host_moid 
    AND r.collection_timestamp = s.collection_timestamp
    AND r.vcenter_uuid = s.vcenter_uuid
LEFT JOIN 
    vmware_host_metrics m
    ON r.host_moid = m.host_moid 
    AND r.collection_timestamp = m.collection_timestamp
    AND r.vcenter_uuid = m.vcenter_uuid

GROUP BY 
    r.collection_timestamp,
    r.vcenter_uuid,
    r.datacenter_moid,
    r.cluster_moid,
    r.host_moid,
    r.config_name,
    r.connection_state,
    r.power_state,
    r.standby_mode,
    r.health_system_runtime_system_health_info,
    r.in_maintenance_mode,
    r.in_quarantine_mode,
    r.boot_time,
    r.quick_stats_uptime,
    r.quick_stats_overall_cpu_usage,
    r.quick_stats_overall_memory_usage,
    r.quick_stats_distributed_cpu_fairness,
    r.quick_stats_distributed_memory_fairness,
    h.num_cpu_cores,
    h.cpu_mhz,
    h.memory_size,
    h.product_name,
    h.product_version,
    h.product_build,
    h.vendor,
    h.model,
    h.num_nics,
    h.num_hbas,
    m.cpu_utilization_avg_percent,
    m.mem_usage_avg_percent,
    m.disk_total_latency_avg_ms;

-- Example Usage:
-- Show all hosts with health issues:
-- SELECT hostname, summary_health_status, overall_health_status, cpu_health_status, memory_health_status, storage_health_status FROM vmware_host_health WHERE summary_health_status IN ('CRITICAL', 'WARNING') ORDER BY summary_health_status DESC;

-- Show disconnected or powered off hosts:
-- SELECT hostname, connection_state, power_state, boot_time FROM vmware_host_health WHERE connection_state != 'connected' OR power_state != 'poweredOn';

-- Show hosts in maintenance:
-- SELECT hostname, in_maintenance_mode, in_quarantine_mode FROM vmware_host_health WHERE in_maintenance_mode = true OR in_quarantine_mode = true;
