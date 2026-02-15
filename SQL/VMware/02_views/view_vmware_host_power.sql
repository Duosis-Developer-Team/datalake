-- VMware Host Power Consumption View
-- Dedicated view for power monitoring and energy efficiency analysis
-- Purpose: Track power usage trends and identify power optimization opportunities

CREATE OR REPLACE VIEW vmware_host_power AS
WITH power_metrics AS (
    SELECT
        collection_timestamp,
        vcenter_uuid,
        host_moid,
        
        -- Power Metrics (Watts)
        MAX(CASE WHEN counter_name = 'power.power.average' THEN value_avg END) AS power_avg_watts,
        MAX(CASE WHEN counter_name = 'power.power.average' THEN value_min END) AS power_min_watts,
        MAX(CASE WHEN counter_name = 'power.power.average' THEN value_max END) AS power_max_watts,
        
        -- Energy Metrics (Joules)
        MAX(CASE WHEN counter_name = 'power.energy.summation' THEN value_avg END) AS energy_avg_joules,
        MAX(CASE WHEN counter_name = 'power.energy.summation' THEN value_last END) AS energy_total_joules,
        
        -- Power Cap Metrics (if available)
        MAX(CASE WHEN counter_name = 'power.powerCap.average' THEN value_avg END) AS power_cap_watts
        
    FROM raw_vmware_host_perf_agg
    WHERE data_type = 'vmware_host_perf_agg'
      AND counter_name LIKE 'power.%'
    GROUP BY collection_timestamp, vcenter_uuid, host_moid
)
SELECT 
    p.collection_timestamp,
    p.vcenter_uuid,
    h.datacenter_moid,
    h.cluster_moid,
    p.host_moid,
    
    -- Host Identification
    r.config_name AS hostname,
    vc.name AS vcenter_name,
    dc.name AS datacenter_name,
    vc.vcenter_hostname AS vcenter_hostname,
    SPLIT_PART(cl.name, '-', 1) AS location,
    cl.name AS cluster_name,
    h.vendor AS hw_vendor,
    h.model AS hw_model,
    
    -- Host State
    r.power_state,
    r.connection_state,
    r.in_maintenance_mode,
    
    -- CPU Info (for power efficiency calculation)
    h.num_cpu_cores AS cpu_cores,
    h.num_cpu_pkgs AS cpu_sockets,
    h.cpu_mhz AS cpu_core_mhz,
    (h.num_cpu_cores * h.cpu_mhz) AS cpu_total_capacity_mhz,
    
    -- Current CPU Usage (for correlation with power)
    r.quick_stats_overall_cpu_usage AS cpu_current_usage_mhz,
    CASE 
        WHEN h.num_cpu_cores > 0 AND h.cpu_mhz > 0 THEN
            ROUND((r.quick_stats_overall_cpu_usage::numeric / (h.num_cpu_cores * h.cpu_mhz)) * 100, 2)
        ELSE NULL
    END AS cpu_usage_percent,
    
    -- Power Metrics (Raw Watts)
    ROUND(p.power_avg_watts::numeric, 2) AS power_avg_watts,
    ROUND(p.power_min_watts::numeric, 2) AS power_min_watts,
    ROUND(p.power_max_watts::numeric, 2) AS power_max_watts,
    ROUND(p.power_cap_watts::numeric, 2) AS power_cap_watts,
    
    -- Power Metrics (Kilowatts)
    ROUND((p.power_avg_watts / 1000.0)::numeric, 3) AS power_avg_kw,
    ROUND((p.power_max_watts / 1000.0)::numeric, 3) AS power_max_kw,
    
    -- Energy Consumption
    ROUND(p.energy_avg_joules::numeric, 2) AS energy_avg_joules,
    ROUND(p.energy_total_joules::numeric, 2) AS energy_total_joules,
    
    -- Energy (Watt-hours) - Joules / 3600
    ROUND((p.energy_total_joules / 3600.0)::numeric, 2) AS energy_total_wh,
    ROUND((p.energy_total_joules / 3600000.0)::numeric, 3) AS energy_total_kwh,
    
    -- Power Efficiency (Watts per GHz of CPU capacity)
    CASE 
        WHEN h.num_cpu_cores > 0 AND h.cpu_mhz > 0 AND p.power_avg_watts > 0 THEN
            ROUND((p.power_avg_watts / (h.num_cpu_cores * h.cpu_mhz / 1000.0))::numeric, 2)
        ELSE NULL
    END AS watts_per_ghz_capacity,
    
    -- Power Efficiency (Watts per utilized GHz)
    CASE 
        WHEN r.quick_stats_overall_cpu_usage > 0 AND p.power_avg_watts > 0 THEN
            ROUND((p.power_avg_watts / (r.quick_stats_overall_cpu_usage / 1000.0))::numeric, 2)
        ELSE NULL
    END AS watts_per_ghz_utilized,
    
    -- Power Cap Utilization (if power cap is set)
    CASE 
        WHEN p.power_cap_watts > 0 AND p.power_avg_watts IS NOT NULL THEN
            ROUND((p.power_avg_watts / p.power_cap_watts * 100)::numeric, 2)
        ELSE NULL
    END AS power_cap_usage_percent,
    
    -- Power Status Flags
    CASE 
        WHEN p.power_avg_watts IS NULL THEN 'NO_DATA'
        WHEN p.power_cap_watts > 0 AND p.power_avg_watts >= (p.power_cap_watts * 0.95) THEN 'CRITICAL_NEAR_CAP'
        WHEN p.power_cap_watts > 0 AND p.power_avg_watts >= (p.power_cap_watts * 0.85) THEN 'WARNING_HIGH_CAP'
        WHEN p.power_avg_watts > 500 THEN 'HIGH_CONSUMPTION'
        WHEN p.power_avg_watts > 300 THEN 'MEDIUM_CONSUMPTION'
        WHEN p.power_avg_watts > 0 THEN 'NORMAL_CONSUMPTION'
        ELSE 'UNKNOWN'
    END AS power_status,
    
    -- Power Variability (Max - Min)
    CASE 
        WHEN p.power_max_watts IS NOT NULL AND p.power_min_watts IS NOT NULL THEN
            ROUND((p.power_max_watts - p.power_min_watts)::numeric, 2)
        ELSE NULL
    END AS power_variability_watts,
    
    -- Power Stability Indicator (Low variability = stable)
    CASE 
        WHEN p.power_avg_watts > 0 AND p.power_max_watts IS NOT NULL AND p.power_min_watts IS NOT NULL THEN
            ROUND(((p.power_max_watts - p.power_min_watts) / p.power_avg_watts * 100)::numeric, 2)
        ELSE NULL
    END AS power_variability_percent,
    
    CASE 
        WHEN p.power_avg_watts > 0 AND p.power_max_watts IS NOT NULL AND p.power_min_watts IS NOT NULL THEN
            CASE 
                WHEN ((p.power_max_watts - p.power_min_watts) / p.power_avg_watts * 100) < 10 THEN 'STABLE'
                WHEN ((p.power_max_watts - p.power_min_watts) / p.power_avg_watts * 100) < 25 THEN 'MODERATE'
                ELSE 'VARIABLE'
            END
        ELSE 'UNKNOWN'
    END AS power_stability,
    
    -- Idle Power Estimation (min power when host is on)
    CASE 
        WHEN r.power_state = 'poweredOn' AND p.power_min_watts IS NOT NULL THEN
            ROUND(p.power_min_watts::numeric, 2)
        ELSE NULL
    END AS estimated_idle_power_watts,
    
    -- Active Power (difference between current and idle)
    CASE 
        WHEN r.power_state = 'poweredOn' AND p.power_avg_watts IS NOT NULL AND p.power_min_watts IS NOT NULL THEN
            ROUND((p.power_avg_watts - p.power_min_watts)::numeric, 2)
        ELSE NULL
    END AS estimated_active_power_watts,
    
    -- Memory Size (for power correlation)
    ROUND((h.memory_size / (1024.0^3))::numeric, 2) AS memory_total_gb,
    
    -- Uptime (for energy cost calculation)
    r.quick_stats_uptime AS uptime_seconds,
    ROUND((r.quick_stats_uptime / 3600.0)::numeric, 1) AS uptime_hours,
    
    -- Estimated Energy Cost (assuming $0.12 per kWh as default)
    CASE 
        WHEN p.energy_total_joules > 0 THEN
            ROUND(((p.energy_total_joules / 3600000.0) * 0.12)::numeric, 4)
        ELSE NULL
    END AS estimated_cost_usd_012kwh

