\restrict UuRJqlCI84BGFcGfMznLXniLiWNa1RzupfNmqRGeh6bK5HHfXGFhgLRv5sMCwXf
CREATE TABLE public.vm_metrics (
    datacenter text,
    cluster text,
    vmhost text,
    vmname text NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    number_of_cpus integer,
    cpu_usage_avg_mhz numeric(10,2),
    cpu_usage_min_mhz numeric(10,2),
    cpu_usage_max_mhz numeric(10,2),
    memory_usage_avg_perc numeric(5,2),
    memory_usage_min_perc numeric(5,2),
    memory_usage_max_perc numeric(5,2),
    disk_usage_avg_kbps numeric(10,2),
    disk_usage_min_kbps numeric(10,2),
    disk_usage_max_kbps numeric(10,2),
    guest_os text,
    datastore text,
    used_space_gb numeric(10,2),
    provisioned_space_gb numeric(10,2),
    folder text,
    uuid text NOT NULL,
    collection_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    total_cpu_capacity_mhz numeric(20,4),
    total_memory_capacity_gb numeric(20,4),
    esxi_system_uuid character varying(36),
    boottime character varying(255)
);
ALTER TABLE ONLY public.vm_metrics
    ADD CONSTRAINT vm_metrics_datacenter_cluster_vmhost_uuid_timestamp_key UNIQUE (datacenter, cluster, vmhost, uuid, "timestamp");
CREATE INDEX vm_metrics_vmname_idx ON public.vm_metrics USING btree (vmname, "timestamp");
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.vm_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict UuRJqlCI84BGFcGfMznLXniLiWNa1RzupfNmqRGeh6bK5HHfXGFhgLRv5sMCwXf
