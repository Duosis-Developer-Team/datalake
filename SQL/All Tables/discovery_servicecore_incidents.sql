\restrict nkyKq4mFvgYrnWAZjcDOHhtgFcs5hzusI7HgIs0qaknUmlgVGMlkzTXYaqbeEee
CREATE TABLE public.discovery_servicecore_incidents (
    ticket_id bigint NOT NULL,
    data_type text,
    subject text,
    state bigint,
    state_text text,
    status_id bigint,
    status_name text,
    priority_id bigint,
    priority_name text,
    category_id bigint,
    category_name text,
    org_user_id bigint,
    org_users_name text,
    agent_id bigint,
    agent_group_id bigint,
    agent_group_name text,
    agent_full_name text,
    org_user_support_account_name text,
    org_user_support_account_id bigint,
    sla_policy_name text,
    company_name text,
    times_reopen bigint,
    is_active boolean,
    is_deleted boolean,
    is_merged boolean,
    created_date timestamp with time zone,
    last_updated_date timestamp with time zone,
    target_resolution_date timestamp with time zone,
    closed_and_done_date timestamp with time zone,
    code_prefix text,
    guid text,
    description_text_format text,
    custom_fields_json text,
    attachment_files text,
    origin_from_name text,
    collection_time timestamp with time zone NOT NULL
);
COMMENT ON TABLE public.discovery_servicecore_incidents IS 'ServiceCore ITSM incident tickets (Silver). One row per ticket_id; UPSERT from collector data_type=servicecore_inventory_incident. JSON keys match servicecore-discovery.json incident subset; omitted keys are null.';
COMMENT ON COLUMN public.discovery_servicecore_incidents.ticket_id IS 'Primary key; maps to JSON ticket_id.';
COMMENT ON COLUMN public.discovery_servicecore_incidents.data_type IS 'Always servicecore_inventory_incident for this table.';
COMMENT ON COLUMN public.discovery_servicecore_incidents.org_user_support_account_name IS 'Tenant / support account label for customer linkage.';
COMMENT ON COLUMN public.discovery_servicecore_incidents.org_user_support_account_id IS 'Tenant / support account id.';
COMMENT ON COLUMN public.discovery_servicecore_incidents.collection_time IS 'UTC batch timestamp from collector (JSON collection_time).';
ALTER TABLE ONLY public.discovery_servicecore_incidents
    ADD CONSTRAINT discovery_servicecore_incidents_pkey PRIMARY KEY (ticket_id);
CREATE INDEX idx_discovery_servicecore_incidents_category_name ON public.discovery_servicecore_incidents USING btree (category_name);
CREATE INDEX idx_discovery_servicecore_incidents_created_date ON public.discovery_servicecore_incidents USING btree (created_date);
CREATE INDEX idx_discovery_servicecore_incidents_org_user_id ON public.discovery_servicecore_incidents USING btree (org_user_id);
CREATE INDEX idx_discovery_servicecore_incidents_org_user_support_account_id ON public.discovery_servicecore_incidents USING btree (org_user_support_account_id);
CREATE INDEX idx_discovery_servicecore_incidents_priority_name ON public.discovery_servicecore_incidents USING btree (priority_name);
CREATE INDEX idx_discovery_servicecore_incidents_status_name ON public.discovery_servicecore_incidents USING btree (status_name);
\unrestrict nkyKq4mFvgYrnWAZjcDOHhtgFcs5hzusI7HgIs0qaknUmlgVGMlkzTXYaqbeEee
