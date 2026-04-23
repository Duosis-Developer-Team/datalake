-- Dynamics 365 CRM Quotes discovery table
-- data_type: crm_inventory_quote
-- UPSERT key: quoteid

CREATE TABLE IF NOT EXISTS discovery_crm_quotes (
    quoteid                 TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_quote',
    name                    TEXT,
    quotenumber             TEXT,
    customerid              TEXT,
    customerid_name         TEXT,
    opportunityid           TEXT,
    ownerid                 TEXT,
    owner_name              TEXT,
    totalamount             DOUBLE PRECISION,
    totaltax                DOUBLE PRECISION,
    totallineitemamount     DOUBLE PRECISION,
    effectivefrom           DATE,
    effectiveto             DATE,
    statecode               BIGINT,
    statecode_text          TEXT,
    statuscode              BIGINT,
    statuscode_text         TEXT,
    pricelevelid            TEXT,
    pricelevel_name         TEXT,
    transactioncurrencyid   TEXT,
    transactioncurrency_text TEXT,
    createdon               TIMESTAMPTZ,
    modifiedon              TIMESTAMPTZ,
    collection_time         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crm_quotes_customerid ON discovery_crm_quotes (customerid);
CREATE INDEX IF NOT EXISTS idx_crm_quotes_modifiedon ON discovery_crm_quotes (modifiedon);

COMMENT ON TABLE  discovery_crm_quotes IS 'Dynamics 365 CRM quotes. UPSERT on quoteid.';
COMMENT ON COLUMN discovery_crm_quotes.quoteid      IS 'CRM quote GUID — primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_quotes.customerid   IS 'FK account GUID.';
COMMENT ON COLUMN discovery_crm_quotes.opportunityid IS 'FK to parent opportunity.';
COMMENT ON COLUMN discovery_crm_quotes.totalamount  IS 'Total quote amount including tax.';
COMMENT ON COLUMN discovery_crm_quotes.collection_time IS 'Timestamp of the discovery script run.';
