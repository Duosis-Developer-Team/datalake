\restrict Hpy8efrGj5Zlskr6nA9olihsKOxm7QGKCFUNnVbMOmyEh5kwlguSRnDNYVQ269i
CREATE TABLE public.raw_veeam_proxy_datastores (
    id integer NOT NULL,
    proxy_id text NOT NULL,
    datastore_id text NOT NULL,
    source_ip text NOT NULL,
    collection_time timestamp with time zone NOT NULL
);
ALTER TABLE ONLY public.raw_veeam_proxy_datastores
    ADD CONSTRAINT veeam_proxy_datastores_pkey PRIMARY KEY (collection_time, id);
CREATE INDEX raw_veeam_proxy_datastores_collection_time_idx ON public.raw_veeam_proxy_datastores USING btree (collection_time DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_veeam_proxy_datastores FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict Hpy8efrGj5Zlskr6nA9olihsKOxm7QGKCFUNnVbMOmyEh5kwlguSRnDNYVQ269i
