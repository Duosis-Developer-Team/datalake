\restrict OqEhRq4PSffGn0n3ABP5gyEGRBveUqz3SkILXEW9kXFm6FVjBeMwEb3X989kIhT
CREATE TABLE public.raw_s3icos_vault_metrics (
    id integer NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    vault_id integer NOT NULL,
    vault_name character varying(255),
    allotted_size_bytes bigint,
    usable_size_bytes bigint,
    used_physical_size_bytes bigint,
    used_logical_size_bytes bigint,
    object_count_estimate bigint,
    allotment_usage bigint,
    estimate_usable_used_logical_size_bytes bigint,
    estimate_usable_total_logical_size_bytes bigint
);
CREATE SEQUENCE public.s3icos_vault_metrics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.s3icos_vault_metrics_id_seq OWNED BY public.raw_s3icos_vault_metrics.id;
ALTER TABLE ONLY public.raw_s3icos_vault_metrics ALTER COLUMN id SET DEFAULT nextval('public.s3icos_vault_metrics_id_seq'::regclass);
ALTER TABLE ONLY public.raw_s3icos_vault_metrics
    ADD CONSTRAINT s3icos_vault_metrics_pkey PRIMARY KEY (id);
CREATE INDEX idx_vault_metrics_vault_id_timestamp ON public.raw_s3icos_vault_metrics USING btree (vault_id, collection_timestamp DESC);
\unrestrict OqEhRq4PSffGn0n3ABP5gyEGRBveUqz3SkILXEW9kXFm6FVjBeMwEb3X989kIhT
