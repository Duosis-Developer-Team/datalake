-- Move GUI configuration out of the datalake DB.
-- Datalake DB now keeps only raw CRM data (discovery_crm_*).
-- gui_crm_* tables and v_gui_crm_product_mapping live in the new webui-db
-- (Docker service "webui-db", database "bulutwebui").
--
-- Operator checklist:
--   1. Confirm webui-db is reachable and migrations 001..003 ran.
--   2. Optionally export current overrides:
--        psql -h <datalake_host> -d bulutlake -c "\copy gui_crm_service_mapping_override TO 'override.csv' CSV HEADER"
--      then \copy them into webui-db before dropping below.
--   3. Run this migration. Application-layer joins replace the cross-DB view.
--
-- This migration is idempotent: each DROP uses IF EXISTS.

BEGIN;

DROP VIEW  IF EXISTS v_gui_crm_product_mapping CASCADE;
DROP TABLE IF EXISTS gui_crm_service_mapping_override CASCADE;
DROP TABLE IF EXISTS gui_crm_service_mapping_seed CASCADE;
DROP TABLE IF EXISTS gui_crm_service_pages CASCADE;

-- discovery_crm_customer_alias kept in datalake DB schema for backward compatibility,
-- but the canonical alias source is now gui_crm_customer_alias in webui-db.
-- Comment kept here intentionally.

COMMIT;
