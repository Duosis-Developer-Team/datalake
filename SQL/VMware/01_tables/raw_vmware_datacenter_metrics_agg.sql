-- VMware Datacenter Aggregated Metrics Table
-- Data Type: vmware_datacenter_metrics_agg
-- Source: Script-calculated aggregations from hosts (NOT raw API data)
-- Update Frequency: High (every collection cycle)
-- Primary Key: (vcenter_uuid, datacenter_moid, collection_timestamp)
-- NOTE: This is an optimization table with pre-calculated aggregations

CREATE TABLE IF NOT EXISTS raw_vmware_datacenter_metrics_agg (
    -- Meta fields
    data_type TEXT NOT NULL,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    vcenter_uuid TEXT NOT NULL,
    datacenter_moid TEXT NOT NULL,
    datacenter_name TEXT,
    
    -- Aggregation window
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    
    -- Counts (from inventory)
    total_cluster_count INT,
    total_host_count INT,
    total_vm_count INT,
    
    -- CPU Aggregates (summed from hosts, in MHz)
    total_cpu_cores INT,
    total_cpu_threads INT,
    total_cpu_mhz_capacity BIGINT,
    total_cpu_mhz_used BIGINT,
    
    -- Memory Aggregates (summed from hosts, in bytes)
    total_memory_bytes_capacity BIGINT,
    total_memory_bytes_used BIGINT,
    
    -- Storage Aggregates (summed from datastores, in bytes)
    total_storage_bytes_capacity BIGINT,
    total_storage_bytes_used BIGINT,
    
    -- Performance Aggregates (averaged from hosts, percentages)
    cpu_usage_avg_percent DOUBLE PRECISION,
    cpu_usage_min_percent DOUBLE PRECISION,
    cpu_usage_max_percent DOUBLE PRECISION,
    memory_usage_avg_percent DOUBLE PRECISION,
    memory_usage_min_percent DOUBLE PRECISION,
    memory_usage_max_percent DOUBLE PRECISION,
    
    -- Disk I/O Aggregates (summed from hosts, KBps)
    disk_usage_avg_kbps DOUBLE PRECISION,
    disk_usage_min_kbps DOUBLE PRECISION,
    disk_usage_max_kbps DOUBLE PRECISION,
    
    -- Network Aggregates (summed from hosts, KBps)
    network_usage_avg_kbps DOUBLE PRECISION,
    network_usage_min_kbps DOUBLE PRECISION,
    network_usage_max_kbps DOUBLE PRECISION,
    
    -- Constraints
    PRIMARY KEY (vcenter_uuid, datacenter_moid, collection_timestamp)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_raw_vmware_datacenter_metrics_agg_vcenter 
    ON raw_vmware_datacenter_metrics_agg(vcenter_uuid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_datacenter_metrics_agg_timestamp 
    ON raw_vmware_datacenter_metrics_agg(collection_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_datacenter_metrics_agg_data_type 
    ON raw_vmware_datacenter_metrics_agg(data_type);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_datacenter_metrics_agg_name 
    ON raw_vmware_datacenter_metrics_agg(datacenter_name);

-- Comments
COMMENT ON TABLE raw_vmware_datacenter_metrics_agg IS 'VMware datacenter aggregated metrics - calculated from host data for optimization';
COMMENT ON COLUMN raw_vmware_datacenter_metrics_agg.data_type IS 'Always: vmware_datacenter_metrics_agg';
COMMENT ON COLUMN raw_vmware_datacenter_metrics_agg.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN raw_vmware_datacenter_metrics_agg.total_cpu_mhz_capacity IS 'Total CPU capacity in MHz (summed from hosts)';
COMMENT ON COLUMN raw_vmware_datacenter_metrics_agg.total_cpu_mhz_used IS 'Total CPU used in MHz (summed from hosts)';
COMMENT ON COLUMN raw_vmware_datacenter_metrics_agg.total_memory_bytes_capacity IS 'Total memory capacity in bytes (summed from hosts)';
COMMENT ON COLUMN raw_vmware_datacenter_metrics_agg.total_memory_bytes_used IS 'Total memory used in bytes (summed from hosts)';

-- WARNING: This table contains pre-calculated aggregations, NOT raw VMware API data.
-- The same data can be derived from raw_vmware_host_* tables using SQL,
-- but this table provides faster access for dashboards and reporting.
