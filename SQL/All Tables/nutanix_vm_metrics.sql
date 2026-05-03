\restrict tvTp44tgcBh38V1uhAncqvIbFrvVUsMYHUowUsqle9ZGn9DgONaO7Yv206Jbjln
CREATE TABLE public.nutanix_vm_metrics (
    vm_name character varying(255) NOT NULL,
    vm_uuid uuid NOT NULL,
    cluster_uuid uuid NOT NULL,
    host_name character varying(255),
    host_uuid uuid,
    power_state character varying(10),
    memory_capacity bigint,
    cpu_count integer,
    disk_capacity bigint,
    hypervisor_read_io_bandwidth_min bigint,
    hypervisor_read_io_bandwidth_max bigint,
    hypervisor_read_io_bandwidth_avg bigint,
    hypervisor_write_io_bandwidth_min bigint,
    hypervisor_write_io_bandwidth_max bigint,
    hypervisor_write_io_bandwidth_avg bigint,
    cpu_usage_min bigint,
    cpu_usage_max bigint,
    cpu_usage_avg bigint,
    memory_usage_min bigint,
    memory_usage_max bigint,
    memory_usage_avg bigint,
    collection_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    used_storage bigint,
    guest_os character varying,
    power_usage numeric
);
CREATE INDEX nutanix_vm_metrics_collection_time_idx ON public.nutanix_vm_metrics USING btree (collection_time DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.nutanix_vm_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict tvTp44tgcBh38V1uhAncqvIbFrvVUsMYHUowUsqle9ZGn9DgONaO7Yv206Jbjln
