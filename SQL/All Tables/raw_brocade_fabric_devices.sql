\restrict N8Ye7QNDex9sQhyeUGdPra5w5ea4yMmm6PwoOhMS0IqIT4ahdwn2YavhQgnYoVW
CREATE TABLE public.raw_brocade_fabric_devices (
    switch_host character varying(255) NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    device_wwpn character varying(23) NOT NULL,
    device_wwnn character varying(23),
    port_index integer,
    port_id character varying(10),
    port_symbolic_name text,
    node_symbolic_name text,
    device_port_type character varying(50),
    class_of_service character varying(50)
);
COMMENT ON TABLE public.raw_brocade_fabric_devices IS 'Switch''e bağlı olan cihazların (sunucu, storage vb.) WWN ve bağlantı noktası bilgilerini içerir.';
COMMENT ON COLUMN public.raw_brocade_fabric_devices.device_wwpn IS 'Cihazın porta ait World Wide Port Name''i.';
COMMENT ON COLUMN public.raw_brocade_fabric_devices.port_index IS 'Cihazın bağlı olduğu switch portunun numarası.';
ALTER TABLE ONLY public.raw_brocade_fabric_devices
    ADD CONSTRAINT brocade_fabric_devices_pkey PRIMARY KEY (switch_host, collection_timestamp, device_wwpn);
\unrestrict N8Ye7QNDex9sQhyeUGdPra5w5ea4yMmm6PwoOhMS0IqIT4ahdwn2YavhQgnYoVW
