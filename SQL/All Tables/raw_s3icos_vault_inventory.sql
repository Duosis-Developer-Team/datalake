\restrict mjZu943EZS6WlObfqq1g5f2Zo3MsTgyuliSVNEdc5hI7bqItrGI6XIrLeT06tZ5
CREATE TABLE public.raw_s3icos_vault_inventory (
    id integer NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    vault_id integer NOT NULL,
    vault_name character varying(255),
    uuid character varying(255),
    description text,
    type character varying(50),
    width integer,
    threshold integer,
    write_threshold integer,
    privacy_enabled boolean,
    vault_purpose character varying(50),
    soft_quota_bytes bigint,
    hard_quota_bytes bigint
);
CREATE SEQUENCE public.s3icos_vault_inventory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.s3icos_vault_inventory_id_seq OWNED BY public.raw_s3icos_vault_inventory.id;
ALTER TABLE ONLY public.raw_s3icos_vault_inventory ALTER COLUMN id SET DEFAULT nextval('public.s3icos_vault_inventory_id_seq'::regclass);
ALTER TABLE ONLY public.raw_s3icos_vault_inventory
    ADD CONSTRAINT s3icos_vault_inventory_pkey PRIMARY KEY (id);
CREATE INDEX idx_vault_inventory_vault_id_timestamp ON public.raw_s3icos_vault_inventory USING btree (vault_id, collection_timestamp DESC);
\unrestrict mjZu943EZS6WlObfqq1g5f2Zo3MsTgyuliSVNEdc5hI7bqItrGI6XIrLeT06tZ5
