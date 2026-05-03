\restrict x30VCYhl2V7dS8zVeXwxb8TMHHi46GsrZvPrtf63UQKag1teI9loxMUhZvWvdlB
CREATE TABLE public.zabbix_network_device_metrics (
    id bigint NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    data_type character varying(50) NOT NULL,
    host character varying(255) NOT NULL,
    location character varying(255),
    loki_id character varying(100),
    applied_templates text,
    icmp_status integer,
    icmp_loss_pct numeric(5,2),
    icmp_response_time_ms numeric(10,4),
    cpu_utilization_pct numeric(5,2),
    memory_utilization_pct numeric(5,2),
    uptime_seconds bigint,
    system_name character varying(255),
    system_description text,
    total_ports_count integer,
    active_ports_count integer
);
CREATE SEQUENCE public.zabbix_network_device_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.zabbix_network_device_metrics_id_seq OWNED BY public.zabbix_network_device_metrics.id;
ALTER TABLE ONLY public.zabbix_network_device_metrics ALTER COLUMN id SET DEFAULT nextval('public.zabbix_network_device_metrics_id_seq'::regclass);
ALTER TABLE ONLY public.zabbix_network_device_metrics
    ADD CONSTRAINT zabbix_network_device_metrics_pkey PRIMARY KEY (id, collection_timestamp);
CREATE INDEX idx_zabbix_net_device_host ON public.zabbix_network_device_metrics USING btree (host, collection_timestamp DESC);
CREATE INDEX zabbix_network_device_metrics_collection_timestamp_idx ON public.zabbix_network_device_metrics USING btree (collection_timestamp DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.zabbix_network_device_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict x30VCYhl2V7dS8zVeXwxb8TMHHi46GsrZvPrtf63UQKag1teI9loxMUhZvWvdlB
