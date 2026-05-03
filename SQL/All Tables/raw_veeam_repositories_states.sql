\restrict rkOfBQVrzcGby5UM1xIjKWEgWI6xF4iyqWEosDMBGG8fNFp0Gt3Ph3G7kUf3hhM
CREATE TABLE public.raw_veeam_repositories_states (
    id text NOT NULL,
    name text,
    description text,
    type text,
    host_id text,
    host_name text,
    path text,
    capacity_gb numeric,
    free_gb numeric,
    used_space_gb numeric,
    is_online boolean,
    source_ip text NOT NULL,
    collection_time timestamp with time zone NOT NULL
);
CREATE INDEX raw_veeam_repositories_states_collection_time_idx ON public.raw_veeam_repositories_states USING btree (collection_time DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_veeam_repositories_states FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict rkOfBQVrzcGby5UM1xIjKWEgWI6xF4iyqWEosDMBGG8fNFp0Gt3Ph3G7kUf3hhM
