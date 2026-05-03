\restrict ZBkVBYg6ScKvcgL1pvyqMW32raFlfNfygLrxqJigJvO5a7XRvCPcpCwHXEhQRZR
CREATE TABLE public.raw_zerto_vm_metrics (
    data_type character varying(50) NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    zerto_host character varying(50) DEFAULT ''::character varying NOT NULL,
    id character varying(255) NOT NULL,
    vm_identifier character varying(255),
    vm_name character varying(255),
    name character varying(255),
    status integer,
    vpg_identifier character varying(255),
    cpu_count integer,
    memory_mb bigint,
    disk_count integer,
    vm_network_count integer,
    os character varying(100),
    ip_addresses jsonb,
    disk_info jsonb,
    is_protected boolean,
    is_archived boolean,
    is_offline boolean
);
ALTER TABLE ONLY public.raw_zerto_vm_metrics
    ADD CONSTRAINT zerto_vm_metrics_pkey PRIMARY KEY (id, collection_timestamp);
\unrestrict ZBkVBYg6ScKvcgL1pvyqMW32raFlfNfygLrxqJigJvO5a7XRvCPcpCwHXEhQRZR
