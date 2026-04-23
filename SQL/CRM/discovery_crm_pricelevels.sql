-- Dynamics 365 CRM Price Lists (Price Levels) discovery table
-- data_type: crm_inventory_pricelevel
-- UPSERT key: pricelevelid

CREATE TABLE IF NOT EXISTS discovery_crm_pricelevels (
    pricelevelid            TEXT        PRIMARY KEY,
    data_type               TEXT        NOT NULL DEFAULT 'crm_inventory_pricelevel',
    name                    TEXT,
    transactioncurrencyid   TEXT,
    transactioncurrency_text TEXT,
    exchangerate            DOUBLE PRECISION,
    begindate               DATE,
    enddate                 DATE,
    statecode               BIGINT,
    statecode_text          TEXT,
    createdon               TIMESTAMPTZ,
    modifiedon              TIMESTAMPTZ,
    collection_time         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crm_pricelevels_name       ON discovery_crm_pricelevels (name);
CREATE INDEX IF NOT EXISTS idx_crm_pricelevels_modifiedon ON discovery_crm_pricelevels (modifiedon);

COMMENT ON TABLE  discovery_crm_pricelevels IS 'Dynamics 365 CRM price lists (pricelevels). UPSERT on pricelevelid.';
COMMENT ON COLUMN discovery_crm_pricelevels.pricelevelid IS 'CRM price level GUID — primary key and UPSERT key.';
COMMENT ON COLUMN discovery_crm_pricelevels.name         IS 'Price list name (e.g. TL Fiyat Listesi, USD Fiyat Listesi).';
COMMENT ON COLUMN discovery_crm_pricelevels.exchangerate IS 'Exchange rate relative to base currency at time of last modification.';
COMMENT ON COLUMN discovery_crm_pricelevels.collection_time IS 'Timestamp of the discovery script run.';
