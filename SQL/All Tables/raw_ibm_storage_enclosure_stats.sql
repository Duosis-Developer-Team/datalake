\restrict fBtqWlBnIj9rkHVkHb76mSOm2eQMiJEUf12Me3R1Ifav9buI9xp7cCy1sZPk29Q
CREATE TABLE public.raw_ibm_storage_enclosure_stats (
    enclosure_id integer NOT NULL,
    power_w integer,
    temp_c integer,
    temp_f integer,
    "timestamp" timestamp without time zone,
    storage_ip character varying(255)
);
\unrestrict fBtqWlBnIj9rkHVkHb76mSOm2eQMiJEUf12Me3R1Ifav9buI9xp7cCy1sZPk29Q
