-- VMware Host Hardware Configuration Table
-- Data Type: vmware_host_hardware
-- Source: host.hardware, host.summary.hardware, host.config.product
-- Update Frequency: Very Low (hardware rarely changes)
-- Primary Key: (vcenter_uuid, host_moid, collection_timestamp)

CREATE TABLE IF NOT EXISTS raw_vmware_host_hardware (
    -- Meta fields
    data_type TEXT NOT NULL,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    vcenter_uuid TEXT NOT NULL,
    datacenter_moid TEXT,
    cluster_moid TEXT,
    host_moid TEXT NOT NULL,
    
    -- host.summary.hardware fields (AS-IS from VMware API)
    vendor TEXT,
    model TEXT,
    uuid TEXT,
    memory_size BIGINT,
    cpu_model TEXT,
    cpu_mhz INT,
    num_cpu_pkgs INT,
    num_cpu_cores INT,
    num_cpu_threads INT,
    num_nics INT,
    num_hbas INT,
    
    -- host.hardware.systemInfo fields (AS-IS from VMware API)
    system_info_vendor TEXT,
    system_info_model TEXT,
    system_info_uuid TEXT,
    system_info_other_identifying_info TEXT,
    
    -- host.config.product fields (AS-IS from VMware API)
    product_name TEXT,
    product_full_name TEXT,
    product_vendor TEXT,
    product_version TEXT,
    product_build TEXT,
    product_locale_version TEXT,
    product_locale_build TEXT,
    product_os_type TEXT,
    product_product_line_id TEXT,
    product_api_type TEXT,
    product_api_version TEXT,
    product_license_product_name TEXT,
    product_license_product_version TEXT,
    
    -- Constraints
    PRIMARY KEY (vcenter_uuid, host_moid, collection_timestamp)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_hardware_vcenter 
    ON raw_vmware_host_hardware(vcenter_uuid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_hardware_datacenter 
    ON raw_vmware_host_hardware(datacenter_moid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_hardware_cluster 
    ON raw_vmware_host_hardware(cluster_moid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_hardware_timestamp 
    ON raw_vmware_host_hardware(collection_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_hardware_data_type 
    ON raw_vmware_host_hardware(data_type);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_hardware_uuid 
    ON raw_vmware_host_hardware(uuid);

-- Comments
COMMENT ON TABLE raw_vmware_host_hardware IS 'VMware ESXi host hardware configuration - raw fields from host.hardware and host.config';
COMMENT ON COLUMN raw_vmware_host_hardware.data_type IS 'Always: vmware_host_hardware';
COMMENT ON COLUMN raw_vmware_host_hardware.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN raw_vmware_host_hardware.memory_size IS 'Total memory in bytes (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_host_hardware.cpu_mhz IS 'CPU frequency in MHz (AS-IS from VMware API)';
COMMENT ON COLUMN raw_vmware_host_hardware.num_cpu_cores IS 'Number of physical CPU cores (AS-IS from VMware API)';
