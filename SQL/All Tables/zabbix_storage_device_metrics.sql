\restrict qsHce5kfzojhIscxaGFsbb7QjD05QHs7XPGmFRAfeSqk2AQvX3IDngiDp4IDrcl
CREATE TABLE public.zabbix_storage_device_metrics (
    id bigint NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    data_type text NOT NULL,
    host text NOT NULL,
    location text,
    loki_id text,
    total_capacity_bytes bigint,
    used_capacity_bytes bigint,
    free_capacity_bytes bigint,
    health_status text,
    applied_templates text
);
CREATE SEQUENCE public.zabbix_storage_device_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.zabbix_storage_device_metrics_id_seq OWNED BY public.zabbix_storage_device_metrics.id;
ALTER TABLE ONLY public.zabbix_storage_device_metrics ALTER COLUMN id SET DEFAULT nextval('public.zabbix_storage_device_metrics_id_seq'::regclass);
ALTER TABLE ONLY public.zabbix_storage_device_metrics
    ADD CONSTRAINT zabbix_storage_device_metrics_pkey PRIMARY KEY (id, collection_timestamp);
CREATE INDEX zabbix_storage_device_metrics_collection_timestamp_idx ON public.zabbix_storage_device_metrics USING btree (collection_timestamp DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.zabbix_storage_device_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict qsHce5kfzojhIscxaGFsbb7QjD05QHs7XPGmFRAfeSqk2AQvX3IDngiDp4IDrcl
