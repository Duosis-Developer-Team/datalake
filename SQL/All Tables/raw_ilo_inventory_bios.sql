\restrict UbeCQJ9hHY7GKOIvBzemXx2TaXER4CQ6soR5jbl9cDYPVJfZx6wwTlxqKogUhMX
CREATE TABLE public.raw_ilo_inventory_bios (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    workloadprofile character varying(255),
    prochyperthreading character varying(50),
    procvirtualization character varying(50),
    powerregulator character varying(50),
    sriov character varying(50),
    bootmode character varying(50)
);
ALTER TABLE ONLY public.raw_ilo_inventory_bios
    ADD CONSTRAINT ilo_inventory_bios_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number);
CREATE INDEX idx_inventory_bios_serial_time ON public.raw_ilo_inventory_bios USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict UbeCQJ9hHY7GKOIvBzemXx2TaXER4CQ6soR5jbl9cDYPVJfZx6wwTlxqKogUhMX
