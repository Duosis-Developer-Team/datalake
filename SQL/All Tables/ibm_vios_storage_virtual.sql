\restrict 8EJpJjXFzpwyfc4s0XFwYsgzoiLfIB3uTDTkvlxLyHRnGh3peWqka0wf3GXZCYZ
CREATE TABLE public.ibm_vios_storage_virtual (
    servername character varying(255),
    viosname character varying(255),
    id character varying(255),
    location character varying(255),
    type character varying(50),
    physicallocation character varying(255),
    numofreads double precision,
    numofwrites double precision,
    readbytes double precision,
    writebytes double precision,
    "time" timestamp with time zone NOT NULL
);
ALTER TABLE ONLY public.ibm_vios_storage_virtual
    ADD CONSTRAINT ibm_vios_storage_virtual_viosname_id_time_key UNIQUE (viosname, id, "time");
CREATE INDEX ibm_vios_storage_virtual_time_idx ON public.ibm_vios_storage_virtual USING btree ("time" DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.ibm_vios_storage_virtual FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict 8EJpJjXFzpwyfc4s0XFwYsgzoiLfIB3uTDTkvlxLyHRnGh3peWqka0wf3GXZCYZ
