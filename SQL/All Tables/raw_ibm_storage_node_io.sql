\restrict 9Fq9SriZfhzvFFi1rjPNOeONAwO9GQyPVG3lIpGXJD7QHsCGmgbggkgvleQKJ9o
CREATE TABLE public.raw_ibm_storage_node_io (
    node_id text,
    "timestamp" timestamp without time zone,
    cluster text,
    node_id_hex text,
    cluster_id text,
    ro bigint,
    wo bigint,
    rb bigint,
    lrb bigint,
    wb bigint,
    lwb bigint,
    re bigint,
    we bigint,
    rq bigint,
    wq bigint,
    storage_ip character varying(255)
);
\unrestrict 9Fq9SriZfhzvFFi1rjPNOeONAwO9GQyPVG3lIpGXJD7QHsCGmgbggkgvleQKJ9o
