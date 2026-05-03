\restrict M583ULFhQlqLTK3US6ZLNrfwpZdIGVwIfFIyhar3q3SN3Tw9Err4m1kzbDULm4V
CREATE TABLE public.discovery_vmware_inventory_vm (
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
    status_description text,
    guest_os text,
    tools_status character varying(50)
);
CREATE SEQUENCE public.vmware_inventory_vm_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.vmware_inventory_vm_id_seq OWNED BY public.discovery_vmware_inventory_vm.id;
ALTER TABLE ONLY public.discovery_vmware_inventory_vm ALTER COLUMN id SET DEFAULT nextval('public.vmware_inventory_vm_id_seq'::regclass);
ALTER TABLE ONLY public.discovery_vmware_inventory_vm
    ADD CONSTRAINT uq_vm_unique UNIQUE (vcenter_uuid, component_moid);
ALTER TABLE ONLY public.discovery_vmware_inventory_vm
    ADD CONSTRAINT vmware_inventory_vm_pkey PRIMARY KEY (id);
CREATE INDEX idx_vm_component_uuid ON public.discovery_vmware_inventory_vm USING btree (component_uuid);
CREATE INDEX idx_vm_last_observed ON public.discovery_vmware_inventory_vm USING btree (last_observed DESC);
CREATE INDEX idx_vm_parent_moid ON public.discovery_vmware_inventory_vm USING btree (parent_component_moid);
CREATE TRIGGER update_vm_last_observed BEFORE UPDATE ON public.discovery_vmware_inventory_vm FOR EACH ROW EXECUTE FUNCTION public.update_last_observed_column();
\unrestrict M583ULFhQlqLTK3US6ZLNrfwpZdIGVwIfFIyhar3q3SN3Tw9Err4m1kzbDULm4V
