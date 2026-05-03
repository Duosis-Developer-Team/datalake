\restrict QDb5Gk371C338zzEQITrn5ir2Qt0juojJDstoIAo25VyHhOJCPVodZ2KDoEV0mo
CREATE TABLE public.discovery_vmware_inventory_datacenter (
    id character varying NOT NULL,
    first_observed timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_observed timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    vcenter_uuid uuid NOT NULL,
    data_type character varying(50) NOT NULL,
    component_moid character varying(255) NOT NULL,
    parent_component_moid character varying(255) NOT NULL,
    component_uuid character varying(255),
    name text NOT NULL,
    status character varying(20) NOT NULL,
    status_description text
);
CREATE SEQUENCE public.vmware_inventory_datacenter_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.vmware_inventory_datacenter_id_seq OWNED BY public.discovery_vmware_inventory_datacenter.id;
ALTER TABLE ONLY public.discovery_vmware_inventory_datacenter ALTER COLUMN id SET DEFAULT nextval('public.vmware_inventory_datacenter_id_seq'::regclass);
ALTER TABLE ONLY public.discovery_vmware_inventory_datacenter
    ADD CONSTRAINT uq_datacenter_hier UNIQUE (parent_component_moid, component_moid);
ALTER TABLE ONLY public.discovery_vmware_inventory_datacenter
    ADD CONSTRAINT vmware_inventory_datacenter_pkey PRIMARY KEY (id);
CREATE INDEX idx_datacenter_last_observed ON public.discovery_vmware_inventory_datacenter USING btree (last_observed DESC);
CREATE INDEX idx_datacenter_parent_moid ON public.discovery_vmware_inventory_datacenter USING btree (parent_component_moid);
CREATE TRIGGER update_datacenter_last_observed BEFORE UPDATE ON public.discovery_vmware_inventory_datacenter FOR EACH ROW EXECUTE FUNCTION public.update_last_observed_column();
\unrestrict QDb5Gk371C338zzEQITrn5ir2Qt0juojJDstoIAo25VyHhOJCPVodZ2KDoEV0mo
