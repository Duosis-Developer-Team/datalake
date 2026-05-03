\restrict Aicdua6MmnvIouVf8f6AbOL9g24T4OPShQ6NvJjbri40JMqX93IfpPfJQkWeMBk
CREATE TABLE public.discovery_nutanix_inventory_host (
    id character varying NOT NULL,
    first_observed timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    last_observed timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    data_type character varying(50) NOT NULL,
    component_moid character varying(255) NOT NULL,
    nutanix_uuid character varying(255),
    parent_component_moid character varying(255),
    component_uuid character varying(255),
    name text,
    status character varying(20),
    status_description text,
    serial character varying(255),
    model text
);
CREATE SEQUENCE public.discovery_nutanix_inventory_host_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.discovery_nutanix_inventory_host_id_seq OWNED BY public.discovery_nutanix_inventory_host.id;
ALTER TABLE ONLY public.discovery_nutanix_inventory_host ALTER COLUMN id SET DEFAULT nextval('public.discovery_nutanix_inventory_host_id_seq'::regclass);
ALTER TABLE ONLY public.discovery_nutanix_inventory_host
    ADD CONSTRAINT discovery_nutanix_inventory_host_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.discovery_nutanix_inventory_host
    ADD CONSTRAINT uniq_host_parent_moid UNIQUE (parent_component_moid, component_moid);
\unrestrict Aicdua6MmnvIouVf8f6AbOL9g24T4OPShQ6NvJjbri40JMqX93IfpPfJQkWeMBk
