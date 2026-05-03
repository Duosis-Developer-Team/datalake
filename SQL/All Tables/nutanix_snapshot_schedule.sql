\restrict leGqpcarVO4r1rSwBdFVVXN8Xn13Sc6gvWQ4BPToPwzNx1AqT6RFLlamrn0tQwT
CREATE TABLE public.nutanix_snapshot_schedule (
    collection_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    nutanix_ip character varying(255),
    protection_domain_name character varying(255),
    state character varying(255),
    missing_entities_entity_name character varying(255),
    missing_entities_entity_type character varying(255),
    missing_entities_cg_name character varying(255),
    size_in_bytes bigint,
    vm_names character varying(255),
    schedule_type character varying(255),
    schedule_every_nth integer,
    schedule_start_times_in_usecs bigint,
    schedule_end_time_in_usecs bigint,
    schedule_local_max_snapshots integer,
    schedule_remote_max_snapshots jsonb
);
CREATE INDEX nutanix_snapshot_schedule_collection_time_idx ON public.nutanix_snapshot_schedule USING btree (collection_time DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.nutanix_snapshot_schedule FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict leGqpcarVO4r1rSwBdFVVXN8Xn13Sc6gvWQ4BPToPwzNx1AqT6RFLlamrn0tQwT
