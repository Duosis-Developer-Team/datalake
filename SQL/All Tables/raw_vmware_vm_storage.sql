\restrict nl4lBhXiDuIppnOCg23iyIpoEAiI7xMDZB5yJzheLRRJZq8oq30dY6T48C63ch3
CREATE TABLE public.raw_vmware_vm_storage (
    data_type text NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    vcenter_uuid text NOT NULL,
    vm_moid text NOT NULL,
    datastore_moid text NOT NULL,
    datastore_name text,
    datastore_url text,
    datastore_capacity bigint,
    datastore_free_space bigint,
    datastore_type text,
    datastore_accessible boolean,
    datastore_multiple_host_access boolean,
    committed bigint,
    uncommitted bigint,
    unshared bigint
);
CREATE INDEX raw_vmware_vm_storage_collection_timestamp_idx ON public.raw_vmware_vm_storage USING btree (collection_timestamp DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_vmware_vm_storage FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict nl4lBhXiDuIppnOCg23iyIpoEAiI7xMDZB5yJzheLRRJZq8oq30dY6T48C63ch3
