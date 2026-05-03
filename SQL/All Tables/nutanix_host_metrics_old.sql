\restrict 0r6qgGp1KA6vFfsyM06yfQVjJgQZsRnJAUoFvUNek1CF5n5KBv3FDYffVXEiZSV
CREATE TABLE public.nutanix_host_metrics_old (
    id integer NOT NULL,
    host_name character varying(255) NOT NULL,
    host_uuid character varying(255) NOT NULL,
    cluster_uuid character varying(255) NOT NULL,
    total_memory_capacity bigint NOT NULL,
    total_cpu_capacity bigint NOT NULL,
    num_cpu_cores integer NOT NULL,
    total_vms integer NOT NULL,
    network_transmitted_avg bigint,
    network_received_avg bigint,
    memory_usage_min bigint,
    memory_usage_max bigint,
    memory_usage_avg bigint,
    cpu_usage_min bigint,
    cpu_usage_max bigint,
    cpu_usage_avg bigint,
    storage_capacity bigint NOT NULL,
    storage_usage bigint NOT NULL,
    read_io_bandwidth_min bigint,
    read_io_bandwidth_max bigint,
    read_io_bandwidth_avg bigint,
    write_io_bandwidth_min bigint,
    write_io_bandwidth_max bigint,
    write_io_bandwidth_avg bigint,
    collectiontime timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    boottime bigint
);
CREATE SEQUENCE public.nutanix_host_metrics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.nutanix_host_metrics_id_seq OWNED BY public.nutanix_host_metrics_old.id;
ALTER TABLE ONLY public.nutanix_host_metrics_old ALTER COLUMN id SET DEFAULT nextval('public.nutanix_host_metrics_id_seq'::regclass);
ALTER TABLE ONLY public.nutanix_host_metrics_old
    ADD CONSTRAINT unique_nutanix_host_metric_entry_old UNIQUE (host_uuid, collectiontime);
\unrestrict 0r6qgGp1KA6vFfsyM06yfQVjJgQZsRnJAUoFvUNek1CF5n5KBv3FDYffVXEiZSV
