\restrict PmhqFeVo1Bbc75KFP19dIftHfaj7Me77azsAsJViQWDUttdsDatnAiwuXueDwMT
CREATE TABLE public.discovery_crm_customer_alias (
    crm_accountid text NOT NULL,
    crm_account_name text NOT NULL,
    canonical_customer_key text,
    netbox_musteri_value text,
    notes text,
    source text DEFAULT 'auto'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT discovery_crm_customer_alias_source_check CHECK ((source = ANY (ARRAY['auto'::text, 'manual'::text])))
);
COMMENT ON TABLE public.discovery_crm_customer_alias IS 'Identity resolution bridge: maps CRM account GUIDs to canonical platform customer keys and NetBox musteri values. Rows with source=auto are seeded by seed_customer_alias_from_accounts.sql; manually corrected rows set source=manual and survive re-seeding.';
COMMENT ON COLUMN public.discovery_crm_customer_alias.crm_accountid IS 'CRM account GUID — primary key. FK to discovery_crm_accounts.accountid.';
COMMENT ON COLUMN public.discovery_crm_customer_alias.crm_account_name IS 'Account name from CRM at seed time.';
COMMENT ON COLUMN public.discovery_crm_customer_alias.canonical_customer_key IS 'Platform canonical key used in GUI customer selector and all API filters.';
COMMENT ON COLUMN public.discovery_crm_customer_alias.netbox_musteri_value IS 'Value matching discovery_netbox_virtualization_vm.custom_fields_musteri for VM ownership join.';
COMMENT ON COLUMN public.discovery_crm_customer_alias.notes IS 'Free-text operator notes on the mapping.';
COMMENT ON COLUMN public.discovery_crm_customer_alias.source IS 'auto = seeded by script; manual = operator-corrected (protected from re-seed overwrite).';
COMMENT ON COLUMN public.discovery_crm_customer_alias.updated_at IS 'Timestamp of last modification (manual or auto).';
ALTER TABLE ONLY public.discovery_crm_customer_alias
    ADD CONSTRAINT discovery_crm_customer_alias_pkey PRIMARY KEY (crm_accountid);
CREATE INDEX idx_crm_alias_canonical ON public.discovery_crm_customer_alias USING btree (canonical_customer_key);
CREATE INDEX idx_crm_alias_netbox ON public.discovery_crm_customer_alias USING btree (netbox_musteri_value);
\unrestrict PmhqFeVo1Bbc75KFP19dIftHfaj7Me77azsAsJViQWDUttdsDatnAiwuXueDwMT
