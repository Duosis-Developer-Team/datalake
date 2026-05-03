\restrict U5q0GiOnXVS8TdV3uJXUFmGKgackU45jtIIJV2nDbdpJQ2FP403zE7HUlQwu4oy
CREATE TABLE public.nutanix_snapshot_schedule_metrics (
    collection_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    nutanix_ip character varying(255),
    protection_domain_name character varying(255),
    state character varying(255),
    missing_entities_entity_name text,
    missing_entities_entity_type text,
    missing_entities_cg_name text,
    size_in_bytes bigint,
    vm_names text,
    schedule_type character varying(255),
    schedule_every_nth integer,
    schedule_start_times_in_usecs bigint,
    schedule_end_time_in_usecs bigint,
    schedule_local_max_snapshots integer,
    schedule_remote_max_snapshots jsonb,
    exclusive_usage_in_bytes bigint,
    snapshot_id character varying(255),
    snapshot_create_time_usecs bigint,
    snapshot_expiry_time_usecs bigint,
    schedule_user_start_time_in_usecs bigint,
    schedule_id character varying(255),
    schedule_suspended boolean,
    schedule_local_retention_period bigint,
    schedule_remote_retention_period jsonb,
    schedule_local_retention_type character varying(255),
    schedule_remote_retention_type character varying(255)
);
ALTER TABLE ONLY public.nutanix_snapshot_schedule_metrics
    ADD CONSTRAINT unique_nutanix_snapshot_schedule UNIQUE (collection_time, nutanix_ip, protection_domain_name, snapshot_id, schedule_id);
ALTER TABLE ONLY public.nutanix_snapshot_schedule_metrics
    ADD CONSTRAINT unique_snapshot_identity UNIQUE (nutanix_ip, protection_domain_name, snapshot_id, snapshot_create_time_usecs, collection_time);
CREATE INDEX nutanix_snapshot_schedule_metrics_collection_time_idx ON public.nutanix_snapshot_schedule_metrics USING btree (collection_time DESC);
CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.nutanix_snapshot_schedule_metrics FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();
\unrestrict U5q0GiOnXVS8TdV3uJXUFmGKgackU45jtIIJV2nDbdpJQ2FP403zE7HUlQwu4oy
