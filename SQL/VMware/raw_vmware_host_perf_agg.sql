-- VMware Host Performance Aggregated Table
-- Data Type: vmware_host_perf_agg
-- Source: Calculated from raw samples (optimization table)
-- Update Frequency: Very High (300s interval)
-- Primary Key: (vcenter_uuid, host_moid, counter_id, instance, window_start, window_end)
-- Purpose: Pre-calculated avg/min/max for query optimization

CREATE TABLE IF NOT EXISTS raw_vmware_host_perf_agg (
    -- Meta fields
    data_type TEXT NOT NULL,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    vcenter_uuid TEXT NOT NULL,
    host_moid TEXT NOT NULL,
    
    -- Aggregation window
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    window_duration_seconds INT,
    sample_count INT,
    
    -- Performance counter metadata
    counter_id INT NOT NULL,
    counter_name TEXT,
    counter_group TEXT,
    counter_rollup_type TEXT,
    counter_unit_key TEXT,
    instance TEXT NOT NULL,
    
    -- Aggregated values (calculated from raw samples)
    value_avg DOUBLE PRECISION,
    value_min BIGINT,
    value_max BIGINT,
    value_stddev DOUBLE PRECISION,
    value_first BIGINT,
    value_last BIGINT,
    
    -- Constraints
    PRIMARY KEY (vcenter_uuid, host_moid, counter_id, instance, window_start, window_end)
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_agg_vcenter 
    ON raw_vmware_host_perf_agg(vcenter_uuid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_agg_host 
    ON raw_vmware_host_perf_agg(host_moid);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_agg_counter 
    ON raw_vmware_host_perf_agg(counter_id);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_agg_counter_name 
    ON raw_vmware_host_perf_agg(counter_name);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_agg_window_end 
    ON raw_vmware_host_perf_agg(window_end DESC);

CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_agg_data_type 
    ON raw_vmware_host_perf_agg(data_type);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_raw_vmware_host_perf_agg_host_counter_time 
    ON raw_vmware_host_perf_agg(host_moid, counter_id, window_end DESC);

-- Comments
COMMENT ON TABLE raw_vmware_host_perf_agg IS 'VMware host performance aggregated - avg/min/max calculated from raw samples';
COMMENT ON COLUMN raw_vmware_host_perf_agg.data_type IS 'Always: vmware_host_perf_agg';
COMMENT ON COLUMN raw_vmware_host_perf_agg.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN raw_vmware_host_perf_agg.window_start IS 'Start of aggregation window';
COMMENT ON COLUMN raw_vmware_host_perf_agg.window_end IS 'End of aggregation window';
COMMENT ON COLUMN raw_vmware_host_perf_agg.value_avg IS 'Average value across samples';
COMMENT ON COLUMN raw_vmware_host_perf_agg.value_min IS 'Minimum value across samples';
COMMENT ON COLUMN raw_vmware_host_perf_agg.value_max IS 'Maximum value across samples';
