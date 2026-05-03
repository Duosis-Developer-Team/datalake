\restrict Qz1cRNwvZEcbpXk8MbfBR3261I6i7fTL3DqM2bOnSXkSO5M5oUnbLkAglatxqmY
CREATE TABLE public.datacenter_metrics (
    datacenter text,
    "timestamp" timestamp without time zone NOT NULL,
    total_memory_capacity_gb numeric(10,2),
    total_memory_used_gb numeric(10,2),
    total_storage_capacity_gb numeric(20,4),
    total_used_storage_gb numeric(20,4),
    total_cpu_ghz_capacity numeric(10,2),
    total_cpu_ghz_used numeric(10,2),
    disk_usage_avg_kbps numeric(15,2),
    disk_usage_min_kbps numeric(15,0),
    disk_usage_max_kbps numeric(15,0),
    network_usage_avg_kbps numeric(15,2),
    network_usage_min_kbps numeric(15,0),
    network_usage_max_kbps numeric(15,0),
    memory_usage_avg_perc numeric(7,2),
    memory_usage_min_perc numeric(7,2),
    memory_usage_max_perc numeric(7,2),
    cpu_usage_avg_perc numeric(7,2),
    cpu_usage_min_perc numeric(7,2),
    cpu_usage_max_perc numeric(7,2),
    total_host_count integer,
    total_vm_count integer,
    total_cluster_count integer,
    collection_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    dc character varying(50)
);
ALTER TABLE ONLY public.datacenter_metrics
    ADD CONSTRAINT unique_dc_timestamp_entry UNIQUE (datacenter, "timestamp");
CREATE INDEX datacenter_metrics_timestamp_idx ON public.datacenter_metrics USING btree ("timestamp" DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.datacenter_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict Qz1cRNwvZEcbpXk8MbfBR3261I6i7fTL3DqM2bOnSXkSO5M5oUnbLkAglatxqmY
