\restrict N97roTnTjCMlBMteOd630C0bgrTdTUwWdeahEggtAR3eBZhAWcstPkMa1hqwd6j
CREATE TABLE public.raw_ilo_inventory_psu (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    psu_id character varying(50) NOT NULL,
    model character varying(255),
    serial_number character varying(255),
    part_number character varying(255),
    firmware_version character varying(50),
    power_capacity_watts integer,
    status_health character varying(50)
);
ALTER TABLE ONLY public.raw_ilo_inventory_psu
    ADD CONSTRAINT ilo_inventory_psu_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number, psu_id);
CREATE INDEX idx_inventory_psu_serial_time ON public.raw_ilo_inventory_psu USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict N97roTnTjCMlBMteOd630C0bgrTdTUwWdeahEggtAR3eBZhAWcstPkMa1hqwd6j
