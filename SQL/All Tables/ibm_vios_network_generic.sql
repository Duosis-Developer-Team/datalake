\restrict Y3UkaJCCyrmaowDuJrCyv9kLft0NZpUME0DENdMldw93uRUlJcjf0mp64wJSy0V
CREATE TABLE public.ibm_vios_network_generic (
    servername character varying(255),
    viosname character varying(255),
    id character varying(255),
    location character varying(255),
    type character varying(255),
    physicallocation character varying(255),
    receivedpackets double precision,
    sentpackets double precision,
    droppedpackets double precision,
    sentbytes double precision,
    receivedbytes double precision,
    transferredbytes double precision,
    "time" timestamp with time zone NOT NULL
);
ALTER TABLE ONLY public.ibm_vios_network_generic
    ADD CONSTRAINT ibm_vios_network_generic_viosname_id_time_key UNIQUE (viosname, id, "time");
CREATE INDEX ibm_vios_network_generic_time_idx ON public.ibm_vios_network_generic USING btree ("time" DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.ibm_vios_network_generic FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict Y3UkaJCCyrmaowDuJrCyv9kLft0NZpUME0DENdMldw93uRUlJcjf0mp64wJSy0V
