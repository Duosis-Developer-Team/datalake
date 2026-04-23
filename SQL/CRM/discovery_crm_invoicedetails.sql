-- Dynamics 365 CRM Invoice Details (line items) discovery table
-- data_type: crm_inventory_invoicedetail
-- UPSERT key: invoicedetailid

CREATE TABLE IF NOT EXISTS discovery_crm_invoicedetails (
    invoicedetailid         TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_invoicedetail',
    invoiceid               TEXT,
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

CREATE INDEX IF NOT EXISTS idx_crm_invd_invoiceid ON discovery_crm_invoicedetails (invoiceid);
CREATE INDEX IF NOT EXISTS idx_crm_invd_productid ON discovery_crm_invoicedetails (productid);

COMMENT ON TABLE  discovery_crm_invoicedetails IS 'Dynamics 365 CRM invoice line items. Key for product-level billing analysis. UPSERT on invoicedetailid.';
COMMENT ON COLUMN discovery_crm_invoicedetails.invoicedetailid IS 'Primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_invoicedetails.invoiceid       IS 'FK to discovery_crm_invoices.';
COMMENT ON COLUMN discovery_crm_invoicedetails.productid       IS 'FK to discovery_crm_products. Use with discovery_crm_productpricelevels for catalog valuation.';
COMMENT ON COLUMN discovery_crm_invoicedetails.uomid_name      IS 'Unit of measure (Adet, GB, vCPU, etc.) — key for capacity utilisation mapping.';
COMMENT ON COLUMN discovery_crm_invoicedetails.quantity        IS 'Billed quantity in unit of measure.';
COMMENT ON COLUMN discovery_crm_invoicedetails.extendedamount  IS 'Total line billing amount.';
COMMENT ON COLUMN discovery_crm_invoicedetails.collection_time IS 'Timestamp of the discovery script run.';
