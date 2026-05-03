\restrict ZoIGRHXutDpuq5kHAZFJByZVw3eVGinxXGH3m5y5236J8ylUc5LbgtQap33fyHH
CREATE TABLE public.zabbix_storage_disk_metrics (
    id bigint NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    data_type text NOT NULL,
    host text NOT NULL,
    disk_name text NOT NULL,
    health_status text,
    running_status text,
    temperature_c numeric(5,2),
    total_capacity_bytes bigint,
    free_capacity_bytes bigint,
    read_iops numeric(15,2),
    write_iops numeric(15,2),
    total_iops numeric(15,2),
    latency_ms numeric(10,4),
    total_throughput_bps bigint
);
CREATE SEQUENCE public.zabbix_storage_disk_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.zabbix_storage_disk_metrics_id_seq OWNED BY public.zabbix_storage_disk_metrics.id;
ALTER TABLE ONLY public.zabbix_storage_disk_metrics ALTER COLUMN id SET DEFAULT nextval('public.zabbix_storage_disk_metrics_id_seq'::regclass);
ALTER TABLE ONLY public.zabbix_storage_disk_metrics
    ADD CONSTRAINT zabbix_storage_disk_metrics_pkey PRIMARY KEY (id, collection_timestamp);
CREATE INDEX zabbix_storage_disk_metrics_collection_timestamp_idx ON public.zabbix_storage_disk_metrics USING btree (collection_timestamp DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.zabbix_storage_disk_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict ZoIGRHXutDpuq5kHAZFJByZVw3eVGinxXGH3m5y5236J8ylUc5LbgtQap33fyHH
