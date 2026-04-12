-- Discovery (Silver): current state per ServiceRequest. UPSERT via NiFi PutDatabaseRecord.

CREATE TABLE IF NOT EXISTS public.discovery_servicecore_servicerequests (
    service_request_id            BIGINT PRIMARY KEY,
    data_type                     TEXT,

    service_request_name          TEXT,
    subject                       TEXT,
    requester_id                  BIGINT,
    requester_full_name           TEXT,
    org_users_name                TEXT,

    state                         BIGINT,
    state_text                    TEXT,
    status_id                     BIGINT,
    status_name                   TEXT,
    priority_id                   BIGINT,
    priority_name                 TEXT,

    category_name                 TEXT,
    service_category_name         TEXT,
    service_item_names            TEXT,

    agent_id                      BIGINT,
    agent_group_id                BIGINT,
    agent_group_name              TEXT,
    agent_full_name               TEXT,

    org_user_support_account_name TEXT,
    org_user_support_account_id   BIGINT,
    sla_policy_name               TEXT,
    company_name                  TEXT,

    origin_from_name              TEXT,
    tags                          TEXT,

    request_date                  TIMESTAMPTZ,
    target_resolution_date        TIMESTAMPTZ,
    target_response_date          TIMESTAMPTZ,
    deleted_date                  TIMESTAMPTZ,

    is_active                     BOOLEAN,
    is_deleted                    BOOLEAN,
    code_prefix                   TEXT,
    guid                          TEXT,

    request_description_text_format TEXT,
    custom_fields_json            TEXT,
    attachment_files              TEXT,

    collection_time               TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_sr_status_name
    ON public.discovery_servicecore_servicerequests (status_name);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_sr_priority_name
    ON public.discovery_servicecore_servicerequests (priority_name);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_sr_requester_id
    ON public.discovery_servicecore_servicerequests (requester_id);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_sr_request_date
    ON public.discovery_servicecore_servicerequests (request_date);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_sr_org_user_support_account_id
    ON public.discovery_servicecore_servicerequests (org_user_support_account_id);

COMMENT ON TABLE public.discovery_servicecore_servicerequests IS
    'ServiceCore ITSM service requests (Silver). One row per service_request_id; UPSERT from collector data_type=servicecore_inventory_servicerequest. SR OData filter uses RequestDate (not LastUpdatedDate).';

COMMENT ON COLUMN public.discovery_servicecore_servicerequests.service_request_id IS 'Primary key; maps to JSON service_request_id.';
COMMENT ON COLUMN public.discovery_servicecore_servicerequests.data_type IS 'Always servicecore_inventory_servicerequest for this table.';
COMMENT ON COLUMN public.discovery_servicecore_servicerequests.subject IS 'Display subject; API Subject or fallback to ServiceRequestName.';
COMMENT ON COLUMN public.discovery_servicecore_servicerequests.org_user_support_account_name IS 'Tenant / support account label for customer linkage.';
COMMENT ON COLUMN public.discovery_servicecore_servicerequests.collection_time IS 'UTC batch timestamp from collector (JSON collection_time).';

-- Existing deployments: add new columns (safe to run once; ignore errors if columns exist).
-- ALTER TABLE public.discovery_servicecore_servicerequests ADD COLUMN IF NOT EXISTS subject TEXT;
-- ALTER TABLE public.discovery_servicecore_servicerequests ADD COLUMN IF NOT EXISTS agent_id BIGINT;
-- ALTER TABLE public.discovery_servicecore_servicerequests ADD COLUMN IF NOT EXISTS agent_full_name TEXT;
-- ALTER TABLE public.discovery_servicecore_servicerequests ADD COLUMN IF NOT EXISTS org_user_support_account_name TEXT;
-- ALTER TABLE public.discovery_servicecore_servicerequests ADD COLUMN IF NOT EXISTS org_user_support_account_id BIGINT;
-- ALTER TABLE public.discovery_servicecore_servicerequests ADD COLUMN IF NOT EXISTS sla_policy_name TEXT;
-- ALTER TABLE public.discovery_servicecore_servicerequests ADD COLUMN IF NOT EXISTS company_name TEXT;
-- ALTER TABLE public.discovery_servicecore_servicerequests ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN;
-- ALTER TABLE public.discovery_servicecore_servicerequests ADD COLUMN IF NOT EXISTS attachment_files TEXT;
