-- VMware VM Configuration Table
-- Data Type: vmware_vm_config
-- Source: vm.summary.config, vm.config
-- Update Frequency: Low (configuration changes)
-- Primary Key: (vcenter_uuid, vm_moid, collection_timestamp)

CREATE TABLE IF NOT EXISTS raw_vmware_vm_config (
    -- Meta fields
    data_type TEXT NOT NULL,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    vcenter_uuid TEXT NOT NULL,
    datacenter_moid TEXT,
    cluster_moid TEXT,
    host_moid TEXT,
    vm_moid TEXT NOT NULL,
    
    -- vm.summary.config fields (AS-IS from VMware API)
    name TEXT,
    template BOOLEAN,
    vm_path_name TEXT,
    memory_size_mb BIGINT,
    cpu_reservation BIGINT,
    memory_reservation BIGINT,
    num_cpu INT,
    num_ethernet_cards INT,
    num_virtual_disks INT,
    uuid TEXT,
    instance_uuid TEXT,
    guest_id TEXT,
    guest_full_name TEXT,
    annotation TEXT,
    
    -- vm.config fields (AS-IS from VMware API)
    change_version TEXT,
    modified TIMESTAMPTZ,
    change_tracking_enabled BOOLEAN,
    firmware TEXT,
    max_mks_connections INT,
    guest_auto_lock_enabled BOOLEAN,
    managed_by_extension_key TEXT,
    managed_by_type TEXT,
    version TEXT,
    
    -- Organizational hierarchy
    folder_path TEXT,
    
    -- Constraints
    PRIMARY KEY (vcenter_uuid, vm_moid, collection_timestamp)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_config_vcenter 
    ON raw_vmware_vm_config(vcenter_uuid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_config_datacenter 
    ON raw_vmware_vm_config(datacenter_moid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_config_cluster 
    ON raw_vmware_vm_config(cluster_moid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_config_host 
    ON raw_vmware_vm_config(host_moid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_config_timestamp 
    ON raw_vmware_vm_config(collection_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_config_data_type 
    ON raw_vmware_vm_config(data_type);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_config_name 
    ON raw_vmware_vm_config(name);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_config_folder_path 
    ON raw_vmware_vm_config(folder_path);

-- Comments
COMMENT ON TABLE raw_vmware_vm_config IS 'VMware VM configuration data - raw fields from vm.summary.config and vm.config';
COMMENT ON COLUMN raw_vmware_vm_config.data_type IS 'Always: vmware_vm_config';
COMMENT ON COLUMN raw_vmware_vm_config.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN raw_vmware_vm_config.memory_size_mb IS 'VM memory size in megabytes (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_vm_config.num_cpu IS 'Number of virtual CPUs (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_vm_config.folder_path IS 'VM folder path in vCenter hierarchy (e.g., production/web-servers)';
