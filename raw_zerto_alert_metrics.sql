\restrict QkQeCKXwtdKa0HEMFfVZvsdTMvKllYxxBww04YVhypJvwkoeH47qWNPk2KfBCAH
CREATE TABLE public.raw_zerto_alert_metrics (
    data_type character varying(50) NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    zerto_host character varying(50) DEFAULT ''::character varying NOT NULL,
    id character varying(255) NOT NULL,
    alert_identifier character varying(255),
    title character varying(500),
    description text,
    severity character varying(50),
    category character varying(100),
    creation_date timestamp with time zone,
    site_identifier character varying(255),
    vpg_identifier character varying(255),
    is_acknowledged boolean,
    is_resolved boolean,
    related_entities jsonb,
    tags jsonb
);
ALTER TABLE ONLY public.raw_zerto_alert_metrics
    ADD CONSTRAINT zerto_alert_metrics_pkey PRIMARY KEY (id, collection_timestamp);
\unrestrict QkQeCKXwtdKa0HEMFfVZvsdTMvKllYxxBww04YVhypJvwkoeH47qWNPk2KfBCAH
