-- Seed discovery_crm_customer_alias from discovery_crm_accounts.
--
-- Strategy: normalize account name (lower-case, trim, collapse whitespace) and
-- attempt a best-effort match to the platform canonical customer key.
-- Rows with source = 'manual' are protected and never overwritten by this script.
--
-- Step 1: run this script after the first accounts discovery to populate auto rows.
-- Step 2: operators correct unmatched rows in the GUI (Settings → Customer Alias)
--         or by running UPDATE statements with source = 'manual'.
--
-- Usage (run once after initial backfill):
--   psql -d datalake -f seed_customer_alias_from_accounts.sql
--
-- Repeat runs are safe: existing manual rows are untouched; auto rows are UPSERT-ed.

-- Insert or update auto rows from accounts snapshot.
-- canonical_customer_key is seeded as the account name itself;
-- operators refine this to match the exact string used in GUI customer selectors.

INSERT INTO discovery_crm_customer_alias (
    crm_accountid,
    crm_account_name,
    canonical_customer_key,
    netbox_musteri_value,
    source,
    created_at,
    updated_at
)
SELECT
    a.accountid                                          AS crm_accountid,
    a.name                                               AS crm_account_name,
    -- Canonical key: exact account name (refine manually if it differs from GUI selector)
    a.name                                               AS canonical_customer_key,
    -- Best-effort NetBox musteri match: normalize both sides (lower, trim, collapse spaces)
    -- Returns the NetBox value when found; NULL otherwise — operator must fill manually.
    (
        SELECT vm.custom_fields_musteri
        FROM   discovery_netbox_virtualization_vm vm
        WHERE  lower(trim(regexp_replace(vm.custom_fields_musteri, '\s+', ' ', 'g')))
               = lower(trim(regexp_replace(a.name, '\s+', ' ', 'g')))
        LIMIT  1
    )                                                    AS netbox_musteri_value,
    'auto'                                               AS source,
    now()                                                AS created_at,
    now()                                                AS updated_at
FROM discovery_crm_accounts a
WHERE a.statecode = 0  -- Active accounts only
ON CONFLICT (crm_accountid) DO UPDATE
    SET
        crm_account_name       = EXCLUDED.crm_account_name,
        canonical_customer_key = CASE
            WHEN discovery_crm_customer_alias.source = 'manual' THEN discovery_crm_customer_alias.canonical_customer_key
            ELSE EXCLUDED.canonical_customer_key
        END,
        netbox_musteri_value   = CASE
            WHEN discovery_crm_customer_alias.source = 'manual' THEN discovery_crm_customer_alias.netbox_musteri_value
            ELSE EXCLUDED.netbox_musteri_value
        END,
        updated_at             = now()
    WHERE discovery_crm_customer_alias.source = 'auto';

-- Report unmatched rows for operator review
SELECT
    crm_accountid,
    crm_account_name,
    canonical_customer_key,
    netbox_musteri_value,
    source
FROM discovery_crm_customer_alias
WHERE netbox_musteri_value IS NULL
  AND source = 'auto'
ORDER BY crm_account_name;
