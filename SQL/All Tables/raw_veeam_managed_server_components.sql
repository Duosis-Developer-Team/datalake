\restrict yYJzdxhtOmxOynd9VkKJROpLZbQBoQhRuLcL1Db5as18YLkZc7zn2UJBPBPbION
CREATE TABLE public.raw_veeam_managed_server_components (
    id integer NOT NULL,
    managed_server_id text NOT NULL,
    component_name text,
    port integer,
    source_ip text NOT NULL,
    collection_time timestamp with time zone NOT NULL
);
ALTER TABLE ONLY public.raw_veeam_managed_server_components
    ADD CONSTRAINT veeam_managed_server_components_pkey PRIMARY KEY (id, collection_time);
CREATE INDEX raw_veeam_managed_server_components_collection_time_idx ON public.raw_veeam_managed_server_components USING btree (collection_time DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_veeam_managed_server_components FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict yYJzdxhtOmxOynd9VkKJROpLZbQBoQhRuLcL1Db5as18YLkZc7zn2UJBPBPbION
