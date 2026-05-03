\restrict e0ohb8umeoItSkYoz4DEW7OsHPZE58r2TdO4xeYby5vmrgecUdlDPakFNHGn1mw
CREATE TABLE public.ibm_vios_storage_fc (
    servername character varying(255),
    viosname character varying(255),
    id character varying(255),
    location character varying(255),
    wwpn double precision,
    physicallocation character varying(255),
    numofports integer,
    numofreads double precision,
    numofwrites double precision,
    readbytes double precision,
    writebytes double precision,
    runningspeed double precision,
    "time" timestamp with time zone NOT NULL
);
ALTER TABLE ONLY public.ibm_vios_storage_fc
    ADD CONSTRAINT ibm_vios_storage_fc_viosname_id_wwpn_time_key UNIQUE (viosname, id, wwpn, "time");
CREATE INDEX ibm_vios_storage_fc_time_idx ON public.ibm_vios_storage_fc USING btree ("time" DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.ibm_vios_storage_fc FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict e0ohb8umeoItSkYoz4DEW7OsHPZE58r2TdO4xeYby5vmrgecUdlDPakFNHGn1mw
