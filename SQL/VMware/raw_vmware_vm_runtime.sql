-- VMware VM Runtime State Table
-- Data Type: vmware_vm_runtime
-- Source: vm.runtime, vm.guest, vm.summary.quickStats
-- Update Frequency: High (runtime state changes frequently)
-- Primary Key: (vcenter_uuid, vm_moid, collection_timestamp)

CREATE TABLE IF NOT EXISTS raw_vmware_vm_runtime (
    -- Meta fields
    data_type TEXT NOT NULL,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    vcenter_uuid TEXT NOT NULL,
    vm_moid TEXT NOT NULL,
    
    -- vm.runtime fields (AS-IS from VMware API)
    power_state TEXT,
    connection_state TEXT,
    boot_time TIMESTAMPTZ,
    suspend_time TIMESTAMPTZ,
    suspend_interval BIGINT,
    question TEXT,
    memory_overhead BIGINT,
    max_cpu_usage INT,
    max_memory_usage INT,
    num_mks_connections INT,
    record_replay_state TEXT,
    clean_power_off BOOLEAN,
    need_secondary_reason TEXT,
    online_standby BOOLEAN,
    min_required_evc_mode_key TEXT,
    consolidation_needed BOOLEAN,
    offline_feature_requirement TEXT[],
    feature_requirement TEXT[],
    
    -- vm.guest fields (AS-IS from VMware API)
    guest_tools_status TEXT,
    guest_tools_version TEXT,
    guest_tools_version_status TEXT,
    guest_tools_running_status TEXT,
    guest_tools_version_status2 TEXT,
    guest_guest_id TEXT,
    guest_guest_family TEXT,
    guest_guest_full_name TEXT,
    guest_host_name TEXT,
    guest_ip_address TEXT,
    guest_guest_state TEXT,
    
    -- vm.summary.quickStats (AS-IS, NO CONVERSION)
    quick_stats_overall_cpu_usage INT,
    quick_stats_overall_cpu_demand INT,
    quick_stats_guest_memory_usage INT,
    quick_stats_host_memory_usage INT,
    quick_stats_guest_heartbeat_status TEXT,
    quick_stats_distributed_cpu_entitlement INT,
    quick_stats_distributed_memory_entitlement INT,
    quick_stats_static_cpu_entitlement INT,
    quick_stats_static_memory_entitlement INT,
    quick_stats_private_memory INT,
    quick_stats_shared_memory INT,
    quick_stats_swapped_memory INT,
    quick_stats_ballooned_memory INT,
    quick_stats_consumed_overhead_memory INT,
    quick_stats_ft_log_bandwidth INT,
    quick_stats_ft_secondary_latency INT,
    quick_stats_ft_latency_status TEXT,
    quick_stats_compressed_memory BIGINT,
    quick_stats_uptime_seconds BIGINT,
    quick_stats_ssd_swapped_memory BIGINT,
    
    -- Constraints
    PRIMARY KEY (vcenter_uuid, vm_moid, collection_timestamp)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_runtime_vcenter 
    ON raw_vmware_vm_runtime(vcenter_uuid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_runtime_timestamp 
    ON raw_vmware_vm_runtime(collection_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_runtime_data_type 
    ON raw_vmware_vm_runtime(data_type);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_runtime_power_state 
    ON raw_vmware_vm_runtime(power_state);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_runtime_connection_state 
    ON raw_vmware_vm_runtime(connection_state);

-- Comments
COMMENT ON TABLE raw_vmware_vm_runtime IS 'VMware VM runtime state - raw fields from vm.runtime, vm.guest, and vm.summary.quickStats';
COMMENT ON COLUMN raw_vmware_vm_runtime.data_type IS 'Always: vmware_vm_runtime';
COMMENT ON COLUMN raw_vmware_vm_runtime.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN raw_vmware_vm_runtime.quick_stats_overall_cpu_usage IS 'Overall CPU usage in MHz (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_vm_runtime.quick_stats_guest_memory_usage IS 'Guest memory usage in MB (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_vm_runtime.quick_stats_host_memory_usage IS 'Host memory usage in MB (AS-IS from VMware API)';
