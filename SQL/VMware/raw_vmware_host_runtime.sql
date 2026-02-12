-- VMware Host Runtime State Table
-- Data Type: vmware_host_runtime
-- Source: host.runtime, host.summary.quickStats, host.summary.config
-- Update Frequency: High (runtime state changes)
-- Primary Key: (vcenter_uuid, host_moid, collection_timestamp)

CREATE TABLE IF NOT EXISTS raw_vmware_host_runtime (
    -- Meta fields
    data_type TEXT NOT NULL,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    vcenter_uuid TEXT NOT NULL,
    host_moid TEXT NOT NULL,
    
    -- host.runtime fields (AS-IS from VMware API)
    connection_state TEXT,
    power_state TEXT,
    standby_mode TEXT,
    in_maintenance_mode BOOLEAN,
    in_quarantine_mode BOOLEAN,
    boot_time TIMESTAMPTZ,
    health_system_runtime_system_health_info TEXT,
    
    -- host.summary.quickStats (AS-IS, NO CONVERSION)
    quick_stats_overall_cpu_usage INT,
    quick_stats_overall_memory_usage INT,
    quick_stats_distributed_cpu_fairness INT,
    quick_stats_distributed_memory_fairness INT,
    quick_stats_uptime BIGINT,
    
    -- host.summary.config (connection info)
    config_name TEXT,
    config_port INT,
    config_ssl_thumbprint TEXT,
    
    -- Constraints
    PRIMARY KEY (vcenter_uuid, host_moid, collection_timestamp)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_runtime_vcenter 
    ON raw_vmware_host_runtime(vcenter_uuid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_runtime_timestamp 
    ON raw_vmware_host_runtime(collection_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_runtime_data_type 
    ON raw_vmware_host_runtime(data_type);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_runtime_connection_state 
    ON raw_vmware_host_runtime(connection_state);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_runtime_power_state 
    ON raw_vmware_host_runtime(power_state);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_runtime_maintenance 
    ON raw_vmware_host_runtime(in_maintenance_mode);

-- Comments
COMMENT ON TABLE raw_vmware_host_runtime IS 'VMware ESXi host runtime state - raw fields from host.runtime and host.summary.quickStats';
COMMENT ON COLUMN raw_vmware_host_runtime.data_type IS 'Always: vmware_host_runtime';
COMMENT ON COLUMN raw_vmware_host_runtime.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN raw_vmware_host_runtime.quick_stats_overall_cpu_usage IS 'Overall CPU usage in MHz (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_host_runtime.quick_stats_overall_memory_usage IS 'Overall memory usage in MB (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_host_runtime.quick_stats_uptime IS 'Host uptime in seconds (AS-IS from VMware API)';
