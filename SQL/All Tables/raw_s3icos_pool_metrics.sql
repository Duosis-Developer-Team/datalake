\restrict e6ybjh39Kt7eOkohqlgfYHkriY4We6ZsllPx0vtse1ld1ydXVTezPa6tMGpfCzi
CREATE TABLE public.raw_s3icos_pool_metrics (
    id integer NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    pool_id integer NOT NULL,
    pool_name character varying(255),
    total_capacity_bytes bigint,
    used_capacity_bytes bigint,
    analytics_enabled boolean,
    usable_size_bytes bigint,
    used_physical_size_bytes bigint,
    used_logical_size_bytes bigint,
    estimate_usable_used_logical_size_bytes bigint,
    estimate_usable_total_logical_size_bytes bigint
);
CREATE SEQUENCE public.s3icos_pool_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.s3icos_pool_metrics_id_seq OWNED BY public.raw_s3icos_pool_metrics.id;
ALTER TABLE ONLY public.raw_s3icos_pool_metrics ALTER COLUMN id SET DEFAULT nextval('public.s3icos_pool_metrics_id_seq'::regclass);
ALTER TABLE ONLY public.raw_s3icos_pool_metrics
    ADD CONSTRAINT s3icos_pool_metrics_pkey PRIMARY KEY (id);
CREATE INDEX idx_pool_metrics_pool_id_timestamp ON public.raw_s3icos_pool_metrics USING btree (pool_id, collection_timestamp DESC);
\unrestrict e6ybjh39Kt7eOkohqlgfYHkriY4We6ZsllPx0vtse1ld1ydXVTezPa6tMGpfCzi
