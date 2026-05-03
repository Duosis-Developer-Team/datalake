\restrict yoygbErg0rzNclrgE1333BN4f77lg1l17x39uhVREdP5g6NccLWIGqldyAuYNUT
CREATE TABLE public.raw_zerto_license_metrics (
    data_type character varying(50) NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    zerto_host character varying(50) DEFAULT ''::character varying NOT NULL,
    id character varying(255) NOT NULL,
    name character varying(255),
    expirationdate character varying(255),
    license_key character varying(255),
    license_type character varying(100),
    is_valid boolean,
    max_vms integer,
    total_vms_count integer,
    sites_usage jsonb,
    days_until_expiry integer
);
ALTER TABLE ONLY public.raw_zerto_license_metrics
    ADD CONSTRAINT zerto_license_metrics_pkey PRIMARY KEY (id, collection_timestamp);
\unrestrict yoygbErg0rzNclrgE1333BN4f77lg1l17x39uhVREdP5g6NccLWIGqldyAuYNUT
