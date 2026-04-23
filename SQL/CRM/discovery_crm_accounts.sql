-- Dynamics 365 CRM Accounts discovery table
-- data_type: crm_inventory_account
-- UPSERT key: accountid
-- Source script: collectors/CRM/Dynamics365/crm-dynamics-discovery.py

CREATE TABLE IF NOT EXISTS discovery_crm_accounts (
    accountid               TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_account',
    name                    TEXT,
    accountnumber           TEXT,
    customertypecode_value  BIGINT,
    customertypecode_text   TEXT,
    parentaccountid         TEXT,
    parentaccount_name      TEXT,
    primarycontactid        TEXT,
    primarycontact_name     TEXT,
    ownerid                 TEXT,
    owner_name              TEXT,
    statecode               BIGINT,
    statecode_text          TEXT,
    statuscode              BIGINT,
    statuscode_text         TEXT,
    telephone1              TEXT,
    address1_line1          TEXT,
    address1_city           TEXT,
    address1_country        TEXT,
    industrycode            BIGINT,
    industrycode_text       TEXT,
    revenue                 DOUBLE PRECISION,
    numberofemployees       BIGINT,
    transactioncurrencyid   TEXT,
    transactioncurrency_text TEXT,
    exchangerate            DOUBLE PRECISION,
    createdon               TIMESTAMPTZ,
    modifiedon              TIMESTAMPTZ,
    collection_time         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crm_accounts_name        ON discovery_crm_accounts (name);
CREATE INDEX IF NOT EXISTS idx_crm_accounts_modifiedon  ON discovery_crm_accounts (modifiedon);
CREATE INDEX IF NOT EXISTS idx_crm_accounts_collection  ON discovery_crm_accounts (collection_time);

COMMENT ON TABLE  discovery_crm_accounts IS 'Dynamics 365 CRM account (customer) master records. UPSERT on accountid.';
COMMENT ON COLUMN discovery_crm_accounts.accountid               IS 'CRM account GUID — primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_accounts.name                    IS 'Account display name (company/customer name).';
COMMENT ON COLUMN discovery_crm_accounts.accountnumber           IS 'Unique account number assigned in CRM.';
COMMENT ON COLUMN discovery_crm_accounts.customertypecode_value  IS 'Customer type option set value.';
COMMENT ON COLUMN discovery_crm_accounts.customertypecode_text   IS 'Customer type option set label.';
COMMENT ON COLUMN discovery_crm_accounts.statecode               IS 'Account state (0=Active, 1=Inactive).';
COMMENT ON COLUMN discovery_crm_accounts.revenue                 IS 'Annual revenue in transaction currency.';
COMMENT ON COLUMN discovery_crm_accounts.transactioncurrencyid   IS 'FK to transactioncurrency entity.';
COMMENT ON COLUMN discovery_crm_accounts.modifiedon              IS 'Last modification timestamp from CRM.';
COMMENT ON COLUMN discovery_crm_accounts.collection_time         IS 'Timestamp of the discovery script run that produced this record.';
