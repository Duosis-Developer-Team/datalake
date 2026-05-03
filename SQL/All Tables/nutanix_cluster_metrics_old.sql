\restrict Om9UsogZcVoep8jVwifiC5IIQHy1c4kPLcbw2tW65anG3TR0PnHhbIku8JlQ7gP
CREATE TABLE public.nutanix_cluster_metrics_old (
    datacenter_name character varying(255) NOT NULL,
    cluster_name character varying(255) NOT NULL,
    cluster_uuid character varying(255) NOT NULL,
    num_nodes integer NOT NULL,
    total_memory_capacity bigint NOT NULL,
    total_cpu_capacity bigint NOT NULL,
    total_vms integer NOT NULL,
    network_transmitted_avg bigint,
    network_received_avg bigint,
    storage_capacity bigint,
    storage_usage bigint,
    memory_usage_min bigint,
    memory_usage_max bigint,
    memory_usage_avg bigint,
    cpu_usage_min bigint,
    cpu_usage_max bigint,
    cpu_usage_avg bigint,
    read_io_bandwidth_min bigint,
    read_io_bandwidth_max bigint,
    read_io_bandwidth_avg bigint,
    write_io_bandwidth_min bigint,
    write_io_bandwidth_max bigint,
    write_io_bandwidth_avg bigint,
    collection_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE ONLY public.nutanix_cluster_metrics_old
    ADD CONSTRAINT unique_nutanix_cluster_metric_entry_old UNIQUE (cluster_uuid, collection_time);
\unrestrict Om9UsogZcVoep8jVwifiC5IIQHy1c4kPLcbw2tW65anG3TR0PnHhbIku8JlQ7gP
