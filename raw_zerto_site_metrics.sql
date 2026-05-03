\restrict mO5dhU75fcxYU2FtQfN1ZYNS6jZ5gEHgrtTlZrbPgTqYItOFcU5EUFPsuB3fSEp
CREATE TABLE public.raw_zerto_site_metrics (
    data_type character varying(50) NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    zerto_host character varying(50) DEFAULT ''::character varying NOT NULL,
    id character varying(255) NOT NULL,
    name character varying(255),
    status integer,
    ip character varying(50),
    site_type character varying(100),
    version character varying(100),
    port integer,
    is_connected character varying(10),
    location character varying(255),
    incoming_throughput_mb numeric(10,4),
    outgoing_bandwidth_mb numeric(10,4),
    provisioned_storage_mb bigint,
    used_storage_mb bigint
);
ALTER TABLE ONLY public.raw_zerto_site_metrics
    ADD CONSTRAINT zerto_site_metrics_pkey PRIMARY KEY (id, collection_timestamp);
\unrestrict mO5dhU75fcxYU2FtQfN1ZYNS6jZ5gEHgrtTlZrbPgTqYItOFcU5EUFPsuB3fSEp
