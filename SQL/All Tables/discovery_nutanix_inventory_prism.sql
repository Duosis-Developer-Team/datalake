\restrict 59MtsfHhdVDweYCp5FiDlVGdhq0ZCPF6fnhujt4CARu9U1nW7hwkwkYe1WNbCXF
CREATE TABLE public.discovery_nutanix_inventory_prism (
    id character varying NOT NULL,
    first_observed timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    last_observed timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    nutanix_uuid character varying(255),
    data_type character varying(50),
    component_moid character varying(255),
    name text,
    status character varying(20),
    status_description text
);
CREATE SEQUENCE public.discovery_nutanix_inventory_prism_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.discovery_nutanix_inventory_prism_id_seq OWNED BY public.discovery_nutanix_inventory_prism.id;
ALTER TABLE ONLY public.discovery_nutanix_inventory_prism ALTER COLUMN id SET DEFAULT nextval('public.discovery_nutanix_inventory_prism_id_seq'::regclass);
ALTER TABLE ONLY public.discovery_nutanix_inventory_prism
    ADD CONSTRAINT discovery_nutanix_inventory_prism_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.discovery_nutanix_inventory_prism
    ADD CONSTRAINT uniq_prism_moid UNIQUE (component_moid);
\unrestrict 59MtsfHhdVDweYCp5FiDlVGdhq0ZCPF6fnhujt4CARu9U1nW7hwkwkYe1WNbCXF
