\restrict vQBtek4r0Owmz2uUulvMJcYQTzyIo45Gd5LUpFzRNIJUqcRImaFFRzkkfq4IqRb
CREATE TABLE public.discovery_vmware_inventory_vcenter (
    id character varying NOT NULL,
    first_observed timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_observed timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    vcenter_uuid uuid,
    vcenter_ip character varying(255) NOT NULL,
    vcenter_hostname text,
    data_type character varying(50) NOT NULL,
    component_moid character varying(255) NOT NULL,
    name text NOT NULL,
    status character varying(20) NOT NULL,
    status_description text,
    version character varying(50)
);
CREATE SEQUENCE public.vmware_inventory_vcenter_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.vmware_inventory_vcenter_id_seq OWNED BY public.discovery_vmware_inventory_vcenter.id;
ALTER TABLE ONLY public.discovery_vmware_inventory_vcenter ALTER COLUMN id SET DEFAULT nextval('public.vmware_inventory_vcenter_id_seq'::regclass);
ALTER TABLE ONLY public.discovery_vmware_inventory_vcenter
    ADD CONSTRAINT uq_vcenter_comp_moid UNIQUE (component_moid);
ALTER TABLE ONLY public.discovery_vmware_inventory_vcenter
    ADD CONSTRAINT vmware_inventory_vcenter_pkey PRIMARY KEY (id);
CREATE INDEX idx_vcenter_last_observed ON public.discovery_vmware_inventory_vcenter USING btree (last_observed DESC);
CREATE TRIGGER update_vcenter_last_observed BEFORE UPDATE ON public.discovery_vmware_inventory_vcenter FOR EACH ROW EXECUTE FUNCTION public.update_last_observed_column();
\unrestrict vQBtek4r0Owmz2uUulvMJcYQTzyIo45Gd5LUpFzRNIJUqcRImaFFRzkkfq4IqRb
