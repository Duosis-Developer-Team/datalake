\restrict CTglMaB5GyLhBT4YJYGbX858mfUGQ3iqUHVGGa1eMd1MftH2myOI8g6blYPEPjY
CREATE TABLE public.raw_ilo_inventory_processor (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    processor_id character varying(50) NOT NULL,
    model character varying(255),
    max_speed_mhz integer,
    total_cores integer,
    total_threads integer,
    status_health character varying(50),
    status_state character varying(50)
);
ALTER TABLE ONLY public.raw_ilo_inventory_processor
    ADD CONSTRAINT ilo_inventory_processor_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number, processor_id);
CREATE INDEX idx_inventory_processor_serial_time ON public.raw_ilo_inventory_processor USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict CTglMaB5GyLhBT4YJYGbX858mfUGQ3iqUHVGGa1eMd1MftH2myOI8g6blYPEPjY
