\restrict CvKVZVvDxSJKo9BmWt9pk8quaw5RuMUv3mXQegiOEys6xqOEPQ55qhwfMtcD3wo
CREATE TABLE public.raw_ilo_metrics_system (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    cpu_utilization_percent real,
    memory_bus_utilization_percent real
);
ALTER TABLE ONLY public.raw_ilo_metrics_system
    ADD CONSTRAINT ilo_metrics_system_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number);
CREATE INDEX idx_metrics_system_serial_time ON public.raw_ilo_metrics_system USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict CvKVZVvDxSJKo9BmWt9pk8quaw5RuMUv3mXQegiOEys6xqOEPQ55qhwfMtcD3wo
