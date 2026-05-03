\restrict PXMfHrcLZxAAFMXnLI3uWYhwIYemJVN5GzQA80ILrdfEJnastnSfXnbVTDapqcP
CREATE TABLE public.raw_ilo_metrics_fan (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    fan_name character varying(255) NOT NULL,
    reading_percent real,
    reading_units character varying(50),
    status_health character varying(50)
);
ALTER TABLE ONLY public.raw_ilo_metrics_fan
    ADD CONSTRAINT ilo_metrics_fan_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number, fan_name);
CREATE INDEX idx_metrics_fan_name_time ON public.raw_ilo_metrics_fan USING btree (fan_name, collection_timestamp DESC);
CREATE INDEX idx_metrics_fan_serial_time ON public.raw_ilo_metrics_fan USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict PXMfHrcLZxAAFMXnLI3uWYhwIYemJVN5GzQA80ILrdfEJnastnSfXnbVTDapqcP
