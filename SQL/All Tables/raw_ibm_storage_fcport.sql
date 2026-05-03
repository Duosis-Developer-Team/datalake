\restrict LUWi669SuM3fJhV51eP4HQoO4shRVRpzfHSEuTbleF3OAlnBDr6SQukjEXYWH3a
CREATE TABLE public.raw_ibm_storage_fcport (
    id integer,
    fc_io_port_id integer,
    port_id integer,
    type character varying(10),
    port_speed character varying(10),
    node_id integer,
    node_name character varying(50),
    wwpn character varying(50),
    nportid character varying(10),
    status character varying(50),
    attachment character varying(20),
    cluster_use character varying(20),
    adapter_location integer,
    adapter_port_id integer,
    "timestamp" timestamp without time zone,
    storage_ip character varying(255)
);
\unrestrict LUWi669SuM3fJhV51eP4HQoO4shRVRpzfHSEuTbleF3OAlnBDr6SQukjEXYWH3a
