\restrict 9RXc6OqwqpPsDbpPtbO9VJVMGUwVKv1lLTwzLjWsAIZbt5AOyExQVa4gJfnaOkI
CREATE TABLE public.raw_vmware_cluster_metrics_agg (
    data_type text NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    vcenter_uuid text NOT NULL,
    datacenter_moid text,
    cluster_moid text NOT NULL,
    cluster_name text,
    window_start timestamp with time zone,
    window_end timestamp with time zone,
    total_host_count integer,
    total_vm_count integer,
    total_cpu_cores integer,
    total_cpu_threads integer,
    total_cpu_mhz_capacity bigint,
    total_cpu_mhz_used bigint,
    total_memory_bytes_capacity bigint,
    total_memory_bytes_used bigint,
    total_storage_bytes_capacity bigint,
    total_storage_bytes_used bigint,
    cpu_usage_avg_percent double precision,
    cpu_usage_min_percent double precision,
    cpu_usage_max_percent double precision,
    memory_usage_avg_percent double precision,
    memory_usage_min_percent double precision,
    memory_usage_max_percent double precision,
    disk_usage_avg_kbps double precision,
    disk_usage_min_kbps double precision,
    disk_usage_max_kbps double precision,
    network_usage_avg_kbps double precision,
    network_usage_min_kbps double precision,
    network_usage_max_kbps double precision
);
CREATE INDEX raw_vmware_cluster_metrics_agg_collection_timestamp_idx ON public.raw_vmware_cluster_metrics_agg USING btree (collection_timestamp DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_vmware_cluster_metrics_agg FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict 9RXc6OqwqpPsDbpPtbO9VJVMGUwVKv1lLTwzLjWsAIZbt5AOyExQVa4gJfnaOkI
