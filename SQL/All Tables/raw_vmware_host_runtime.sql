\restrict N8L80WGZKnJFjfXZCNlpetyxJiJHgHNHFYaeDB5r0fglrnwXBNkm522rP19NPCH
CREATE TABLE public.raw_vmware_host_runtime (
    data_type text NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    vcenter_uuid text NOT NULL,
    host_moid text NOT NULL,
    connection_state text,
    power_state text,
    standby_mode text,
    in_maintenance_mode boolean,
    in_quarantine_mode boolean,
    boot_time timestamp with time zone,
    health_system_runtime_system_health_info text,
    quick_stats_overall_cpu_usage integer,
    quick_stats_overall_memory_usage integer,
    quick_stats_distributed_cpu_fairness integer,
    quick_stats_distributed_memory_fairness integer,
    quick_stats_uptime bigint,
    config_name text,
    config_port integer,
    config_ssl_thumbprint text
);
CREATE INDEX raw_vmware_host_runtime_collection_timestamp_idx ON public.raw_vmware_host_runtime USING btree (collection_timestamp DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_vmware_host_runtime FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict N8L80WGZKnJFjfXZCNlpetyxJiJHgHNHFYaeDB5r0fglrnwXBNkm522rP19NPCH
