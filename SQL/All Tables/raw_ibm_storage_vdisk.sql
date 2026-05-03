\restrict t4TXObaVKFNSKMXBhNUkoyzfKKaVeLrykruLMtywcRYWG0BAFQJh3nkSEDjM5tm
CREATE TABLE public.raw_ibm_storage_vdisk (
    id character varying(255),
    name character varying(255),
    io_group_id character varying(255),
    io_group_name character varying(255),
    status character varying(50),
    mdisk_grp_id character varying(255),
    mdisk_grp_name character varying(255),
    capacity character varying(50),
    type character varying(50),
    fc_id character varying(255),
    fc_name character varying(255),
    rc_id character varying(255),
    rc_name character varying(255),
    vdisk_uid character varying(255),
    fc_map_count integer,
    copy_count integer,
    fast_write_state character varying(50),
    se_copy_count integer,
    rc_change character varying(50),
    compressed_copy_count integer,
    parent_mdisk_grp_id character varying(255),
    parent_mdisk_grp_name character varying(255),
    owner_id character varying(255),
    owner_name character varying(255),
    formatting character varying(50),
    encrypt character varying(10),
    volume_id character varying(255),
    volume_name character varying(255),
    function character varying(255),
    protocol character varying(50),
    "timestamp" timestamp without time zone NOT NULL,
    storage_ip character varying(255)
);
CREATE INDEX raw_ibm_storage_vdisk_timestamp_idx ON public.raw_ibm_storage_vdisk USING btree ("timestamp" DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.raw_ibm_storage_vdisk FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict t4TXObaVKFNSKMXBhNUkoyzfKKaVeLrykruLMtywcRYWG0BAFQJh3nkSEDjM5tm
