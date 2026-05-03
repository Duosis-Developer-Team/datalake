\restrict F5qcvKdc7LqchQMFwgYDzpobDggygkA0Lk3Opufb6mgEmQgTcDsp28sKt40AaTn
CREATE TABLE public.raw_ilo_inventory_firmware (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    component_name character varying(255) NOT NULL,
    version character varying(255) NOT NULL,
    updateable boolean,
    device_context character varying(255)
);
ALTER TABLE ONLY public.raw_ilo_inventory_firmware
    ADD CONSTRAINT ilo_inventory_firmware_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number, component_name, version);
\unrestrict F5qcvKdc7LqchQMFwgYDzpobDggygkA0Lk3Opufb6mgEmQgTcDsp28sKt40AaTn
