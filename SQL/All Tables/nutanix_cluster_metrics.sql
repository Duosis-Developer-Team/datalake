\restrict kr8RcspavaRxDr7PQz0RpXSg3IFFdXRzn5sFbUGRy9klGgORShPgVMi8JGC07g7
CREATE TABLE public.nutanix_cluster_metrics (
    datacenter_name character varying(255) NOT NULL,
    cluster_name character varying(255) NOT NULL,
    cluster_uuid character varying(255) NOT NULL,
    num_nodes integer NOT NULL,
    total_memory_capacity bigint NOT NULL,
    total_cpu_capacity bigint NOT NULL,
    total_vms integer NOT NULL,
    network_transmitted_avg bigint,
    network_received_avg bigint,
    storage_capacity bigint,
    storage_usage bigint,
    memory_usage_min bigint,
    memory_usage_max bigint,
    memory_usage_avg bigint,
    cpu_usage_min bigint,
    cpu_usage_max bigint,
    cpu_usage_avg bigint,
    read_io_bandwidth_min bigint,
    read_io_bandwidth_max bigint,
    read_io_bandwidth_avg bigint,
    write_io_bandwidth_min bigint,
    write_io_bandwidth_max bigint,
    write_io_bandwidth_avg bigint,
    collection_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);
ALTER TABLE ONLY public.nutanix_cluster_metrics
    ADD CONSTRAINT unique_nutanix_cluster_metric_entry UNIQUE (cluster_uuid, collection_time);
CREATE INDEX nutanix_cluster_metrics_collection_time_idx ON public.nutanix_cluster_metrics USING btree (collection_time DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.nutanix_cluster_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict kr8RcspavaRxDr7PQz0RpXSg3IFFdXRzn5sFbUGRy9klGgORShPgVMi8JGC07g7
