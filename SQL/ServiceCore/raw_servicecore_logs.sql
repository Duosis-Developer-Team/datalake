-- Bronze layer: immutable append-only raw API payloads (JSONB).
-- Naming: raw_<domain>_<entity> per collector_discovery_template.md

CREATE TABLE IF NOT EXISTS public.raw_servicecore_logs (
    id              BIGSERIAL PRIMARY KEY,
    endpoint_type   TEXT NOT NULL,
    raw_content     JSONB NOT NULL,
    collected_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.raw_servicecore_logs IS 'ServiceCore ITSM raw API responses (Bronze). endpoint_type: incident | servicerequest';

CREATE INDEX IF NOT EXISTS idx_raw_servicecore_logs_collected_at
    ON public.raw_servicecore_logs (collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_servicecore_logs_endpoint_type
    ON public.raw_servicecore_logs (endpoint_type);
