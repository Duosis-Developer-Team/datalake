\restrict bXl4BfSC3s2L4h1weAa3h6WlzBYO4RZQPE7MS1RrI2d1a7cWvbNLiks63Bjecz7
CREATE TABLE public.raw_servicecore_logs (
    id bigint NOT NULL,
    endpoint_type text NOT NULL,
    raw_content jsonb NOT NULL,
    collected_at timestamp with time zone DEFAULT now() NOT NULL
);
COMMENT ON TABLE public.raw_servicecore_logs IS 'ServiceCore ITSM raw API responses (Bronze). endpoint_type: incident | servicerequest | user';
CREATE SEQUENCE public.raw_servicecore_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.raw_servicecore_logs_id_seq OWNED BY public.raw_servicecore_logs.id;
ALTER TABLE ONLY public.raw_servicecore_logs ALTER COLUMN id SET DEFAULT nextval('public.raw_servicecore_logs_id_seq'::regclass);
ALTER TABLE ONLY public.raw_servicecore_logs
    ADD CONSTRAINT raw_servicecore_logs_pkey PRIMARY KEY (id);
CREATE INDEX idx_raw_servicecore_logs_collected_at ON public.raw_servicecore_logs USING btree (collected_at DESC);
CREATE INDEX idx_raw_servicecore_logs_endpoint_type ON public.raw_servicecore_logs USING btree (endpoint_type);
\unrestrict bXl4BfSC3s2L4h1weAa3h6WlzBYO4RZQPE7MS1RrI2d1a7cWvbNLiks63Bjecz7
