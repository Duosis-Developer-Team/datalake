\restrict Eq0tuOZ2ZdHJ7m1Dqxr3WG2TJ8ISdhXNeFedh2Ex39TJw2J07oNPbygiFeegRgQ
CREATE TABLE public.raw_veeam_proxies (
    id text NOT NULL,
    name text,
    description text,
    type text,
    server_host_id text,
    server_transport_mode text,
    server_failover_to_network boolean,
    server_host_to_proxy_encryption boolean,
    server_max_task_count integer,
    server_connected_datastores_auto_select_enabled boolean,
    source_ip text NOT NULL,
    collection_time timestamp with time zone NOT NULL
);
ALTER TABLE ONLY public.raw_veeam_proxies
    ADD CONSTRAINT veeam_proxies_pkey PRIMARY KEY (id, source_ip, collection_time);
CREATE INDEX raw_veeam_proxies_collection_time_idx ON public.raw_veeam_proxies USING btree (collection_time DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_veeam_proxies FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict Eq0tuOZ2ZdHJ7m1Dqxr3WG2TJ8ISdhXNeFedh2Ex39TJw2J07oNPbygiFeegRgQ
