\restrict aRiwiyFn5KOh3wfJwbUkeL6MZiapJQet69htHwO71aTSVYnghb6OVCFgXnbaFST
CREATE TABLE public.raw_vmware_host_perf_raw (
    data_type text NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    vcenter_uuid text NOT NULL,
    host_moid text NOT NULL,
    counter_id integer NOT NULL,
    counter_name text,
    counter_group text,
    counter_name_short text,
    counter_rollup_type text,
    counter_stats_type text,
    counter_unit_key text,
    counter_unit_label text,
    instance text NOT NULL,
    sample_timestamp timestamp with time zone NOT NULL,
    value bigint,
    interval_id integer
);
CREATE INDEX raw_vmware_host_perf_raw_collection_timestamp_idx ON public.raw_vmware_host_perf_raw USING btree (collection_timestamp DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_vmware_host_perf_raw FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict aRiwiyFn5KOh3wfJwbUkeL6MZiapJQet69htHwO71aTSVYnghb6OVCFgXnbaFST
