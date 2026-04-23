-- Dynamics 365 CRM Contracts discovery table
-- data_type: crm_inventory_contract
-- UPSERT key: contractid

CREATE TABLE IF NOT EXISTS discovery_crm_contracts (
    contractid              TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_contract',
    title                   TEXT,
    contractnumber          TEXT,
    customerid              TEXT,
    customerid_name         TEXT,
    ownerid                 TEXT,
    owner_name              TEXT,
    activeon                DATE,
    expireson               DATE,
    billingfrequencycode    BIGINT,
    billingfrequencycode_text TEXT,
    totalprice              DOUBLE PRECISION,
    totallineitemdiscount   DOUBLE PRECISION,
    statecode               BIGINT,
    statecode_text          TEXT,
    statuscode              BIGINT,
    statuscode_text         TEXT,
    transactioncurrencyid   TEXT,
    transactioncurrency_text TEXT,
    createdon               TIMESTAMPTZ,
    modifiedon              TIMESTAMPTZ,
    collection_time         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crm_ctr_customerid ON discovery_crm_contracts (customerid);
CREATE INDEX IF NOT EXISTS idx_crm_ctr_statecode  ON discovery_crm_contracts (statecode);
CREATE INDEX IF NOT EXISTS idx_crm_ctr_expireson  ON discovery_crm_contracts (expireson);

COMMENT ON TABLE  discovery_crm_contracts IS 'Dynamics 365 CRM service contracts. Used for MRR/ARR calculation. UPSERT on contractid.';
COMMENT ON COLUMN discovery_crm_contracts.contractid   IS 'CRM contract GUID — primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_contracts.customerid   IS 'FK account GUID.';
COMMENT ON COLUMN discovery_crm_contracts.totalprice   IS 'Total contract value in transaction currency.';
COMMENT ON COLUMN discovery_crm_contracts.billingfrequencycode_text IS 'Billing cycle label (Monthly, Quarterly, etc.).';
COMMENT ON COLUMN discovery_crm_contracts.activeon     IS 'Contract start date.';
COMMENT ON COLUMN discovery_crm_contracts.expireson    IS 'Contract end/expiry date.';
COMMENT ON COLUMN discovery_crm_contracts.collection_time IS 'Timestamp of the discovery script run.';
