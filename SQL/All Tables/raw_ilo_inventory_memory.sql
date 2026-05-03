\restrict 5EBGFmCTV7zs5db03rexfOcvvRccys9942SdCKf5vJ2PNoWOMAtgEqR7mMZSmAr
CREATE TABLE public.raw_ilo_inventory_memory (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    dimm_id character varying(50) NOT NULL,
    memory_type character varying(50),
    capacity_mib integer,
    operating_speed_mhz integer,
    manufacturer character varying(255),
    part_number character varying(255),
    status_health character varying(50),
    status_state character varying(50)
);
ALTER TABLE ONLY public.raw_ilo_inventory_memory
    ADD CONSTRAINT ilo_inventory_memory_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number, dimm_id);
CREATE INDEX idx_inventory_memory_serial_time ON public.raw_ilo_inventory_memory USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict 5EBGFmCTV7zs5db03rexfOcvvRccys9942SdCKf5vJ2PNoWOMAtgEqR7mMZSmAr
