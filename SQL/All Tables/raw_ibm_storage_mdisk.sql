\restrict f0tsMVjRRSPTx9D3YY2K5LHqsi5hAjVUZH71SjH5q6MFiEj0vwawG0NU6CxHQpP
CREATE TABLE public.raw_ibm_storage_mdisk (
    id text NOT NULL,
    name text,
    status text,
    mode text,
    mdisk_grp_id text,
    mdisk_grp_name text,
    capacity text,
    "ctrl_LUN_#" text,
    controller_name text,
    uid text,
    tier text,
    encrypt text,
    site_id text,
    site_name text,
    distributed text,
    dedupe text,
    over_provisioned text,
    supports_unmap text,
    "timestamp" timestamp without time zone DEFAULT now(),
    storage_ip character varying(255)
);
\unrestrict f0tsMVjRRSPTx9D3YY2K5LHqsi5hAjVUZH71SjH5q6MFiEj0vwawG0NU6CxHQpP
