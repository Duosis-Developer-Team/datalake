\restrict DqWeKQ8NWWKTdNgDlr4MQpzsMhXV2QlAJDH4BJYc41eyLPeCpLhM8HGXL7isFmo
CREATE TABLE public.discovery_netbox_platform (
    id bigint NOT NULL,
    data_type character varying(50),
    url text,
    display_url text,
    display text,
    name text,
    slug text,
    parent_id bigint,
    parent_name text,
    manufacturer_id bigint,
    manufacturer_name text,
    config_template_id bigint,
    description text,
    comments text,
    custom_fields jsonb,
    tags jsonb,
    cf_datalake character varying(255),
    cf_dc character varying(255),
    cf_ip_addresses character varying(255),
    cf_izlenmeli character varying(255),
    cf_port character varying(255),
    cf_site character varying(255),
    cf_url character varying(255),
    cf_user_type character varying(255),
    cf_zabbix character varying(255),
    created character varying(255),
    last_updated character varying(255),
    device_count bigint,
    virtualmachine_count bigint,
    _depth bigint,
    collection_time character varying(255)
);
ALTER TABLE ONLY public.discovery_netbox_platform
    ADD CONSTRAINT discovery_netbox_platform_pkey PRIMARY KEY (id);
\unrestrict DqWeKQ8NWWKTdNgDlr4MQpzsMhXV2QlAJDH4BJYc41eyLPeCpLhM8HGXL7isFmo
