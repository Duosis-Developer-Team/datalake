\restrict WCTakz4lpCiT2MiejDsdgh7CpR0Fz5FXEg6MlyRP55JEVUMvxGcC0vq1zdIamBT
CREATE TABLE public.raw_zerto_vra_metrics (
    data_type character varying(50) NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    zerto_host character varying(50) DEFAULT ''::character varying NOT NULL,
    id character varying(255) NOT NULL,
    name character varying(255),
    ip character varying(50),
    status integer,
    version character varying(100),
    host_name character varying(255),
    datastore_identifier character varying(255),
    datastore_name character varying(255),
    network_name character varying(255),
    is_connected boolean,
    is_stale boolean,
    cpu_count integer,
    memory_mb bigint,
    vpgcount integer,
    vmcount integer,
    alarmstatus integer
);
ALTER TABLE ONLY public.raw_zerto_vra_metrics
    ADD CONSTRAINT zerto_vra_metrics_pkey PRIMARY KEY (id, collection_timestamp);
\unrestrict WCTakz4lpCiT2MiejDsdgh7CpR0Fz5FXEg6MlyRP55JEVUMvxGcC0vq1zdIamBT
