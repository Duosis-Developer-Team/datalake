\restrict IMvINW8asiHgcCUj0cNDE2EGaHNf5pQkvdPxhF4qtguVJaafbewMQOBHbwscpg1
CREATE TABLE public.raw_vmware_cluster_config (
    data_type text NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    vcenter_uuid text NOT NULL,
    datacenter_moid text,
    cluster_moid text NOT NULL,
    name text,
    summary_num_hosts integer,
    summary_num_cpu_cores integer,
    summary_num_cpu_threads integer,
    summary_effective_cpu integer,
    summary_total_cpu integer,
    summary_num_effective_hosts integer,
    summary_total_memory bigint,
    summary_effective_memory bigint,
    summary_overall_status text,
    config_das_enabled boolean,
    config_das_vm_monitoring text,
    config_das_host_monitoring text,
    config_drs_enabled boolean,
    config_drs_default_vm_behavior text,
    config_drs_vmotion_rate integer,
    config_dpm_enabled boolean
);
COMMENT ON TABLE public.raw_vmware_cluster_config IS 'VMware cluster configuration - raw fields from cluster.configuration and cluster.summary';
COMMENT ON COLUMN public.raw_vmware_cluster_config.data_type IS 'Always: vmware_cluster_config';
COMMENT ON COLUMN public.raw_vmware_cluster_config.collection_timestamp IS 'Timestamp when script collected this data';
COMMENT ON COLUMN public.raw_vmware_cluster_config.summary_total_cpu IS 'Total CPU in MHz (AS-IS from VMware API)';
COMMENT ON COLUMN public.raw_vmware_cluster_config.summary_total_memory IS 'Total memory in bytes (AS-IS from VMware API)';
COMMENT ON COLUMN public.raw_vmware_cluster_config.config_das_enabled IS 'HA (High Availability) enabled status';
COMMENT ON COLUMN public.raw_vmware_cluster_config.config_drs_enabled IS 'DRS (Distributed Resource Scheduler) enabled status';
ALTER TABLE ONLY public.raw_vmware_cluster_config
    ADD CONSTRAINT raw_vmware_cluster_config_pkey PRIMARY KEY (vcenter_uuid, cluster_moid, collection_timestamp);
CREATE INDEX idx_raw_vmware_cluster_config_data_type ON public.raw_vmware_cluster_config USING btree (data_type);
CREATE INDEX idx_raw_vmware_cluster_config_datacenter ON public.raw_vmware_cluster_config USING btree (datacenter_moid);
CREATE INDEX idx_raw_vmware_cluster_config_name ON public.raw_vmware_cluster_config USING btree (name);
CREATE INDEX idx_raw_vmware_cluster_config_timestamp ON public.raw_vmware_cluster_config USING btree (collection_timestamp DESC);
CREATE INDEX idx_raw_vmware_cluster_config_vcenter ON public.raw_vmware_cluster_config USING btree (vcenter_uuid);
\unrestrict IMvINW8asiHgcCUj0cNDE2EGaHNf5pQkvdPxhF4qtguVJaafbewMQOBHbwscpg1
