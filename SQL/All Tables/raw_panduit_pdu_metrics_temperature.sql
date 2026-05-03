\restrict ZzfxZnKHMpIbhlH44gscy3EeU9QlOKD4tcuKzEl9bdpfySZhkbZGIpgIQNIxST8
CREATE TABLE public.raw_panduit_pdu_metrics_temperature (
    id integer NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    pdu_id integer NOT NULL,
    sensor_id character varying(50) NOT NULL,
    value numeric,
    status integer,
    th_status integer
);
COMMENT ON TABLE public.raw_panduit_pdu_metrics_temperature IS 'PDU''ya bağlı sıcaklık sensörlerinin zaman serisi verilerini saklar.';
CREATE SEQUENCE public.panduit_pdu_metrics_temperature_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.panduit_pdu_metrics_temperature_id_seq OWNED BY public.raw_panduit_pdu_metrics_temperature.id;
ALTER TABLE ONLY public.raw_panduit_pdu_metrics_temperature ALTER COLUMN id SET DEFAULT nextval('public.panduit_pdu_metrics_temperature_id_seq'::regclass);
ALTER TABLE ONLY public.raw_panduit_pdu_metrics_temperature
    ADD CONSTRAINT panduit_pdu_metrics_temperature_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.raw_panduit_pdu_metrics_temperature
    ADD CONSTRAINT uq_panduit_temperature_metrics_pdu_timestamp_sensor UNIQUE (pdu_id, collection_timestamp, sensor_id);
CREATE INDEX idx_panduit_temperature_metrics_pdu_id_sensor_timestamp ON public.raw_panduit_pdu_metrics_temperature USING btree (pdu_id, sensor_id, collection_timestamp DESC);
\unrestrict ZzfxZnKHMpIbhlH44gscy3EeU9QlOKD4tcuKzEl9bdpfySZhkbZGIpgIQNIxST8
