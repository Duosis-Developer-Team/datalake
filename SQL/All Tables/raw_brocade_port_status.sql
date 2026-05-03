\restrict 4Sa8zo0MkTJdW3D9GSq32hK9aaKYRLMQCWDaXzzkDMUFGkbrD76eiPMWBsoOcGy
CREATE TABLE public.raw_brocade_port_status (
    switch_host character varying(255) NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    name character varying(50) NOT NULL,
    wwn character varying(23),
    port_type integer,
    speed bigint,
    max_speed bigint,
    user_friendly_name character varying(255),
    operational_status integer,
    is_enabled_state boolean,
    auto_negotiate integer,
    isl_ready_mode_enabled integer,
    long_distance integer,
    trunk_port_enabled integer,
    vc_link_init integer,
    pod_license_status boolean,
    default_index integer,
    fcid integer,
    fcid_hex character varying(10),
    physical_state character varying(50),
    persistent_disable integer,
    g_port_locked integer,
    e_port_disable integer,
    ex_port_enabled integer,
    npiv_enabled integer,
    qos_enabled integer,
    fec_enabled integer,
    fec_active integer,
    credit_recovery_enabled integer,
    credit_recovery_active integer,
    neighbor_node_wwn character varying(23)
);
COMMENT ON TABLE public.raw_brocade_port_status IS 'Her bir Brocade switch portunun anlık fiziksel ve operasyonel durum bilgilerini içerir.';
COMMENT ON COLUMN public.raw_brocade_port_status.name IS 'Portun fiziksel adı (örn: 0/15)';
COMMENT ON COLUMN public.raw_brocade_port_status.operational_status IS 'Portun operasyonel durumu (örn: 2=Online, 3=Offline)';
COMMENT ON COLUMN public.raw_brocade_port_status.physical_state IS 'Portun fiziksel katman durumu (örn: online, no_light)';
ALTER TABLE ONLY public.raw_brocade_port_status
    ADD CONSTRAINT brocade_port_status_pkey PRIMARY KEY (switch_host, collection_timestamp, name);
\unrestrict 4Sa8zo0MkTJdW3D9GSq32hK9aaKYRLMQCWDaXzzkDMUFGkbrD76eiPMWBsoOcGy
