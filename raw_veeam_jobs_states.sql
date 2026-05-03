\restrict o7mdRnZL3FHQRqovadDsZdsBUeaXosEILwisjeX2Nz1gDofcHcNcOHfO5Hv2K6j
CREATE TABLE public.raw_veeam_jobs_states (
    id text NOT NULL,
    name text,
    description text,
    type text,
    status text,
    last_result text,
    last_run timestamp with time zone NOT NULL,
    next_run timestamp with time zone,
    workload text,
    objects_count integer,
    repository_id text,
    repository_name text,
    session_id text NOT NULL,
    source_ip text NOT NULL,
    collection_time timestamp with time zone NOT NULL
);
ALTER TABLE ONLY public.raw_veeam_jobs_states
    ADD CONSTRAINT veeam_jobs_states_pkey UNIQUE (id, last_run, source_ip, session_id, collection_time);
CREATE INDEX raw_veeam_jobs_states_collection_time_idx ON public.raw_veeam_jobs_states USING btree (collection_time DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_veeam_jobs_states FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict o7mdRnZL3FHQRqovadDsZdsBUeaXosEILwisjeX2Nz1gDofcHcNcOHfO5Hv2K6j
