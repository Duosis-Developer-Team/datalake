\restrict IeOgA5C1ujhR7JPWk2xekkRKrrYdt5LFvXgMkkS73yjbBf3IwWLmKlV2bL7hJhy
CREATE TABLE public.raw_ibm_storage_host_by_id (
    id integer,
    name character varying(255),
    port_count integer,
    type character varying(100),
    iogrp_count integer,
    status character varying(50),
    site_id integer,
    site_name character varying(255),
    host_cluster_id integer,
    host_cluster_name character varying(255),
    protocol character varying(50),
    status_policy character varying(100),
    status_site character varying(100),
    nodes_wwpn character varying(255),
    nodes_node_logged_in_count integer,
    nodes_state character varying(100),
    owner_id integer,
    owner_name character varying(255),
    portset_id integer,
    portset_name character varying(255),
    "timestamp" timestamp without time zone,
    storage_ip character varying(255)
);
\unrestrict IeOgA5C1ujhR7JPWk2xekkRKrrYdt5LFvXgMkkS73yjbBf3IwWLmKlV2bL7hJhy
