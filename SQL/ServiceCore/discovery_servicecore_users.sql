-- Discovery (Silver): ServiceCore users from User/GetAllUsers. UPSERT via NiFi PutDatabaseRecord.

CREATE TABLE IF NOT EXISTS public.discovery_servicecore_users (
    user_id           BIGINT PRIMARY KEY,
    data_type         TEXT,

    email             TEXT,
    full_name         TEXT,
    job_title         TEXT,
    is_enabled        BOOLEAN,
    soft_deleted      BOOLEAN,

    collection_time   TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_users_email
    ON public.discovery_servicecore_users (email);

CREATE INDEX IF NOT EXISTS idx_discovery_servicecore_users_is_enabled
    ON public.discovery_servicecore_users (is_enabled);

COMMENT ON TABLE public.discovery_servicecore_users IS
    'ServiceCore user directory from User/GetAllUsers (Silver). Join user_id to incident org_user_id or service request requester_id. Full catalog each run unless collector --skip-users.';

COMMENT ON COLUMN public.discovery_servicecore_users.user_id IS 'Primary key; maps to JSON user_id (API UserId).';
COMMENT ON COLUMN public.discovery_servicecore_users.data_type IS 'Always servicecore_inventory_user for this table.';
COMMENT ON COLUMN public.discovery_servicecore_users.collection_time IS 'UTC batch timestamp from collector (JSON collection_time).';

-- Existing deployments: add new columns (safe to run once; ignore errors if columns exist).
-- ALTER TABLE public.discovery_servicecore_users ADD COLUMN IF NOT EXISTS job_title TEXT;
-- ALTER TABLE public.discovery_servicecore_users ADD COLUMN IF NOT EXISTS soft_deleted BOOLEAN;
