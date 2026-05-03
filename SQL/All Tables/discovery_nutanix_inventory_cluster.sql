\restrict O9ZO8ALRHhgSOQLMENFcTu6MJ486rpMw0LrqhWYI2O9bLnzQyLbaryiIYg1ijxA
CREATE TABLE public.discovery_nutanix_inventory_cluster (
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
    status_description text
);
CREATE SEQUENCE public.discovery_nutanix_inventory_cluster_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.discovery_nutanix_inventory_cluster_id_seq OWNED BY public.discovery_nutanix_inventory_cluster.id;
ALTER TABLE ONLY public.discovery_nutanix_inventory_cluster ALTER COLUMN id SET DEFAULT nextval('public.discovery_nutanix_inventory_cluster_id_seq'::regclass);
ALTER TABLE ONLY public.discovery_nutanix_inventory_cluster
    ADD CONSTRAINT discovery_nutanix_inventory_cluster_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.discovery_nutanix_inventory_cluster
    ADD CONSTRAINT uniq_cluster_parent_moid UNIQUE (parent_component_moid, component_moid);
\unrestrict O9ZO8ALRHhgSOQLMENFcTu6MJ486rpMw0LrqhWYI2O9bLnzQyLbaryiIYg1ijxA
