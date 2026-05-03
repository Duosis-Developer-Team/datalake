\restrict Lg6couJoigp1PCc8kRGB2haU4myl7x5ZxwQeX1EMkcZ8ZGN62hOuIu3O31h70pJ
CREATE TABLE public.raw_ibm_storage_vdisk_mapping (
    id integer,
    name character varying(250),
    scsi_id integer,
    vdisk_id integer,
    vdisk_name character varying(250),
    vdisk_uid character varying(250),
    io_group_id integer,
    io_group_name character varying(250),
    mapping_type character varying(250),
    host_cluster_id character varying(250),
    host_cluster_name character varying(250),
    protocol character varying(250),
    "timestamp" timestamp without time zone,
    storage_ip character varying(255)
);
\unrestrict Lg6couJoigp1PCc8kRGB2haU4myl7x5ZxwQeX1EMkcZ8ZGN62hOuIu3O31h70pJ
