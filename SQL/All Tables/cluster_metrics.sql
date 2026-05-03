\restrict kMGQOnmUm4vNruagsKXgAAtSPlvP1fpe52wmMQgS1zeZ9hYthJpYol02g9Kx6Co
CREATE TABLE public.cluster_metrics (
    datacenter text,
    cluster text,
    "timestamp" timestamp without time zone NOT NULL,
    vhost_count integer,
    vm_count integer,
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
    total_freespace_gb numeric(20,2),
    total_capacity_gb numeric(20,2),
    collection_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE ONLY public.cluster_metrics
    ADD CONSTRAINT unique_cluster_timestamp UNIQUE (datacenter, cluster, "timestamp");
CREATE INDEX cluster_metrics_timestamp_idx ON public.cluster_metrics USING btree ("timestamp" DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.cluster_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict kMGQOnmUm4vNruagsKXgAAtSPlvP1fpe52wmMQgS1zeZ9hYthJpYol02g9Kx6Co
