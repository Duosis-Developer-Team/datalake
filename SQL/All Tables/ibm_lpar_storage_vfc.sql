\restrict 6Q88444tDe5POmZHlFp9NwRYHEUZPJgICDcT68HTB1usTedI56nMVKtbL6kdedw
CREATE TABLE public.ibm_lpar_storage_vfc (
    servername character varying(255),
    lparname character varying(255),
    location character varying(255),
    viosid integer,
    id character varying(255),
    wwpn character varying(255),
    wwpn2 character varying(255),
    physicallocation character varying(255),
    physicalportwwpn double precision,
    numofreads double precision,
    numofwrites double precision,
    readbytes double precision,
    writebytes double precision,
    runningspeed double precision,
    "time" timestamp with time zone NOT NULL
);
ALTER TABLE ONLY public.ibm_lpar_storage_vfc
    ADD CONSTRAINT ibm_lpar_storage_vfc_lparname_wwpn_wwpn2_time_key UNIQUE (lparname, wwpn, wwpn2, "time");
CREATE INDEX ibm_lpar_storage_vfc_lparname_time_idx ON public.ibm_lpar_storage_vfc USING btree (lparname, "time" DESC);
CREATE INDEX ibm_lpar_storage_vfc_time_idx ON public.ibm_lpar_storage_vfc USING btree ("time" DESC);
CREATE INDEX ibm_lpar_storage_vfc_wwpn2_idx ON public.ibm_lpar_storage_vfc USING btree (wwpn2);
CREATE INDEX ibm_lpar_storage_vfc_wwpn_idx ON public.ibm_lpar_storage_vfc USING btree (wwpn);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.ibm_lpar_storage_vfc FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict 6Q88444tDe5POmZHlFp9NwRYHEUZPJgICDcT68HTB1usTedI56nMVKtbL6kdedw
