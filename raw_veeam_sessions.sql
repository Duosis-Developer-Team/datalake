\restrict LGfvd2JYBWstxovBldu2kgFTZVAbkX8ZT1wTh69Zqebhx6Wkaqcxf7fi90EYvB2
CREATE TABLE public.raw_veeam_sessions (
    id text NOT NULL,
    name text,
    job_id text NOT NULL,
    session_type text,
    state text,
    creation_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone,
    result_result text,
    result_message text,
    result_is_canceled boolean,
    progress_percent integer,
    usn bigint,
    platform_id text,
    platform_name text,
    resource_id text,
    resource_reference text,
    parent_session_id text,
    source_ip text NOT NULL,
    collection_time timestamp with time zone NOT NULL
);
ALTER TABLE ONLY public.raw_veeam_sessions
    ADD CONSTRAINT veeam_sessions_pkey PRIMARY KEY (source_ip, id, job_id, creation_time, collection_time);
CREATE INDEX raw_veeam_sessions_collection_time_idx ON public.raw_veeam_sessions USING btree (collection_time DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_veeam_sessions FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict LGfvd2JYBWstxovBldu2kgFTZVAbkX8ZT1wTh69Zqebhx6Wkaqcxf7fi90EYvB2
