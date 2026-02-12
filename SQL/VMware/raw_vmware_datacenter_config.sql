-- VMware Datacenter Configuration Table
-- Data Type: vmware_datacenter_config
-- Source: datacenter
-- Update Frequency: Very Low (datacenter config rarely changes)
-- Primary Key: (vcenter_uuid, datacenter_moid, collection_timestamp)

CREATE TABLE IF NOT EXISTS raw_vmware_datacenter_config (
    -- Meta fields
    data_type TEXT NOT NULL,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    vcenter_uuid TEXT NOT NULL,
    datacenter_moid TEXT NOT NULL,
    
    -- datacenter basic info (AS-IS from VMware API)
    name TEXT,
    overall_status TEXT,
    
    -- Constraints
    PRIMARY KEY (vcenter_uuid, datacenter_moid, collection_timestamp)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_raw_vmware_datacenter_config_vcenter 
    ON raw_vmware_datacenter_config(vcenter_uuid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_datacenter_config_timestamp 
    ON raw_vmware_datacenter_config(collection_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_datacenter_config_data_type 
    ON raw_vmware_datacenter_config(data_type);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_datacenter_config_name 
    ON raw_vmware_datacenter_config(name);

-- Comments
COMMENT ON TABLE raw_vmware_datacenter_config IS 'VMware datacenter configuration - minimal config info';
COMMENT ON COLUMN raw_vmware_datacenter_config.data_type IS 'Always: vmware_datacenter_config';
COMMENT ON COLUMN raw_vmware_datacenter_config.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN raw_vmware_datacenter_config.overall_status IS 'Overall status (green/yellow/red)';
