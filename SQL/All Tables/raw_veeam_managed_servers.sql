\restrict CcQd987YAAgtRnZWUK4V3pjzT2RtHQbRpmecs2hTGdjRZRp71gVjRDDnaJDzT00
CREATE TABLE public.raw_veeam_managed_servers (
    id text NOT NULL,
    name text,
    description text,
    type text,
    status text,
    port integer,
    credentials_id text,
    vi_host_type text,
    network_port_range_start integer,
    network_port_range_end integer,
    network_server_side boolean,
    source_ip text NOT NULL,
    collection_time timestamp with time zone NOT NULL
);
ALTER TABLE ONLY public.raw_veeam_managed_servers
    ADD CONSTRAINT veeam_managed_servers_pkey PRIMARY KEY (id, source_ip, collection_time);
CREATE INDEX raw_veeam_managed_servers_collection_time_idx ON public.raw_veeam_managed_servers USING btree (collection_time DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_veeam_managed_servers FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict CcQd987YAAgtRnZWUK4V3pjzT2RtHQbRpmecs2hTGdjRZRp71gVjRDDnaJDzT00
