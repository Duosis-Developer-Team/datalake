-- Dynamics 365 CRM Contract Details (line items) discovery table
-- data_type: crm_inventory_contractdetail
-- UPSERT key: contractdetailid

CREATE TABLE IF NOT EXISTS discovery_crm_contractdetails (
    contractdetailid        TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_contractdetail',
    contractid              TEXT,
    productid               TEXT,
    product_name            TEXT,
    productdescription      TEXT,
    uomid                   TEXT,
    uomid_name              TEXT,
    quantity                DOUBLE PRECISION,
    price                   DOUBLE PRECISION,
    totalprice              DOUBLE PRECISION,
    discount                DOUBLE PRECISION,
    activeon                DATE,
    expireson               DATE,
    transactioncurrencyid   TEXT,
    transactioncurrency_text TEXT,
    modifiedon              TIMESTAMPTZ,
    collection_time         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crm_ctrd_contractid ON discovery_crm_contractdetails (contractid);
CREATE INDEX IF NOT EXISTS idx_crm_ctrd_productid  ON discovery_crm_contractdetails (productid);

COMMENT ON TABLE  discovery_crm_contractdetails IS 'Dynamics 365 CRM contract line items. UPSERT on contractdetailid.';
COMMENT ON COLUMN discovery_crm_contractdetails.contractdetailid IS 'Primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_contractdetails.contractid       IS 'FK to discovery_crm_contracts.';
COMMENT ON COLUMN discovery_crm_contractdetails.productid        IS 'FK to discovery_crm_products.';
COMMENT ON COLUMN discovery_crm_contractdetails.price            IS 'Unit price per line item.';
COMMENT ON COLUMN discovery_crm_contractdetails.totalprice       IS 'Total price for this line item.';
COMMENT ON COLUMN discovery_crm_contractdetails.collection_time  IS 'Timestamp of the discovery script run.';
