-- Dynamics 365 CRM Sales Orders discovery table
-- data_type: crm_inventory_salesorder
-- UPSERT key: salesorderid

CREATE TABLE IF NOT EXISTS discovery_crm_salesorders (
    salesorderid            TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_salesorder',
    name                    TEXT,
    ordernumber             TEXT,
    customerid              TEXT,
    customerid_name         TEXT,
    opportunityid           TEXT,
    quoteid                 TEXT,
    ownerid                 TEXT,
    owner_name              TEXT,
    totalamount             DOUBLE PRECISION,
    totaltax                DOUBLE PRECISION,
    totallineitemamount     DOUBLE PRECISION,
    submitdate              DATE,
    fulfilldate             DATE,
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

CREATE INDEX IF NOT EXISTS idx_crm_so_customerid ON discovery_crm_salesorders (customerid);
CREATE INDEX IF NOT EXISTS idx_crm_so_statecode  ON discovery_crm_salesorders (statecode);
CREATE INDEX IF NOT EXISTS idx_crm_so_modifiedon ON discovery_crm_salesorders (modifiedon);

COMMENT ON TABLE  discovery_crm_salesorders IS 'Dynamics 365 CRM sales orders. UPSERT on salesorderid.';
COMMENT ON COLUMN discovery_crm_salesorders.salesorderid IS 'CRM sales order GUID — primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_salesorders.customerid   IS 'FK account GUID.';
COMMENT ON COLUMN discovery_crm_salesorders.statecode    IS 'Order state (0=Active, 1=Submitted, 2=Cancelled, 3=Fulfilled, 4=Invoiced).';
COMMENT ON COLUMN discovery_crm_salesorders.collection_time IS 'Timestamp of the discovery script run.';
