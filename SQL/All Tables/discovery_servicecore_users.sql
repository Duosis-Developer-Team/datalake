\restrict ciX9winilsjYd7Cv78wHbFE21TPc5EMc2NLKfJ2QpBWpVBx5GXubdXL0i1x3e7H
CREATE TABLE public.discovery_servicecore_users (
    user_id bigint NOT NULL,
    data_type text,
    email text,
    full_name text,
    job_title text,
    is_enabled boolean,
    soft_deleted boolean,
    collection_time timestamp with time zone NOT NULL
);
COMMENT ON TABLE public.discovery_servicecore_users IS 'ServiceCore user directory from User/GetAllUsers (Silver). Join user_id to incident org_user_id or service request requester_id. Full catalog each run unless collector --skip-users.';
COMMENT ON COLUMN public.discovery_servicecore_users.user_id IS 'Primary key; maps to JSON user_id (API UserId).';
COMMENT ON COLUMN public.discovery_servicecore_users.data_type IS 'Always servicecore_inventory_user for this table.';
COMMENT ON COLUMN public.discovery_servicecore_users.collection_time IS 'UTC batch timestamp from collector (JSON collection_time).';
ALTER TABLE ONLY public.discovery_servicecore_users
    ADD CONSTRAINT discovery_servicecore_users_pkey PRIMARY KEY (user_id);
CREATE INDEX idx_discovery_servicecore_users_email ON public.discovery_servicecore_users USING btree (email);
CREATE INDEX idx_discovery_servicecore_users_is_enabled ON public.discovery_servicecore_users USING btree (is_enabled);
\unrestrict ciX9winilsjYd7Cv78wHbFE21TPc5EMc2NLKfJ2QpBWpVBx5GXubdXL0i1x3e7H
