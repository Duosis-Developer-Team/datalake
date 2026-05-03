\restrict P3HnwqFvpY1YkejLG46l3QPOa4heTJzg8mAI1KtiYDO5mnvf7zpTQI4xHPycbGX
CREATE TABLE public.raw_vmware_vm_config (
    data_type text NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    vcenter_uuid text NOT NULL,
    datacenter_moid text,
    cluster_moid text,
    host_moid text,
    vm_moid text NOT NULL,
    name text,
    template boolean,
    vm_path_name text,
    memory_size_mb bigint,
    cpu_reservation bigint,
    memory_reservation bigint,
    num_cpu integer,
    num_ethernet_cards integer,
    num_virtual_disks integer,
    uuid text,
    instance_uuid text,
    guest_id text,
    guest_full_name text,
    annotation text,
    change_version text,
    modified timestamp with time zone,
    change_tracking_enabled boolean,
    firmware text,
    max_mks_connections integer,
    guest_auto_lock_enabled boolean,
    managed_by_extension_key text,
    managed_by_type text,
    version text,
    folder_path text
);
CREATE INDEX raw_vmware_vm_config_collection_timestamp_idx ON public.raw_vmware_vm_config USING btree (collection_timestamp DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_vmware_vm_config FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict P3HnwqFvpY1YkejLG46l3QPOa4heTJzg8mAI1KtiYDO5mnvf7zpTQI4xHPycbGX
