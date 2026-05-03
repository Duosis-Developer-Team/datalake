\restrict bbcNGnz5S7Pk8qZcue94VBebzuRUTezXrQxhs6ftOgvdVKLNHk7vvM2IvHqBoWk
CREATE TABLE public.raw_ilo_inventory (
    id integer NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    chassis_model character varying(255),
    chassis_manufacturer character varying(255),
    system_hostname character varying(255),
    system_power_state character varying(50),
    processor_count integer,
    processor_model character varying(255),
    processor_status_health character varying(50),
    total_system_memory_gib integer,
    total_system_persistent_memory_gib integer,
    memory_status_health character varying(50)
);
CREATE SEQUENCE public.ilo_inventory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE public.ilo_inventory_id_seq OWNED BY public.raw_ilo_inventory.id;
ALTER TABLE ONLY public.raw_ilo_inventory ALTER COLUMN id SET DEFAULT nextval('public.ilo_inventory_id_seq'::regclass);
ALTER TABLE ONLY public.raw_ilo_inventory
    ADD CONSTRAINT ilo_inventory_collection_timestamp_chassis_serial_number_key UNIQUE (collection_timestamp, chassis_serial_number);
ALTER TABLE ONLY public.raw_ilo_inventory
    ADD CONSTRAINT ilo_inventory_pkey PRIMARY KEY (id);
CREATE INDEX idx_inventory_serial_time ON public.raw_ilo_inventory USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict bbcNGnz5S7Pk8qZcue94VBebzuRUTezXrQxhs6ftOgvdVKLNHk7vvM2IvHqBoWk
