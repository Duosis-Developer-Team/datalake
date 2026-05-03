\restrict DOW8Epe3FmvIEwq3vdBSFjF1MuKdbcAhvr4QpQPxf0KdWZinYYzXyQoaoVOnzQl
CREATE TABLE public.ibm_server_power (
    server_name character varying(255),
    atom_id character varying(255),
    "timestamp" timestamp without time zone NOT NULL,
    power_watts integer,
    mb0 integer,
    mb1 integer,
    mb2 integer,
    mb3 integer,
    cpu0 integer,
    cpu1 integer,
    cpu2 integer,
    cpu3 integer,
    cpu4 integer,
    cpu5 integer,
    cpu6 integer,
    cpu7 integer,
    inlet_temp integer
);
ALTER TABLE ONLY public.ibm_server_power
    ADD CONSTRAINT ibm_server_power_server_name_timestamp_key UNIQUE (server_name, "timestamp");
CREATE INDEX ibm_server_power_server_name_idx ON public.ibm_server_power USING btree (server_name);
CREATE INDEX ibm_server_power_timestamp_idx ON public.ibm_server_power USING btree ("timestamp");
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.ibm_server_power FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict DOW8Epe3FmvIEwq3vdBSFjF1MuKdbcAhvr4QpQPxf0KdWZinYYzXyQoaoVOnzQl
