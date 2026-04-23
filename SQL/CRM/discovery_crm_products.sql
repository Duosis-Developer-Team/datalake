-- Dynamics 365 CRM Products discovery table
-- data_type: crm_inventory_product
-- UPSERT key: productid

CREATE TABLE IF NOT EXISTS discovery_crm_products (
    productid               TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_product',
    name                    TEXT,
    productnumber           TEXT,
    statecode               BIGINT,
    statecode_text          TEXT,
    statuscode              BIGINT,
    statuscode_text         TEXT,
    defaultuomid            TEXT,
    defaultuomid_name       TEXT,
    currentcost             DOUBLE PRECISION,
    standardcost            DOUBLE PRECISION,
    pricelevelid            TEXT,
    pricelevel_name         TEXT,
    blt_productgroup        BIGINT,
    blt_productgroup_text   TEXT,
    blt_productmodel        BIGINT,
    blt_productmodel_text   TEXT,
    blt_sectionorder        BIGINT,
    createdon               TIMESTAMPTZ,
    modifiedon              TIMESTAMPTZ,
    collection_time         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crm_products_name       ON discovery_crm_products (name);
CREATE INDEX IF NOT EXISTS idx_crm_products_modifiedon ON discovery_crm_products (modifiedon);

COMMENT ON TABLE  discovery_crm_products IS 'Dynamics 365 CRM product catalog entries. UPSERT on productid.';
COMMENT ON COLUMN discovery_crm_products.productid      IS 'CRM product GUID — primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_products.productnumber  IS 'Internal product SKU/number.';
COMMENT ON COLUMN discovery_crm_products.standardcost   IS 'Standard cost in base currency.';
COMMENT ON COLUMN discovery_crm_products.blt_productgroup_text IS 'Custom product group label (Bulutistan extension).';
COMMENT ON COLUMN discovery_crm_products.blt_productmodel_text IS 'Custom product model label (Bulutistan extension).';
COMMENT ON COLUMN discovery_crm_products.collection_time IS 'Timestamp of the discovery script run.';
