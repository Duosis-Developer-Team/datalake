\restrict 6wrpTxgjGvFyXD4zlHTzbRhKQlbN0nzfg3iLqQ2AXhbulQ4ITXDapFAVnYEpEPz
CREATE TABLE public.zabbix_storage_volume_metrics (
    id bigint NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    data_type text NOT NULL,
    host text NOT NULL,
    volume_name text NOT NULL,
    total_capacity_bytes bigint,
    used_capacity_bytes bigint,
    health_status text,
    total_iops numeric(15,2),
    read_iops numeric(15,2),
    write_iops numeric(15,2),
    latency_ms numeric(10,4),
    total_throughput_bps bigint
);
CREATE SEQUENCE public.zabbix_storage_volume_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.zabbix_storage_volume_metrics_id_seq OWNED BY public.zabbix_storage_volume_metrics.id;
ALTER TABLE ONLY public.zabbix_storage_volume_metrics ALTER COLUMN id SET DEFAULT nextval('public.zabbix_storage_volume_metrics_id_seq'::regclass);
ALTER TABLE ONLY public.zabbix_storage_volume_metrics
    ADD CONSTRAINT zabbix_storage_volume_metrics_pkey PRIMARY KEY (id, collection_timestamp);
CREATE INDEX zabbix_storage_volume_metrics_collection_timestamp_idx ON public.zabbix_storage_volume_metrics USING btree (collection_timestamp DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.zabbix_storage_volume_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict 6wrpTxgjGvFyXD4zlHTzbRhKQlbN0nzfg3iLqQ2AXhbulQ4ITXDapFAVnYEpEPz
