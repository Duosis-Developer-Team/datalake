\restrict PYMHUMLRRAU3Y1nmc0KH0uPB0qyd3eDAbuytEeFy1TG6JxLSe6apC8DyRWp180q
CREATE TABLE public.ibm_vios_storage_physical (
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
ALTER TABLE ONLY public.ibm_vios_storage_physical
    ADD CONSTRAINT ibm_vios_storage_physical_viosname_id_time_key UNIQUE (viosname, id, "time");
CREATE INDEX ibm_vios_storage_physical_time_idx ON public.ibm_vios_storage_physical USING btree ("time" DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.ibm_vios_storage_physical FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict PYMHUMLRRAU3Y1nmc0KH0uPB0qyd3eDAbuytEeFy1TG6JxLSe6apC8DyRWp180q
