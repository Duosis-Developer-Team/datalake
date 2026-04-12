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
