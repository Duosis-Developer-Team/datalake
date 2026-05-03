\restrict h0uZpaosjhe71aTetSObYECO3zt9V4OcIf58joY4VsbLaoZAoFbWsUN19pVKcug
CREATE TABLE public.nutanix_host_metrics (
    id integer DEFAULT nextval('public.nutanix_host_metrics_id_seq'::regclass) NOT NULL,
    host_name character varying(255) NOT NULL,
    host_uuid character varying(255) NOT NULL,
    cluster_uuid character varying(255) NOT NULL,
    total_memory_capacity bigint NOT NULL,
    total_cpu_capacity bigint NOT NULL,
    num_cpu_cores integer NOT NULL,
    total_vms integer NOT NULL,
    network_transmitted_avg bigint,
    network_received_avg bigint,
    memory_usage_min bigint,
    memory_usage_max bigint,
    memory_usage_avg bigint,
    cpu_usage_min bigint,
    cpu_usage_max bigint,
    cpu_usage_avg bigint,
    storage_capacity bigint NOT NULL,
    storage_usage bigint NOT NULL,
    read_io_bandwidth_min bigint,
    read_io_bandwidth_max bigint,
    read_io_bandwidth_avg bigint,
    write_io_bandwidth_min bigint,
    write_io_bandwidth_max bigint,
    write_io_bandwidth_avg bigint,
    collectiontime timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    boottime bigint
);
ALTER TABLE ONLY public.nutanix_host_metrics
    ADD CONSTRAINT unique_nutanix_host_metric_entry UNIQUE (host_uuid, collectiontime);
CREATE INDEX nutanix_host_metrics_collectiontime_idx ON public.nutanix_host_metrics USING btree (collectiontime DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.nutanix_host_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict h0uZpaosjhe71aTetSObYECO3zt9V4OcIf58joY4VsbLaoZAoFbWsUN19pVKcug
