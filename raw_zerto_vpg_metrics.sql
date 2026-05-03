\restrict WDHKTcVGnhSGHEms412dtSa88PYG6zX8vmsomVDYtBJMuWAWbo4cJhWv054jb3F
CREATE TABLE public.raw_zerto_vpg_metrics (
    data_type character varying(50) NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    zerto_host character varying(50) DEFAULT ''::character varying NOT NULL,
    id character varying(255) NOT NULL,
    name character varying(255),
    status integer,
    actualrpo integer,
    vmscount integer,
    alertstatus integer,
    priority integer,
    source_site character varying(255),
    target_site character varying(255),
    vm_identifiers jsonb,
    iops integer,
    throughput_mb numeric(10,4),
    provisioned_storage_mb bigint,
    used_storage_mb bigint
);
ALTER TABLE ONLY public.raw_zerto_vpg_metrics
    ADD CONSTRAINT zerto_vpg_metrics_pkey PRIMARY KEY (id, collection_timestamp);
\unrestrict WDHKTcVGnhSGHEms412dtSa88PYG6zX8vmsomVDYtBJMuWAWbo4cJhWv054jb3F
