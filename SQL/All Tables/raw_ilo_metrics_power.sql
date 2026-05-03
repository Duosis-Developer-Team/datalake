\restrict DF70oelZX3kcdeIuyDvx5u5RemuvslVakfZJc4z01T9JUkRDfVobQHCjmCS2GAN
CREATE TABLE public.raw_ilo_metrics_power (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    psu_id integer NOT NULL,
    power_output_watts real
);
ALTER TABLE ONLY public.raw_ilo_metrics_power
    ADD CONSTRAINT ilo_metrics_power_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number, psu_id);
CREATE INDEX idx_metrics_power_psu_time ON public.raw_ilo_metrics_power USING btree (psu_id, collection_timestamp DESC);
CREATE INDEX idx_metrics_power_serial_time ON public.raw_ilo_metrics_power USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict DF70oelZX3kcdeIuyDvx5u5RemuvslVakfZJc4z01T9JUkRDfVobQHCjmCS2GAN
