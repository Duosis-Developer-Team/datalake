\restrict PipGtC9LR3ER1ZdovUWHe4jOvHeot8QC40sUmhipLqEhd1p8RyDe7CfI7WJuHMQ
CREATE TABLE public.discovery_nutanix_inventory_vm (
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
    guest_os character varying(255),
    memory_mb bigint,
    num_vcpus integer
);
CREATE SEQUENCE public.discovery_nutanix_inventory_vm_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.discovery_nutanix_inventory_vm_id_seq OWNED BY public.discovery_nutanix_inventory_vm.id;
ALTER TABLE ONLY public.discovery_nutanix_inventory_vm ALTER COLUMN id SET DEFAULT nextval('public.discovery_nutanix_inventory_vm_id_seq'::regclass);
ALTER TABLE ONLY public.discovery_nutanix_inventory_vm
    ADD CONSTRAINT discovery_nutanix_inventory_vm_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.discovery_nutanix_inventory_vm
    ADD CONSTRAINT nut_vm_uid UNIQUE (component_moid);
ALTER TABLE ONLY public.discovery_nutanix_inventory_vm
    ADD CONSTRAINT nut_vm_unq UNIQUE (component_moid);
ALTER TABLE ONLY public.discovery_nutanix_inventory_vm
    ADD CONSTRAINT nutanix_vm_unique_moid UNIQUE (component_moid);
ALTER TABLE ONLY public.discovery_nutanix_inventory_vm
    ADD CONSTRAINT uniq_vm_identity UNIQUE (component_moid, nutanix_uuid);
ALTER TABLE ONLY public.discovery_nutanix_inventory_vm
    ADD CONSTRAINT uniq_vm_parent_moid UNIQUE (parent_component_moid, component_moid);
\unrestrict PipGtC9LR3ER1ZdovUWHe4jOvHeot8QC40sUmhipLqEhd1p8RyDe7CfI7WJuHMQ
