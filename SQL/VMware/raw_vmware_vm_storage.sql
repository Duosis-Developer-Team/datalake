-- VMware VM Storage Relationships Table
-- Data Type: vmware_vm_storage
-- Source: vm.datastore[], vm.summary.storage
-- Update Frequency: Medium (storage changes)
-- Primary Key: (vcenter_uuid, vm_moid, datastore_moid, collection_timestamp)
-- Granularity: One row per VM-Datastore relationship

CREATE TABLE IF NOT EXISTS raw_vmware_vm_storage (
    -- Meta fields
    data_type TEXT NOT NULL,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    vcenter_uuid TEXT NOT NULL,
    vm_moid TEXT NOT NULL,
    datastore_moid TEXT NOT NULL,
    
    -- Datastore info (AS-IS from VMware API)
    datastore_name TEXT,
    datastore_url TEXT,
    datastore_capacity BIGINT,
    datastore_free_space BIGINT,
    datastore_type TEXT,
    datastore_accessible BOOLEAN,
    datastore_multiple_host_access BOOLEAN,
    
    -- VM storage usage (snapshot at collection time, AS-IS)
    committed BIGINT,
    uncommitted BIGINT,
    unshared BIGINT,
    
    -- Constraints
    PRIMARY KEY (vcenter_uuid, vm_moid, datastore_moid, collection_timestamp)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_storage_vcenter 
    ON raw_vmware_vm_storage(vcenter_uuid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_storage_vm 
    ON raw_vmware_vm_storage(vm_moid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_storage_datastore 
    ON raw_vmware_vm_storage(datastore_moid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_storage_timestamp 
    ON raw_vmware_vm_storage(collection_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_storage_data_type 
    ON raw_vmware_vm_storage(data_type);

-- Comments
COMMENT ON TABLE raw_vmware_vm_storage IS 'VMware VM-Datastore relationships - one row per VM-datastore pair';
COMMENT ON COLUMN raw_vmware_vm_storage.data_type IS 'Always: vmware_vm_storage';
COMMENT ON COLUMN raw_vmware_vm_storage.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN raw_vmware_vm_storage.datastore_capacity IS 'Datastore capacity in bytes (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_vm_storage.datastore_free_space IS 'Datastore free space in bytes (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_vm_storage.committed IS 'VM committed storage in bytes (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_vm_storage.uncommitted IS 'VM uncommitted storage in bytes (AS-IS from VMware API)';
