\restrict zvrG2UIiQhoIw61nfi5HZSdAXgPgbUosdlaJV79G16QYKo66e3KE0WjdDUbQrrB
CREATE TABLE public.raw_ilo_inventory_nic (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    interface_id character varying(50) NOT NULL,
    name character varying(255),
    mac_address character varying(50),
    speed_mbps integer,
    link_status character varying(50),
    full_duplex boolean,
    ipv4_addresses text,
    status_health character varying(50)
);
ALTER TABLE ONLY public.raw_ilo_inventory_nic
    ADD CONSTRAINT ilo_inventory_nic_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number, interface_id);
CREATE INDEX idx_inventory_nic_serial_time ON public.raw_ilo_inventory_nic USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict zvrG2UIiQhoIw61nfi5HZSdAXgPgbUosdlaJV79G16QYKo66e3KE0WjdDUbQrrB
