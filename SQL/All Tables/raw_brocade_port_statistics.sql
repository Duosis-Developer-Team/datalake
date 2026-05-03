\restrict Kl6J83uqM0nlVbzkUIli2ZezyXVz0fZDEKYl0ym3QKeB0pwDfcuU47IlgcuAbim
CREATE TABLE public.raw_brocade_port_statistics (
    switch_host character varying(255) NOT NULL,
    collection_timestamp timestamp with time zone NOT NULL,
    name character varying(50) NOT NULL,
    time_difference_seconds double precision,
    in_octets bigint,
    out_octets bigint,
    in_frames bigint,
    out_frames bigint,
    crc_errors bigint,
    class_3_discards bigint,
    link_failures bigint,
    loss_of_signal bigint,
    loss_of_sync bigint,
    invalid_transmission_words bigint,
    in_octets_delta bigint,
    out_octets_delta bigint,
    in_frames_delta bigint,
    out_frames_delta bigint,
    crc_errors_delta bigint,
    class_3_discards_delta bigint,
    link_failures_delta bigint,
    loss_of_signal_delta bigint,
    loss_of_sync_delta bigint,
    invalid_transmission_words_delta bigint,
    in_rate bigint,
    out_rate bigint
);
COMMENT ON TABLE public.raw_brocade_port_statistics IS 'Her bir portun kümülatif ve delta (fark) performans/hata sayaçlarını içerir.';
COMMENT ON COLUMN public.raw_brocade_port_statistics.in_octets IS 'Switch açıldığından beri porta gelen toplam byte sayısı.';
COMMENT ON COLUMN public.raw_brocade_port_statistics.in_octets_delta IS 'İki ölçüm arasında porta gelen byte sayısı.';
ALTER TABLE ONLY public.raw_brocade_port_statistics
    ADD CONSTRAINT brocade_port_statistics_pkey PRIMARY KEY (switch_host, collection_timestamp, name);
\unrestrict Kl6J83uqM0nlVbzkUIli2ZezyXVz0fZDEKYl0ym3QKeB0pwDfcuU47IlgcuAbim
