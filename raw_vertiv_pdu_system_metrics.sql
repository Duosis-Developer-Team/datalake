\restrict kcjacKm5IthfCZnvmBXRmGMAmsxn7MjZ2PebIssm2ePHTndVOQcLNYBHVtlhcbC
CREATE TABLE public.raw_vertiv_pdu_system_metrics (
    collection_timestamp timestamp with time zone NOT NULL,
    collection_timestamp_unix bigint NOT NULL,
    collection_date date NOT NULL,
    collection_time time without time zone NOT NULL,
    pdu_name character varying(255) NOT NULL,
    building character varying(100) NOT NULL,
    room character varying(100) NOT NULL,
    unit character varying(100) NOT NULL,
    host_id character varying(50) NOT NULL,
    host_name character varying(255) NOT NULL,
    display_name character varying(255),
    ip_address inet,
    host_status character varying(10),
    status character varying(10) NOT NULL,
    source_system character varying(50) DEFAULT 'zabbix'::character varying
);
ALTER TABLE ONLY public.raw_vertiv_pdu_system_metrics
    ADD CONSTRAINT vertiv_pdu_system_metrics_pkey PRIMARY KEY (pdu_name, collection_timestamp);
CREATE INDEX idx_system_building ON public.raw_vertiv_pdu_system_metrics USING btree (building);
CREATE INDEX idx_system_room ON public.raw_vertiv_pdu_system_metrics USING btree (room);
\unrestrict kcjacKm5IthfCZnvmBXRmGMAmsxn7MjZ2PebIssm2ePHTndVOQcLNYBHVtlhcbC
