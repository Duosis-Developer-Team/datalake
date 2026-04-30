-- Migration: drop CRM discovery tables for entities outside collector scope
-- (invoices, contracts, opportunities, quotes). Safe to re-run (IF EXISTS).
-- Related: ADR-0010, crm-dynamics-discovery.py (6 entities only).

BEGIN;

DROP TABLE IF EXISTS discovery_crm_invoicedetails CASCADE;
DROP TABLE IF EXISTS discovery_crm_invoices CASCADE;

DROP TABLE IF EXISTS discovery_crm_contractdetails CASCADE;
DROP TABLE IF EXISTS discovery_crm_contracts CASCADE;

DROP TABLE IF EXISTS discovery_crm_opportunityproducts CASCADE;
DROP TABLE IF EXISTS discovery_crm_opportunities CASCADE;

DROP TABLE IF EXISTS discovery_crm_quotedetails CASCADE;
DROP TABLE IF EXISTS discovery_crm_quotes CASCADE;

COMMIT;
