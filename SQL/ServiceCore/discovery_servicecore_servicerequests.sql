-- Discovery (Silver): current state per ServiceRequest. UPSERT via NiFi PutDatabaseRecord.

CREATE TABLE IF NOT EXISTS public.discovery_servicecore_servicerequests (
    service_request_id            BIGINT PRIMARY KEY,
    data_type                     TEXT,

    service_request_name          TEXT,
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

    agent_group_id                BIGINT,
    agent_group_name              TEXT,
    origin_from_name              TEXT,
    tags                          TEXT,

    request_date                  TIMESTAMPTZ,
    target_resolution_date        TIMESTAMPTZ,
    target_response_date          TIMESTAMPTZ,
    deleted_date                  TIMESTAMPTZ,

    is_active                     BOOLEAN,
    code_prefix                   TEXT,
    guid                          TEXT,

    request_description_text_format TEXT,
    custom_fields_json            TEXT,

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
