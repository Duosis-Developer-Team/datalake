-- Dynamics 365 CRM Opportunities discovery table
-- data_type: crm_inventory_opportunity
-- UPSERT key: opportunityid

CREATE TABLE IF NOT EXISTS discovery_crm_opportunities (
    opportunityid           TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_opportunity',
    name                    TEXT,
    customerid              TEXT,
    customerid_name         TEXT,
    ownerid                 TEXT,
    owner_name              TEXT,
    estimatedvalue          DOUBLE PRECISION,
    actualvalue             DOUBLE PRECISION,
    closeprobability        BIGINT,
    estimatedclosedate      DATE,
    actualclosedate         DATE,
    statecode               BIGINT,
    statecode_text          TEXT,
    statuscode              BIGINT,
    statuscode_text         TEXT,
    salesstagecode          BIGINT,
    salesstagecode_text     TEXT,
    pricelevelid            TEXT,
    pricelevel_name         TEXT,
    transactioncurrencyid   TEXT,
    transactioncurrency_text TEXT,
    totalamount             DOUBLE PRECISION,
    totaltax                DOUBLE PRECISION,
    totallineitemamount     DOUBLE PRECISION,
    createdon               TIMESTAMPTZ,
    modifiedon              TIMESTAMPTZ,
    collection_time         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crm_opp_customerid  ON discovery_crm_opportunities (customerid);
CREATE INDEX IF NOT EXISTS idx_crm_opp_statecode   ON discovery_crm_opportunities (statecode);
CREATE INDEX IF NOT EXISTS idx_crm_opp_modifiedon  ON discovery_crm_opportunities (modifiedon);

COMMENT ON TABLE  discovery_crm_opportunities IS 'Dynamics 365 CRM sales opportunities. UPSERT on opportunityid.';
COMMENT ON COLUMN discovery_crm_opportunities.opportunityid      IS 'CRM opportunity GUID — primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_opportunities.customerid         IS 'FK account GUID (customer).';
COMMENT ON COLUMN discovery_crm_opportunities.customerid_name    IS 'Customer account name.';
COMMENT ON COLUMN discovery_crm_opportunities.estimatedvalue     IS 'Estimated revenue in transaction currency.';
COMMENT ON COLUMN discovery_crm_opportunities.actualvalue        IS 'Actual closed revenue.';
COMMENT ON COLUMN discovery_crm_opportunities.closeprobability   IS 'Win probability percentage (0-100).';
COMMENT ON COLUMN discovery_crm_opportunities.salesstagecode_text IS 'Sales stage label (Qualify / Develop / Propose / Close).';
COMMENT ON COLUMN discovery_crm_opportunities.collection_time    IS 'Timestamp of the discovery script run.';
