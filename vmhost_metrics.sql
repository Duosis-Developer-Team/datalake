\restrict FI6lGorXbYxJQy491lpeJ6bmCfoDJejskIzRcEtpT73BqA3csqDboxFX9fdxVnB
CREATE TABLE public.vmhost_metrics (
    datacenter text,
    cluster text,
    vmhost text,
    "timestamp" timestamp without time zone NOT NULL,
    esxi_system_uuid text,
    esxi_bios_uuid text,
    cpu_ghz_capacity numeric(10,2),
    cpu_ghz_used numeric(10,2),
    cpu_ghz_free numeric(10,2),
    memory_capacity_gb numeric(10,2),
    memory_used_gb numeric(10,2),
    memory_free_gb numeric(10,2),
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
    total_freespacegb numeric(20,2),
    total_capacitygb numeric(20,2),
    collection_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    power_usage numeric,
    uptime character varying(255)
);
ALTER TABLE ONLY public.vmhost_metrics
    ADD CONSTRAINT unique_vmhost_timestamp UNIQUE (datacenter, cluster, vmhost, "timestamp");
CREATE INDEX vmhost_metrics_timestamp_idx ON public.vmhost_metrics USING btree ("timestamp" DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.vmhost_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict FI6lGorXbYxJQy491lpeJ6bmCfoDJejskIzRcEtpT73BqA3csqDboxFX9fdxVnB
