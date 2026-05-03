\restrict bGiJdXSBxJdt9hufwMMU7VG1HgzJgLvZY5FGnxexUfz8h9RUBl9FxBoxYCHbYF9
CREATE TABLE public.raw_ilo_metrics_temperature (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    sensor_name character varying(255) NOT NULL,
    reading_celsius real,
    status_health character varying(50)
);
ALTER TABLE ONLY public.raw_ilo_metrics_temperature
    ADD CONSTRAINT ilo_metrics_temperature_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number, sensor_name);
CREATE INDEX idx_metrics_temp_sensor_time ON public.raw_ilo_metrics_temperature USING btree (sensor_name, collection_timestamp DESC);
CREATE INDEX idx_metrics_temp_serial_time ON public.raw_ilo_metrics_temperature USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict bGiJdXSBxJdt9hufwMMU7VG1HgzJgLvZY5FGnxexUfz8h9RUBl9FxBoxYCHbYF9