FROM 
    power_metrics p
LEFT JOIN 
    raw_vmware_host_hardware h
    ON p.host_moid = h.host_moid 
    AND p.collection_timestamp = h.collection_timestamp
    AND p.vcenter_uuid = h.vcenter_uuid
LEFT JOIN 
    raw_vmware_host_runtime r
    ON p.host_moid = r.host_moid 
    AND p.collection_timestamp = r.collection_timestamp
    AND p.vcenter_uuid = r.vcenter_uuid
LEFT JOIN discovery_vmware_inventory_vcenter vc
    ON h.vcenter_uuid::text = vc.vcenter_uuid::text
LEFT JOIN discovery_vmware_inventory_datacenter dc
    ON h.vcenter_uuid::text = dc.vcenter_uuid::text
    AND h.datacenter_moid = dc.component_moid
LEFT JOIN discovery_vmware_inventory_cluster cl
    ON h.vcenter_uuid::text = cl.vcenter_uuid::text
    AND h.cluster_moid = cl.component_moid;

-- Example Usage:
-- Show hosts with highest power consumption:
-- SELECT hostname, power_avg_watts, power_status, cpu_usage_percent FROM vmware_host_power WHERE power_avg_watts IS NOT NULL ORDER BY power_avg_watts DESC LIMIT 10;

-- Show power efficiency by host:
-- SELECT hostname, watts_per_ghz_capacity, power_avg_watts, cpu_cores FROM vmware_host_power WHERE watts_per_ghz_capacity IS NOT NULL ORDER BY watts_per_ghz_capacity ASC;

-- Show total energy consumption per datacenter:
-- SELECT datacenter_moid, SUM(energy_total_kwh) AS total_kwh, SUM(estimated_cost_usd_012kwh) AS total_cost FROM vmware_host_power GROUP BY datacenter_moid ORDER BY total_kwh DESC;

-- Show hosts near power cap:
-- SELECT hostname, power_avg_watts, power_cap_watts, power_cap_usage_percent FROM vmware_host_power WHERE power_status LIKE '%CAP%';

-- Power trends over time:
-- SELECT collection_timestamp, AVG(power_avg_watts) AS avg_power, MAX(power_max_watts) AS peak_power FROM vmware_host_power GROUP BY collection_timestamp ORDER BY collection_timestamp;
