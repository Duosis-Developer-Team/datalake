-- Dynamics 365 CRM Invoices discovery table
-- data_type: crm_inventory_invoice
-- UPSERT key: invoiceid

CREATE TABLE IF NOT EXISTS discovery_crm_invoices (
    invoiceid               TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_invoice',
    name                    TEXT,
    invoicenumber           TEXT,
    customerid              TEXT,
    customerid_name         TEXT,
    salesorderid            TEXT,
    opportunityid           TEXT,
    ownerid                 TEXT,
    owner_name              TEXT,
    totalamount             DOUBLE PRECISION,
    totaltax                DOUBLE PRECISION,
    totallineitemamount     DOUBLE PRECISION,
    invoicedate             DATE,
    duedate                 DATE,
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

CREATE INDEX IF NOT EXISTS idx_crm_inv_customerid  ON discovery_crm_invoices (customerid);
CREATE INDEX IF NOT EXISTS idx_crm_inv_invoicedate ON discovery_crm_invoices (invoicedate);
CREATE INDEX IF NOT EXISTS idx_crm_inv_statecode   ON discovery_crm_invoices (statecode);
CREATE INDEX IF NOT EXISTS idx_crm_inv_modifiedon  ON discovery_crm_invoices (modifiedon);

COMMENT ON TABLE  discovery_crm_invoices IS 'Dynamics 365 CRM invoices — primary revenue recognition source. UPSERT on invoiceid.';
COMMENT ON COLUMN discovery_crm_invoices.invoiceid      IS 'CRM invoice GUID — primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_invoices.customerid     IS 'FK account GUID. JOIN with discovery_crm_customer_alias for canonical customer key.';
COMMENT ON COLUMN discovery_crm_invoices.totalamount    IS 'Invoice total including taxes.';
COMMENT ON COLUMN discovery_crm_invoices.statecode      IS 'Invoice state (0=Active, 1=Closed, 2=Cancelled, 3=Paid).';
COMMENT ON COLUMN discovery_crm_invoices.invoicedate    IS 'Invoice date (billing date).';
COMMENT ON COLUMN discovery_crm_invoices.collection_time IS 'Timestamp of the discovery script run.';
