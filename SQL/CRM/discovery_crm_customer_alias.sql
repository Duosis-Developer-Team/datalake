-- CRM Customer Alias / Identity Resolution table
-- Maps CRM account IDs to canonical customer keys used across the platform.
-- Seeded automatically from discovery_crm_accounts; refined manually via GUI.

CREATE TABLE IF NOT EXISTS discovery_crm_customer_alias (
    crm_accountid           TEXT        PRIMARY KEY,
    crm_account_name        TEXT        NOT NULL,
    canonical_customer_key  TEXT,
    netbox_musteri_value    TEXT,
    notes                   TEXT,
    source                  TEXT        NOT NULL DEFAULT 'auto'
                            CHECK (source IN ('auto', 'manual')),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_crm_alias_canonical ON discovery_crm_customer_alias (canonical_customer_key);
CREATE INDEX IF NOT EXISTS idx_crm_alias_netbox    ON discovery_crm_customer_alias (netbox_musteri_value);

COMMENT ON TABLE  discovery_crm_customer_alias IS 'Identity resolution bridge: maps CRM account GUIDs to canonical platform customer keys and NetBox musteri values. Rows with source=auto are seeded by seed_customer_alias_from_accounts.sql; manually corrected rows set source=manual and survive re-seeding.';
COMMENT ON COLUMN discovery_crm_customer_alias.crm_accountid         IS 'CRM account GUID — primary key. FK to discovery_crm_accounts.accountid.';
COMMENT ON COLUMN discovery_crm_customer_alias.crm_account_name      IS 'Account name from CRM at seed time.';
COMMENT ON COLUMN discovery_crm_customer_alias.canonical_customer_key IS 'Platform canonical key used in GUI customer selector and all API filters.';
COMMENT ON COLUMN discovery_crm_customer_alias.netbox_musteri_value   IS 'Value matching discovery_netbox_virtualization_vm.custom_fields_musteri for VM ownership join.';
COMMENT ON COLUMN discovery_crm_customer_alias.notes                  IS 'Free-text operator notes on the mapping.';
COMMENT ON COLUMN discovery_crm_customer_alias.source                 IS 'auto = seeded by script; manual = operator-corrected (protected from re-seed overwrite).';
COMMENT ON COLUMN discovery_crm_customer_alias.updated_at             IS 'Timestamp of last modification (manual or auto).';
