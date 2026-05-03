\restrict vmk3jyHPTxVSdOUigzeoyndXgwdQsHkvgX4gZCy4j9s28hQjj0lrMeuJuA5fxQ1
CREATE TABLE public.raw_ilo_metrics_disk (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    disk_id character varying(50) NOT NULL,
    power_on_hours integer,
    temperature_celsius real,
    endurance_utilization_percent real,
    uncorrected_read_errors integer,
    uncorrected_write_errors integer
);
ALTER TABLE ONLY public.raw_ilo_metrics_disk
    ADD CONSTRAINT ilo_metrics_disk_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number, disk_id);
CREATE INDEX idx_metrics_disk_id_time ON public.raw_ilo_metrics_disk USING btree (disk_id, collection_timestamp DESC);
CREATE INDEX idx_metrics_disk_serial_time ON public.raw_ilo_metrics_disk USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict vmk3jyHPTxVSdOUigzeoyndXgwdQsHkvgX4gZCy4j9s28hQjj0lrMeuJuA5fxQ1
