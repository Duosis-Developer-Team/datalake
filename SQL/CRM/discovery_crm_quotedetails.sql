-- Dynamics 365 CRM Quote Details (line items) discovery table
-- data_type: crm_inventory_quotedetail
-- UPSERT key: quotedetailid

CREATE TABLE IF NOT EXISTS discovery_crm_quotedetails (
    quotedetailid           TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_quotedetail',
    quoteid                 TEXT,
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

CREATE INDEX IF NOT EXISTS idx_crm_qd_quoteid   ON discovery_crm_quotedetails (quoteid);
CREATE INDEX IF NOT EXISTS idx_crm_qd_productid ON discovery_crm_quotedetails (productid);

COMMENT ON TABLE  discovery_crm_quotedetails IS 'Dynamics 365 CRM quote line items. UPSERT on quotedetailid.';
COMMENT ON COLUMN discovery_crm_quotedetails.quotedetailid IS 'Primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_quotedetails.quoteid       IS 'FK to discovery_crm_quotes.';
COMMENT ON COLUMN discovery_crm_quotedetails.productid     IS 'FK to discovery_crm_products.';
COMMENT ON COLUMN discovery_crm_quotedetails.collection_time IS 'Timestamp of the discovery script run.';
