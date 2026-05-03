\restrict kOxEOm7ifCSz43VGePcDgw5DLkqACMvRORhvfbhIGcyLYhQXqexn8IBvmV0d7Mi
CREATE TABLE public.raw_panduit_pdu_inventory (
    id integer NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    pdu_id integer NOT NULL,
    pdu_name character varying(255),
    zabbix_host_name character varying(255),
    location character varying(50),
    rack_id character varying(50),
    pdu_index character varying(50),
    device_model character varying(255),
    firmware_version character varying(50),
    hardware_version character varying(50),
    system_name character varying(255),
    breaker_count integer,
    outlet_count integer,
    door_count integer,
    dry_count integer,
    hid_count integer,
    humidity_count integer,
    input_phase_count integer,
    rope_count integer,
    spot_count integer,
    temperature_count integer
);
COMMENT ON TABLE public.raw_panduit_pdu_inventory IS 'PDU cihazlarının konum, model ve versiyon gibi statik envanter bilgilerini saklar.';
CREATE SEQUENCE public.panduit_pdu_inventory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.panduit_pdu_inventory_id_seq OWNED BY public.raw_panduit_pdu_inventory.id;
ALTER TABLE ONLY public.raw_panduit_pdu_inventory ALTER COLUMN id SET DEFAULT nextval('public.panduit_pdu_inventory_id_seq'::regclass);
ALTER TABLE ONLY public.raw_panduit_pdu_inventory
    ADD CONSTRAINT panduit_pdu_inventory_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.raw_panduit_pdu_inventory
    ADD CONSTRAINT uq_panduit_inventory_pdu_timestamp UNIQUE (pdu_id, collection_timestamp);
CREATE INDEX idx_panduit_inventory_pdu_id_timestamp ON public.raw_panduit_pdu_inventory USING btree (pdu_id, collection_timestamp DESC);
\unrestrict kOxEOm7ifCSz43VGePcDgw5DLkqACMvRORhvfbhIGcyLYhQXqexn8IBvmV0d7Mi
