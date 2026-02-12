-- VMware Host Storage Relationships Table
-- Data Type: vmware_host_storage
-- Source: host.datastore[]
-- Update Frequency: Medium (storage changes)
-- Primary Key: (vcenter_uuid, host_moid, datastore_moid, collection_timestamp)
-- Granularity: One row per Host-Datastore relationship

CREATE TABLE IF NOT EXISTS raw_vmware_host_storage (
    -- Meta fields
    data_type TEXT NOT NULL,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    vcenter_uuid TEXT NOT NULL,
    host_moid TEXT NOT NULL,
    datastore_moid TEXT NOT NULL,
    
    -- Datastore info (AS-IS from VMware API)
    datastore_name TEXT,
    datastore_url TEXT,
    datastore_capacity BIGINT,
    datastore_free_space BIGINT,
    datastore_type TEXT,
    datastore_accessible BOOLEAN,
    datastore_multiple_host_access BOOLEAN,
    
    -- Constraints
    PRIMARY KEY (vcenter_uuid, host_moid, datastore_moid, collection_timestamp)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_storage_vcenter 
    ON raw_vmware_host_storage(vcenter_uuid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_storage_host 
    ON raw_vmware_host_storage(host_moid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_storage_datastore 
    ON raw_vmware_host_storage(datastore_moid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_storage_timestamp 
    ON raw_vmware_host_storage(collection_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_storage_data_type 
    ON raw_vmware_host_storage(data_type);

-- Comments
COMMENT ON TABLE raw_vmware_host_storage IS 'VMware Host-Datastore relationships - one row per host-datastore pair';
COMMENT ON COLUMN raw_vmware_host_storage.data_type IS 'Always: vmware_host_storage';
COMMENT ON COLUMN raw_vmware_host_storage.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN raw_vmware_host_storage.datastore_capacity IS 'Datastore capacity in bytes (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_host_storage.datastore_free_space IS 'Datastore free space in bytes (AS-IS from VMware API)';
