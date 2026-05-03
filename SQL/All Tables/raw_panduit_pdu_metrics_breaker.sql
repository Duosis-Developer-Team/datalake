\restrict xQprkLVNepb6N93K5g43yDdWd82zFUL0QSzocFbncNWFT3WuC0v1ijqg49gJ4Yi
CREATE TABLE public.raw_panduit_pdu_metrics_breaker (
    id integer NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    pdu_id integer NOT NULL,
    breaker_index character varying(10) NOT NULL,
    breaker_status integer,
    current integer,
    current_percent_load integer,
    current_rating integer,
    power_factor integer,
    power_va bigint,
    power_watts bigint,
    voltage integer
);
COMMENT ON TABLE public.raw_panduit_pdu_metrics_breaker IS 'PDU üzerindeki her bir devre kesicinin (breaker) zaman serisi metriklerini saklar.';
CREATE SEQUENCE public.panduit_pdu_metrics_breaker_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.panduit_pdu_metrics_breaker_id_seq OWNED BY public.raw_panduit_pdu_metrics_breaker.id;
ALTER TABLE ONLY public.raw_panduit_pdu_metrics_breaker ALTER COLUMN id SET DEFAULT nextval('public.panduit_pdu_metrics_breaker_id_seq'::regclass);
ALTER TABLE ONLY public.raw_panduit_pdu_metrics_breaker
    ADD CONSTRAINT panduit_pdu_metrics_breaker_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.raw_panduit_pdu_metrics_breaker
    ADD CONSTRAINT uq_panduit_breaker_metrics_pdu_timestamp_breaker UNIQUE (pdu_id, collection_timestamp, breaker_index);
CREATE INDEX idx_panduit_breaker_metrics_pdu_id_breaker_timestamp ON public.raw_panduit_pdu_metrics_breaker USING btree (pdu_id, breaker_index, collection_timestamp DESC);
\unrestrict xQprkLVNepb6N93K5g43yDdWd82zFUL0QSzocFbncNWFT3WuC0v1ijqg49gJ4Yi
