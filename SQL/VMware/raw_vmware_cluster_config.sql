-- VMware Cluster Configuration Table
-- Data Type: vmware_cluster_config
-- Source: cluster.configuration, cluster.summary
-- Update Frequency: Low (configuration changes)
-- Primary Key: (vcenter_uuid, cluster_moid, collection_timestamp)

CREATE TABLE IF NOT EXISTS raw_vmware_cluster_config (
    -- Meta fields
    data_type TEXT NOT NULL,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    vcenter_uuid TEXT NOT NULL,
    datacenter_moid TEXT,
    cluster_moid TEXT NOT NULL,
    name TEXT,
    
    -- cluster.summary fields (AS-IS from VMware API)
    summary_num_hosts INT,
    summary_num_cpu_cores INT,
    summary_num_cpu_threads INT,
    summary_effective_cpu INT,
    summary_total_cpu INT,
    summary_num_effective_hosts INT,
    summary_total_memory BIGINT,
    summary_effective_memory BIGINT,
    summary_overall_status TEXT,
    
    -- cluster.configuration.dasConfig (HA configuration)
    config_das_enabled BOOLEAN,
    config_das_vm_monitoring TEXT,
    config_das_host_monitoring TEXT,
    
    -- cluster.configuration.drsConfig (DRS configuration)
    config_drs_enabled BOOLEAN,
    config_drs_default_vm_behavior TEXT,
    config_drs_vmotion_rate INT,
    
    -- cluster.configuration.dpmConfigInfo (DPM configuration)
    config_dpm_enabled BOOLEAN,
    
    -- Constraints
    PRIMARY KEY (vcenter_uuid, cluster_moid, collection_timestamp)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_raw_vmware_cluster_config_vcenter 
    ON raw_vmware_cluster_config(vcenter_uuid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_cluster_config_datacenter 
    ON raw_vmware_cluster_config(datacenter_moid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_cluster_config_timestamp 
    ON raw_vmware_cluster_config(collection_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_cluster_config_data_type 
    ON raw_vmware_cluster_config(data_type);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_cluster_config_name 
    ON raw_vmware_cluster_config(name);

-- Comments
COMMENT ON TABLE raw_vmware_cluster_config IS 'VMware cluster configuration - raw fields from cluster.configuration and cluster.summary';
COMMENT ON COLUMN raw_vmware_cluster_config.data_type IS 'Always: vmware_cluster_config';
COMMENT ON COLUMN raw_vmware_cluster_config.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN raw_vmware_cluster_config.summary_total_cpu IS 'Total CPU in MHz (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_cluster_config.summary_total_memory IS 'Total memory in bytes (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_cluster_config.config_das_enabled IS 'HA (High Availability) enabled status';
COMMENT ON COLUMN raw_vmware_cluster_config.config_drs_enabled IS 'DRS (Distributed Resource Scheduler) enabled status';
