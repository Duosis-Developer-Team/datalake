\restrict qoKdp8nAdUs9kn7HilWBfsmxfu7hGzXk9mtojcu1bAfgU1Mc54nt8Dt7VCcAUXf
CREATE TABLE public.discovery_loki_rack (
    id character varying(255) NOT NULL,
    component_moid character varying(255),
    parent_component_moid character varying(255),
    data_type character varying(50) DEFAULT 'loki_inventory_rack'::character varying,
    name character varying(255),
    display_name character varying(255),
    status character varying(50),
    status_description text,
    description text,
    comments text,
    facility_id character varying(255),
    serial character varying(255),
    asset_tag character varying(255),
    rack_type character varying(255),
    u_height integer,
    weight integer,
    max_weight integer,
    weight_unit character varying(50),
    kabin_enerji character varying(255),
    pdu_a_ip character varying(255),
    pdu_b_ip character varying(255),
    site_id character varying(255),
    location_id character varying(255),
    role_id character varying(255),
    tenant_name character varying(255),
    tags jsonb,
    first_observed character varying DEFAULT CURRENT_TIMESTAMP,
    last_observed character varying DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE ONLY public.discovery_loki_rack
    ADD CONSTRAINT discovery_loki_rack_component_moid_key UNIQUE (component_moid);
ALTER TABLE ONLY public.discovery_loki_rack
    ADD CONSTRAINT discovery_loki_rack_pkey PRIMARY KEY (id);
\unrestrict qoKdp8nAdUs9kn7HilWBfsmxfu7hGzXk9mtojcu1bAfgU1Mc54nt8Dt7VCcAUXf
