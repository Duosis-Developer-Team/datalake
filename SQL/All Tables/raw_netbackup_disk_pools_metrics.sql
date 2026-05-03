\restrict rcjEfpjImab5nCe3gBxAJj7yysh75Ps60WeQ6x45evLfyMgXjRneS8GxHPcnBML
CREATE TABLE public.raw_netbackup_disk_pools_metrics (
    data_type character varying(50) NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    netbackup_host character varying(50) DEFAULT ''::character varying NOT NULL,
    id character varying(255) NOT NULL,
    type character varying(50),
    name character varying(255),
    stype character varying(100),
    storagecategory character varying(100),
    diskvolumes_name character varying(255),
    diskvolumes_id character varying(255),
    diskvolumes_diskmediaid character varying(255),
    diskvolumes_state character varying(100),
    diskvolumes_rawsizebytes bigint,
    diskvolumes_freesizebytes bigint,
    diskvolumes_isreplicationsource boolean,
    diskvolumes_isreplicationtarget boolean,
    diskvolumes_wormindelibleminimuminterval integer,
    diskvolumes_wormindeliblemaximuminterval integer,
    highwatermark integer,
    lowwatermark integer,
    max_limitiostreams integer,
    diskpoolstate character varying(100),
    rawsizebytes bigint,
    usablesizebytes bigint,
    availablespacebytes bigint,
    usedcapacitybytes bigint,
    wormcapable boolean,
    readonly boolean,
    mediaserverscount integer
);
ALTER TABLE ONLY public.raw_netbackup_disk_pools_metrics
    ADD CONSTRAINT raw_netbackup_disk_pools_metrics_pkey PRIMARY KEY (id, collection_timestamp);
CREATE INDEX raw_netbackup_disk_pools_metrics_collection_timestamp_idx ON public.raw_netbackup_disk_pools_metrics USING btree (collection_timestamp DESC);
CREATE INDEX raw_netbackup_disk_pools_metrics_stype_idx ON public.raw_netbackup_disk_pools_metrics USING btree (stype);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_netbackup_disk_pools_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict rcjEfpjImab5nCe3gBxAJj7yysh75Ps60WeQ6x45evLfyMgXjRneS8GxHPcnBML
