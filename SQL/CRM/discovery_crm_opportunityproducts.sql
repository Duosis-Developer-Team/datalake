-- Dynamics 365 CRM Opportunity Products (line items) discovery table
-- data_type: crm_inventory_opportunityproduct
-- UPSERT key: opportunityproductid

CREATE TABLE IF NOT EXISTS discovery_crm_opportunityproducts (
    opportunityproductid    TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_opportunityproduct',
    opportunityid           TEXT,
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

CREATE INDEX IF NOT EXISTS idx_crm_opprod_opportunityid ON discovery_crm_opportunityproducts (opportunityid);
CREATE INDEX IF NOT EXISTS idx_crm_opprod_productid     ON discovery_crm_opportunityproducts (productid);

COMMENT ON TABLE  discovery_crm_opportunityproducts IS 'Dynamics 365 CRM opportunity line items (products). UPSERT on opportunityproductid.';
COMMENT ON COLUMN discovery_crm_opportunityproducts.opportunityproductid IS 'Primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_opportunityproducts.opportunityid        IS 'FK to discovery_crm_opportunities.';
COMMENT ON COLUMN discovery_crm_opportunityproducts.productid            IS 'FK to discovery_crm_products.';
COMMENT ON COLUMN discovery_crm_opportunityproducts.extendedamount       IS 'Total line amount (quantity × priceperunit − discounts).';
COMMENT ON COLUMN discovery_crm_opportunityproducts.collection_time      IS 'Timestamp of the discovery script run.';
