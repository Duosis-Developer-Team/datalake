\restrict UzNRFfLfIURLm4glliMyyRbg7uL9VQ4IsDHwYYpvwVvkkPwYUF93W3DuvesZoXr
CREATE TABLE public.discovery_crm_accounts (
    accountid text NOT NULL,
    data_type text DEFAULT 'crm_inventory_account'::text NOT NULL,
    name text,
    accountnumber text,
    customertypecode_value bigint,
    customertypecode_text text,
    parentaccountid text,
    parentaccount_name text,
    primarycontactid text,
    primarycontact_name text,
    ownerid text,
    owner_name text,
    statecode bigint,
    statecode_text text,
    statuscode bigint,
    statuscode_text text,
    telephone1 text,
    address1_line1 text,
    address1_city text,
    address1_country text,
    industrycode bigint,
    industrycode_text text,
    revenue double precision,
    numberofemployees bigint,
    transactioncurrencyid text,
    transactioncurrency_text text,
    exchangerate double precision,
    createdon timestamp with time zone,
    modifiedon timestamp with time zone,
    collection_time timestamp with time zone
);
COMMENT ON TABLE public.discovery_crm_accounts IS 'Dynamics 365 CRM account (customer) master records. UPSERT on accountid.';
COMMENT ON COLUMN public.discovery_crm_accounts.accountid IS 'CRM account GUID — primary key and UPSERT key.';
COMMENT ON COLUMN public.discovery_crm_accounts.name IS 'Account display name (company/customer name).';
COMMENT ON COLUMN public.discovery_crm_accounts.accountnumber IS 'Unique account number assigned in CRM.';
COMMENT ON COLUMN public.discovery_crm_accounts.customertypecode_value IS 'Customer type option set value.';
COMMENT ON COLUMN public.discovery_crm_accounts.customertypecode_text IS 'Customer type option set label.';
COMMENT ON COLUMN public.discovery_crm_accounts.statecode IS 'Account state (0=Active, 1=Inactive).';
COMMENT ON COLUMN public.discovery_crm_accounts.revenue IS 'Annual revenue in transaction currency.';
COMMENT ON COLUMN public.discovery_crm_accounts.transactioncurrencyid IS 'FK to transactioncurrency entity.';
COMMENT ON COLUMN public.discovery_crm_accounts.modifiedon IS 'Last modification timestamp from CRM.';
COMMENT ON COLUMN public.discovery_crm_accounts.collection_time IS 'Timestamp of the discovery script run that produced this record.';
ALTER TABLE ONLY public.discovery_crm_accounts
    ADD CONSTRAINT discovery_crm_accounts_pkey PRIMARY KEY (accountid);
CREATE INDEX idx_crm_accounts_collection ON public.discovery_crm_accounts USING btree (collection_time);
CREATE INDEX idx_crm_accounts_modifiedon ON public.discovery_crm_accounts USING btree (modifiedon);
CREATE INDEX idx_crm_accounts_name ON public.discovery_crm_accounts USING btree (name);
\unrestrict UzNRFfLfIURLm4glliMyyRbg7uL9VQ4IsDHwYYpvwVvkkPwYUF93W3DuvesZoXr
