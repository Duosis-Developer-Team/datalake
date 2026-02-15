-- VMware Host Performance Raw Samples Table
-- Data Type: vmware_host_perf_raw
-- Source: perfManager.QueryPerf() - raw samples
-- Update Frequency: Very High (300s interval)
-- Primary Key: (vcenter_uuid, host_moid, counter_id, instance, sample_timestamp)
-- Granularity: One row per metric sample

CREATE TABLE IF NOT EXISTS raw_vmware_host_perf_raw (
    -- Meta fields
    data_type TEXT NOT NULL,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    vcenter_uuid TEXT NOT NULL,
    host_moid TEXT NOT NULL,
    
    -- Performance counter metadata
    counter_id INT NOT NULL,
    counter_name TEXT,
    counter_group TEXT,
    counter_name_short TEXT,
    counter_rollup_type TEXT,
    counter_stats_type TEXT,
    counter_unit_key TEXT,
    counter_unit_label TEXT,
    instance TEXT NOT NULL,
    
    -- Sample data (AS-IS from QueryPerf)
    sample_timestamp TIMESTAMPTZ NOT NULL,
    value BIGINT,
    interval_id INT,
    
    -- Constraints
    PRIMARY KEY (vcenter_uuid, host_moid, counter_id, instance, sample_timestamp)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_raw_vcenter 
    ON raw_vmware_host_perf_raw(vcenter_uuid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_raw_host 
    ON raw_vmware_host_perf_raw(host_moid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_raw_counter 
    ON raw_vmware_host_perf_raw(counter_id);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_raw_counter_name 
    ON raw_vmware_host_perf_raw(counter_name);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_raw_sample_timestamp 
    ON raw_vmware_host_perf_raw(sample_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_raw_collection_timestamp 
    ON raw_vmware_host_perf_raw(collection_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_raw_data_type 
    ON raw_vmware_host_perf_raw(data_type);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_raw_host_counter_time 
    ON raw_vmware_host_perf_raw(host_moid, counter_id, sample_timestamp DESC);

-- Comments
COMMENT ON TABLE raw_vmware_host_perf_raw IS 'VMware host performance raw samples - one row per sample from QueryPerf';
COMMENT ON COLUMN raw_vmware_host_perf_raw.data_type IS 'Always: vmware_host_perf_raw';
COMMENT ON COLUMN raw_vmware_host_perf_raw.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN raw_vmware_host_perf_raw.sample_timestamp IS 'Actual timestamp of the performance sample';
COMMENT ON COLUMN raw_vmware_host_perf_raw.value IS 'Raw metric value (AS-IS from VMware API, no conversion)';

-- Table partitioning recommendation
-- Consider partitioning by sample_timestamp (weekly or monthly) for large environments
