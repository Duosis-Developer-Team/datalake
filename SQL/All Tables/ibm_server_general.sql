\restrict qHQPj1pUHw2vWZ3zI4xmpC8swkkoiEZ9KWcVygRP9hEfjJrtIAH06zKf5eMC9bD
CREATE TABLE public.ibm_server_general (
    server_details_servername character varying(255),
    server_details_utilizedprocunits double precision,
    server_details_assignedmem double precision,
    server_details_mtm character varying(255),
    server_details_name character varying(255),
    server_details_apiversion character varying(255),
    server_details_metric character varying(255),
    server_details_frequency integer,
    server_details_nextract character varying(255),
    server_processor_servername character varying(255),
    server_processor_totalprocunits double precision,
    server_processor_utilizedprocunits double precision,
    server_processor_utilizedprocunitsdeductidle double precision,
    server_processor_availableprocunits double precision,
    server_processor_configurableprocunits double precision,
    server_memory_servername character varying(255),
    server_memory_totalmem double precision,
    server_memory_availablemem double precision,
    server_memory_configurablemem double precision,
    server_memory_assignedmemtolpars double precision,
    server_memory_virtualpersistentmem double precision,
    server_physicalprocessorpool_servername character varying(255),
    server_physicalprocessorpool_assignedprocunits double precision,
    server_physicalprocessorpool_utilizedprocunits double precision,
    server_physicalprocessorpool_availableprocunits double precision,
    server_physicalprocessorpool_configuredprocunits double precision,
    server_physicalprocessorpool_borrowedprocunits double precision,
    server_sharedprocessorpool_servername character varying(255),
    server_sharedprocessorpool_pool integer,
    server_sharedprocessorpool_poolname character varying(255),
    server_sharedprocessorpool_id integer,
    server_sharedprocessorpool_name character varying(255),
    server_sharedprocessorpool_assignedprocunits double precision,
    server_sharedprocessorpool_utilizedprocunits double precision,
    server_sharedprocessorpool_availableprocunits double precision,
    server_sharedprocessorpool_configuredprocunits double precision,
    server_sharedprocessorpool_borrowedprocunits double precision,
    servername character varying(255),
    "time" timestamp with time zone NOT NULL,
    server_details_uptime character varying(255)
);
ALTER TABLE ONLY public.ibm_server_general
    ADD CONSTRAINT ibm_server_general_servername_time_key UNIQUE (servername, "time");
CREATE INDEX ibm_server_general_time_idx ON public.ibm_server_general USING btree ("time" DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.ibm_server_general FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict qHQPj1pUHw2vWZ3zI4xmpC8swkkoiEZ9KWcVygRP9hEfjJrtIAH06zKf5eMC9bD
