\restrict My3uhmm2oyBPsF7HBLz5pVWMIgg5I9WOwgcghG029BQB8Fybwy0FrEWtBD6pb5f
CREATE TABLE public.raw_ilo_inventory_disk (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    disk_id character varying(50) NOT NULL,
    model character varying(255),
    capacity_bytes bigint,
    protocol character varying(50),
    media_type character varying(50),
    serial_number character varying(255),
    status_health character varying(50),
    status_state character varying(50),
    firmware_version character varying(50),
    block_size_bytes integer
);
ALTER TABLE ONLY public.raw_ilo_inventory_disk
    ADD CONSTRAINT ilo_inventory_disk_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number, disk_id);
CREATE INDEX idx_inventory_disk_serial_time ON public.raw_ilo_inventory_disk USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict My3uhmm2oyBPsF7HBLz5pVWMIgg5I9WOwgcghG029BQB8Fybwy0FrEWtBD6pb5f
