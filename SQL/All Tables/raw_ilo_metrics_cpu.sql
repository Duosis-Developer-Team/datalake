\restrict 6QDOB4o4bOovWulr63RV5pBEaABJUfG5XuiR7bL0BiSWdMMphiMHrid1meLcep9
CREATE TABLE public.raw_ilo_metrics_cpu (
    collection_timestamp timestamp with time zone NOT NULL,
    chassis_serial_number character varying(255) NOT NULL,
    cpu_id integer NOT NULL,
    power_watts real,
    frequency_mhz real
);
ALTER TABLE ONLY public.raw_ilo_metrics_cpu
    ADD CONSTRAINT ilo_metrics_cpu_pkey PRIMARY KEY (collection_timestamp, chassis_serial_number, cpu_id);
CREATE INDEX idx_metrics_cpu_id_time ON public.raw_ilo_metrics_cpu USING btree (cpu_id, collection_timestamp DESC);
CREATE INDEX idx_metrics_cpu_serial_time ON public.raw_ilo_metrics_cpu USING btree (chassis_serial_number, collection_timestamp DESC);
\unrestrict 6QDOB4o4bOovWulr63RV5pBEaABJUfG5XuiR7bL0BiSWdMMphiMHrid1meLcep9
