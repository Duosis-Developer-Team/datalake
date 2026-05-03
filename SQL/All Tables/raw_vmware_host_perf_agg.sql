\restrict YWdUtFCtslEp96Ae5RIVAuU6r62tRSt9Hpi8aGHfYpIn9xFy2ilTeM6J9v1HzcE
CREATE TABLE public.raw_vmware_host_perf_agg (
    data_type text NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    vcenter_uuid text NOT NULL,
    host_moid text NOT NULL,
    window_start timestamp with time zone NOT NULL,
    window_end timestamp with time zone NOT NULL,
    window_duration_seconds integer,
    sample_count integer,
    counter_id integer NOT NULL,
    counter_name text,
    counter_group text,
    counter_rollup_type text,
    counter_unit_key text,
    instance text NOT NULL,
    value_avg double precision,
    value_min bigint,
    value_max bigint,
    value_stddev double precision,
    value_first bigint,
    value_last bigint
);
CREATE INDEX raw_vmware_host_perf_agg_collection_timestamp_idx ON public.raw_vmware_host_perf_agg USING btree (collection_timestamp DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_vmware_host_perf_agg FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict YWdUtFCtslEp96Ae5RIVAuU6r62tRSt9Hpi8aGHfYpIn9xFy2ilTeM6J9v1HzcE
