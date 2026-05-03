\restrict o4SHE6JOd7vm6LsZSozn8j5zkK87gW0Visa0qvxEIV5C7FORjc183AzeOoHaCLX
CREATE TABLE public.raw_vmware_datacenter_config (
    data_type text NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    vcenter_uuid text NOT NULL,
    datacenter_moid text NOT NULL,
    name text,
    overall_status text
);
COMMENT ON TABLE public.raw_vmware_datacenter_config IS 'VMware datacenter configuration - minimal config info';
COMMENT ON COLUMN public.raw_vmware_datacenter_config.data_type IS 'Always: vmware_datacenter_config';
COMMENT ON COLUMN public.raw_vmware_datacenter_config.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN public.raw_vmware_datacenter_config.overall_status IS 'Overall status (green/yellow/red)';
ALTER TABLE ONLY public.raw_vmware_datacenter_config
    ADD CONSTRAINT raw_vmware_datacenter_config_pkey PRIMARY KEY (vcenter_uuid, datacenter_moid, collection_timestamp);
CREATE INDEX idx_raw_vmware_datacenter_config_data_type ON public.raw_vmware_datacenter_config USING btree (data_type);
CREATE INDEX idx_raw_vmware_datacenter_config_name ON public.raw_vmware_datacenter_config USING btree (name);
CREATE INDEX idx_raw_vmware_datacenter_config_timestamp ON public.raw_vmware_datacenter_config USING btree (collection_timestamp DESC);
CREATE INDEX idx_raw_vmware_datacenter_config_vcenter ON public.raw_vmware_datacenter_config USING btree (vcenter_uuid);
\unrestrict o4SHE6JOd7vm6LsZSozn8j5zkK87gW0Visa0qvxEIV5C7FORjc183AzeOoHaCLX
