\restrict L9Ex4gc1eRNJQ9JZeWxwJsZrjcgK7jMgd15BHdiW2aZcU5HOle8nBmaUUapW88l
CREATE TABLE public.raw_vertiv_pdu_status_metrics (
    collection_timestamp timestamp with time zone NOT NULL,
    collection_timestamp_unix bigint NOT NULL,
    collection_date date NOT NULL,
    collection_time time without time zone NOT NULL,
    pdu_name character varying(255) NOT NULL,
    building character varying(100) NOT NULL,
    room character varying(100) NOT NULL,
    unit character varying(100) NOT NULL,
    host_id character varying(50) NOT NULL,
    host_name character varying(255) NOT NULL,
    display_name character varying(255),
    ip_address inet,
    host_status character varying(10),
    status character varying(10) NOT NULL,
    source_system character varying(50) DEFAULT 'zabbix'::character varying,
    item_id character varying(50),
    item_name character varying(500),
    item_key character varying(500),
    value text,
    units character varying(50),
    value_type integer,
    last_check bigint
);
ALTER TABLE ONLY public.raw_vertiv_pdu_status_metrics
    ADD CONSTRAINT vertiv_pdu_status_metrics_pkey PRIMARY KEY (pdu_name, collection_timestamp);
\unrestrict L9Ex4gc1eRNJQ9JZeWxwJsZrjcgK7jMgd15BHdiW2aZcU5HOle8nBmaUUapW88l
