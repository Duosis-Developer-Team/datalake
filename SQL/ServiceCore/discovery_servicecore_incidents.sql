-- Discovery (Silver): current state per Incident ticket_id. UPSERT via NiFi PutDatabaseRecord.

CREATE TABLE IF NOT EXISTS public.discovery_servicecore_incidents (
    ticket_id                 BIGINT PRIMARY KEY,
    data_type                 TEXT,

    subject                   TEXT,
    state                     BIGINT,
    state_text                TEXT,
    status_id                 BIGINT,
    status_name               TEXT,
    priority_id               BIGINT,
    priority_name             TEXT,
    category_id               BIGINT,
    category_name             TEXT,

    org_user_id               BIGINT,
    org_users_name            TEXT,
    agent_id                  BIGINT,
    agent_group_id            BIGINT,
    agent_group_name          TEXT,
    agent_full_name           TEXT,

    org_user_support_account_name TEXT,
    org_user_support_account_id   BIGINT,
    sla_policy_name           TEXT,
    company_name              TEXT,
    times_reopen              BIGINT,

    is_active                 BOOLEAN,
    is_deleted                BOOLEAN,
    is_merged                 BOOLEAN,

    created_date              TIMESTAMPTZ,
    last_updated_date         TIMESTAMPTZ,
    target_resolution_date    TIMESTAMPTZ,
    closed_and_done_date      TIMESTAMPTZ,

    code_prefix               TEXT,
    guid                      TEXT,

    description_text_format   TEXT,
    custom_fields_json        TEXT,
    attachment_files          TEXT,
    origin_from_name          TEXT,

    collection_time           TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_incidents_status_name
    ON public.discovery_servicecore_incidents (status_name);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_incidents_priority_name
    ON public.discovery_servicecore_incidents (priority_name);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_incidents_category_name
    ON public.discovery_servicecore_incidents (category_name);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_incidents_org_user_id
    ON public.discovery_servicecore_incidents (org_user_id);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_incidents_created_date
    ON public.discovery_servicecore_incidents (created_date);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_incidents_org_user_support_account_id
    ON public.discovery_servicecore_incidents (org_user_support_account_id);

COMMENT ON TABLE public.discovery_servicecore_incidents IS
    'ServiceCore ITSM incident tickets (Silver). One row per ticket_id; UPSERT from collector data_type=servicecore_inventory_incident. JSON keys match servicecore-discovery.json incident subset; omitted keys are null.';

COMMENT ON COLUMN public.discovery_servicecore_incidents.ticket_id IS 'Primary key; maps to JSON ticket_id.';
COMMENT ON COLUMN public.discovery_servicecore_incidents.data_type IS 'Always servicecore_inventory_incident for this table.';
COMMENT ON COLUMN public.discovery_servicecore_incidents.org_user_support_account_name IS 'Tenant / support account label for customer linkage.';
COMMENT ON COLUMN public.discovery_servicecore_incidents.org_user_support_account_id IS 'Tenant / support account id.';
COMMENT ON COLUMN public.discovery_servicecore_incidents.collection_time IS 'UTC batch timestamp from collector (JSON collection_time).';

-- Existing deployments: add new columns (safe to run once; ignore errors if columns exist).
-- ALTER TABLE public.discovery_servicecore_incidents ADD COLUMN IF NOT EXISTS agent_full_name TEXT;
-- ALTER TABLE public.discovery_servicecore_incidents ADD COLUMN IF NOT EXISTS org_user_support_account_name TEXT;
-- ALTER TABLE public.discovery_servicecore_incidents ADD COLUMN IF NOT EXISTS org_user_support_account_id BIGINT;
-- ALTER TABLE public.discovery_servicecore_incidents ADD COLUMN IF NOT EXISTS sla_policy_name TEXT;
-- ALTER TABLE public.discovery_servicecore_incidents ADD COLUMN IF NOT EXISTS company_name TEXT;
-- ALTER TABLE public.discovery_servicecore_incidents ADD COLUMN IF NOT EXISTS times_reopen BIGINT;
-- ALTER TABLE public.discovery_servicecore_incidents ADD COLUMN IF NOT EXISTS is_active BOOLEAN;
-- ALTER TABLE public.discovery_servicecore_incidents ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN;
-- ALTER TABLE public.discovery_servicecore_incidents ADD COLUMN IF NOT EXISTS is_merged BOOLEAN;
