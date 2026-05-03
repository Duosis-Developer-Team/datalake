\restrict mSf84FINoJOtHc81pVCaoHlRqkUtfqq9xPpmitqM2zdZXwE3SbhZZhRGQxJO2AM
CREATE TABLE public.discovery_servicecore_servicerequests (
    service_request_id bigint NOT NULL,
    data_type text,
    service_request_name text,
    subject text,
    requester_id bigint,
    requester_full_name text,
    org_users_name text,
    state bigint,
    state_text text,
    status_id bigint,
    status_name text,
    priority_id bigint,
    priority_name text,
    category_name text,
    service_category_name text,
    service_item_names text,
    agent_id bigint,
    agent_group_id bigint,
    agent_group_name text,
    agent_full_name text,
    org_user_support_account_name text,
    org_user_support_account_id bigint,
    sla_policy_name text,
    company_name text,
    origin_from_name text,
    tags text,
    request_date timestamp with time zone,
    target_resolution_date timestamp with time zone,
    target_response_date timestamp with time zone,
    deleted_date timestamp with time zone,
    is_active boolean,
    is_deleted boolean,
    code_prefix text,
    guid text,
    request_description_text_format text,
    custom_fields_json text,
    attachment_files text,
    collection_time timestamp with time zone NOT NULL
);
COMMENT ON TABLE public.discovery_servicecore_servicerequests IS 'ServiceCore ITSM service requests (Silver). One row per service_request_id; UPSERT from collector data_type=servicecore_inventory_servicerequest. SR OData filter uses RequestDate (not LastUpdatedDate).';
COMMENT ON COLUMN public.discovery_servicecore_servicerequests.service_request_id IS 'Primary key; maps to JSON service_request_id.';
COMMENT ON COLUMN public.discovery_servicecore_servicerequests.data_type IS 'Always servicecore_inventory_servicerequest for this table.';
COMMENT ON COLUMN public.discovery_servicecore_servicerequests.subject IS 'Display subject; API Subject or fallback to ServiceRequestName.';
COMMENT ON COLUMN public.discovery_servicecore_servicerequests.org_user_support_account_name IS 'Tenant / support account label for customer linkage.';
COMMENT ON COLUMN public.discovery_servicecore_servicerequests.collection_time IS 'UTC batch timestamp from collector (JSON collection_time).';
ALTER TABLE ONLY public.discovery_servicecore_servicerequests
    ADD CONSTRAINT discovery_servicecore_servicerequests_pkey PRIMARY KEY (service_request_id);
CREATE INDEX idx_discovery_servicecore_sr_org_user_support_account_id ON public.discovery_servicecore_servicerequests USING btree (org_user_support_account_id);
CREATE INDEX idx_discovery_servicecore_sr_priority_name ON public.discovery_servicecore_servicerequests USING btree (priority_name);
CREATE INDEX idx_discovery_servicecore_sr_request_date ON public.discovery_servicecore_servicerequests USING btree (request_date);
CREATE INDEX idx_discovery_servicecore_sr_requester_id ON public.discovery_servicecore_servicerequests USING btree (requester_id);
CREATE INDEX idx_discovery_servicecore_sr_status_name ON public.discovery_servicecore_servicerequests USING btree (status_name);
\unrestrict mSf84FINoJOtHc81pVCaoHlRqkUtfqq9xPpmitqM2zdZXwE3SbhZZhRGQxJO2AM
