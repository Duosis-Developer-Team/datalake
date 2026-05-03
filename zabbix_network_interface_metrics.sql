\restrict Mr6XYhEsihxfrWR0XQvWmByxWRFfYaPaSOPtt9DaLurVz3WlpZXPbmWANiq1BSd
CREATE TABLE public.zabbix_network_interface_metrics (
    id bigint NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    data_type character varying(50) NOT NULL,
    host character varying(255) NOT NULL,
    interface_name character varying(255) NOT NULL,
    interface_alias character varying(255),
    operational_status integer,
    duplex_status integer,
    speed bigint,
    bits_received bigint,
    bits_sent bigint,
    inbound_packets_discarded bigint,
    inbound_packets_with_errors bigint,
    outbound_packets_discarded bigint,
    outbound_packets_with_errors bigint,
    interface_type integer
);
CREATE SEQUENCE public.zabbix_network_interface_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.zabbix_network_interface_metrics_id_seq OWNED BY public.zabbix_network_interface_metrics.id;
ALTER TABLE ONLY public.zabbix_network_interface_metrics ALTER COLUMN id SET DEFAULT nextval('public.zabbix_network_interface_metrics_id_seq'::regclass);
ALTER TABLE ONLY public.zabbix_network_interface_metrics
    ADD CONSTRAINT zabbix_network_interface_metrics_pkey PRIMARY KEY (id, collection_timestamp);
CREATE INDEX idx_zabbix_net_iface_host_name ON public.zabbix_network_interface_metrics USING btree (host, interface_name, collection_timestamp DESC);
CREATE INDEX zabbix_network_interface_metrics_collection_timestamp_idx ON public.zabbix_network_interface_metrics USING btree (collection_timestamp DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.zabbix_network_interface_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict Mr6XYhEsihxfrWR0XQvWmByxWRFfYaPaSOPtt9DaLurVz3WlpZXPbmWANiq1BSd
