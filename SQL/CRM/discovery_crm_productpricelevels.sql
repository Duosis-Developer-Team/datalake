-- Dynamics 365 CRM Product Price Levels (unit price per product/price-list) discovery table
-- data_type: crm_inventory_productpricelevel
-- UPSERT key: productpricelevelid

CREATE TABLE IF NOT EXISTS discovery_crm_productpricelevels (
    productpricelevelid     TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_productpricelevel',
    pricelevelid            TEXT,
    pricelevel_name         TEXT,
    productid               TEXT,
    product_name            TEXT,
    uomid                   TEXT,
    uomid_name              TEXT,
    amount                  DOUBLE PRECISION,
    discounttypeid          TEXT,
    pricingmethodcode       BIGINT,
    pricingmethodcode_text  TEXT,
    transactioncurrencyid   TEXT,
    transactioncurrency_text TEXT,
    modifiedon              TIMESTAMPTZ,
    collection_time         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crm_ppl_productid    ON discovery_crm_productpricelevels (productid);
CREATE INDEX IF NOT EXISTS idx_crm_ppl_pricelevelid ON discovery_crm_productpricelevels (pricelevelid);
CREATE INDEX IF NOT EXISTS idx_crm_ppl_modifiedon   ON discovery_crm_productpricelevels (modifiedon);

COMMENT ON TABLE  discovery_crm_productpricelevels IS 'Per-product unit price within a price list. Key join table for catalog valuation. UPSERT on productpricelevelid.';
COMMENT ON COLUMN discovery_crm_productpricelevels.productpricelevelid IS 'CRM product-price-level GUID — primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_productpricelevels.pricelevelid        IS 'FK to discovery_crm_pricelevels.';
COMMENT ON COLUMN discovery_crm_productpricelevels.productid           IS 'FK to discovery_crm_products.';
COMMENT ON COLUMN discovery_crm_productpricelevels.amount              IS 'Unit price in transaction currency.';
COMMENT ON COLUMN discovery_crm_productpricelevels.uomid_name          IS 'Unit of measure name (Adet, GB, vCPU, etc.).';
COMMENT ON COLUMN discovery_crm_productpricelevels.collection_time     IS 'Timestamp of the discovery script run.';
