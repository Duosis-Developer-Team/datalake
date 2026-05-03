\restrict IKpSRJIY8JubcYxKUVWIRVGRUXpFJK2doik6YOKNUaMWpaVtcp8LcX3IZvOfxZr
CREATE TABLE public.raw_vertiv_pdu_collections (
    collection_timestamp timestamp with time zone NOT NULL,
    collection_timestamp_unix bigint NOT NULL,
    collection_date date NOT NULL,
    collection_time time without time zone NOT NULL,
    pdu_name character varying(255) NOT NULL,
    building character varying(100) NOT NULL,
    room character varying(100) NOT NULL,
    unit character varying(100) NOT NULL,
    host_id character varying(50) NOT NULL,
    host_name character varying(255) NOT NULL,
    display_name character varying(255),
    ip_address inet,
    host_status character varying(10),
    status character varying(10) NOT NULL,
    source_system character varying(50) DEFAULT 'zabbix'::character varying
);
ALTER TABLE ONLY public.raw_vertiv_pdu_collections
    ADD CONSTRAINT vertiv_pdu_collections_pkey PRIMARY KEY (pdu_name, collection_timestamp);
CREATE INDEX idx_collections_building ON public.raw_vertiv_pdu_collections USING btree (building);
CREATE INDEX idx_collections_room ON public.raw_vertiv_pdu_collections USING btree (room);
CREATE INDEX idx_collections_unit ON public.raw_vertiv_pdu_collections USING btree (unit);
CREATE INDEX vertiv_pdu_collections_collection_timestamp_idx ON public.raw_vertiv_pdu_collections USING btree (collection_timestamp DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_vertiv_pdu_collections FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict IKpSRJIY8JubcYxKUVWIRVGRUXpFJK2doik6YOKNUaMWpaVtcp8LcX3IZvOfxZr
