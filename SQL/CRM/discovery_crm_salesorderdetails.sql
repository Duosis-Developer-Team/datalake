-- Dynamics 365 CRM Sales Order Details (line items) discovery table
-- data_type: crm_inventory_salesorderdetail
-- UPSERT key: salesorderdetailid

CREATE TABLE IF NOT EXISTS discovery_crm_salesorderdetails (
    salesorderdetailid      TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_salesorderdetail',
    salesorderid            TEXT,
    productid               TEXT,
    product_name            TEXT,
    productdescription      TEXT,
    uomid                   TEXT,
    uomid_name              TEXT,
    quantity                DOUBLE PRECISION,
    priceperunit            DOUBLE PRECISION,
    baseamount              DOUBLE PRECISION,
    extendedamount          DOUBLE PRECISION,
    manualdiscountamount    DOUBLE PRECISION,
    transactioncurrencyid   TEXT,
    transactioncurrency_text TEXT,
    modifiedon              TIMESTAMPTZ,
    collection_time         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crm_sod_salesorderid ON discovery_crm_salesorderdetails (salesorderid);
CREATE INDEX IF NOT EXISTS idx_crm_sod_productid    ON discovery_crm_salesorderdetails (productid);

COMMENT ON TABLE  discovery_crm_salesorderdetails IS 'Dynamics 365 CRM sales order line items. UPSERT on salesorderdetailid.';
COMMENT ON COLUMN discovery_crm_salesorderdetails.salesorderdetailid IS 'Primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_salesorderdetails.salesorderid       IS 'FK to discovery_crm_salesorders.';
COMMENT ON COLUMN discovery_crm_salesorderdetails.productid          IS 'FK to discovery_crm_products.';
COMMENT ON COLUMN discovery_crm_salesorderdetails.extendedamount     IS 'Total line amount.';
COMMENT ON COLUMN discovery_crm_salesorderdetails.collection_time    IS 'Timestamp of the discovery script run.';
