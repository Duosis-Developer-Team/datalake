# Dynamics 365 CRM discovery collector

Python script `crm-dynamics-discovery.py` calls the Dynamics 365 Web API (OData v4) via OAuth2 client-credentials, paginates all pages following `@odata.nextLink`, normalizes records to **per-type sparse JSON** (only keys relevant to each `data_type`; `None` values dropped), and prints a **UTF-8 JSON array** on **stdout** for Apache NiFi `ExecuteStreamCommand` → `SplitJson` → `RouteOnAttribute` → `PutDatabaseRecord`.

Pattern: identical to [`ServiceCore/servicecore-discovery.py`](../../ServiceCore/servicecore-discovery.py).

## CLI parameters

All connection and tuning options are passed via `argparse` (kebab-case long options). There is **no** config file path — parameters are supplied by NiFi Parameter Context.

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--tenant-id` | ✓ | — | Azure AD / Entra ID tenant ID |
| `--client-id` | ✓ | — | App registration client ID |
| `--client-secret` | ✓ | — | Client secret (pass via NiFi Parameter Context) |
| `--crm-url` | ✓ | — | CRM base URL, e.g. `https://org.crm4.dynamics.com` |
| `--api-version` | | `v9.2` | Dynamics 365 Web API version |
| `--lookback-hours` | | `24` | Rolling window for `modifiedon` filter on transactional entities (UTC) |
| `--page-size` | | `5000` | OData `maxpagesize` preference header |
| `--http-timeout-sec` | | `60` | Per-request timeout (seconds) |
| `--http-retries` | | `3` | urllib3 retry count for 429 / 5xx responses |
| `--skip-accounts` | | off | Skip accounts (master data) — faster smoke tests |
| `--skip-catalog` | | off | Skip product catalog entities |
| `--skip-sales` | | off | Skip sales funnel entities |
| `--skip-contracts` | | off | Skip contract entities |
| `--full-snapshot` | | off | Ignore `lookback-hours`; fetch all records (initial backfill) |

**Security:** Never commit real secrets. Pass `--client-secret` via NiFi Parameter Context, HashiCorp Vault, or equivalent.

## Entities and incremental filters

### Master data — always full snapshot (no `modifiedon` filter)

| Entity | OData endpoint | `data_type` |
|--------|---------------|-------------|
| Accounts | `accounts` | `crm_inventory_account` |

### Product catalog — always full snapshot

| Entity | OData endpoint | `data_type` |
|--------|---------------|-------------|
| Products | `products` | `crm_inventory_product` |
| Price Lists | `pricelevels` | `crm_inventory_pricelevel` |
| Unit Prices | `productpricelevels` | `crm_inventory_productpricelevel` |

### Sales funnel — incremental (`$filter=modifiedon ge <UTC>`)

| Entity | OData endpoint | `data_type` |
|--------|---------------|-------------|
| Opportunities | `opportunities` | `crm_inventory_opportunity` |
| Opportunity Products | `opportunityproducts` | `crm_inventory_opportunityproduct` |
| Quotes | `quotes` | `crm_inventory_quote` |
| Quote Details | `quotedetails` | `crm_inventory_quotedetail` |
| Sales Orders | `salesorders` | `crm_inventory_salesorder` |
| Sales Order Details | `salesorderdetails` | `crm_inventory_salesorderdetail` |
| Invoices | `invoices` | `crm_inventory_invoice` |
| Invoice Details | `invoicedetails` | `crm_inventory_invoicedetail` |

### Contracts — incremental (`$filter=modifiedon ge <UTC>`)

| Entity | OData endpoint | `data_type` |
|--------|---------------|-------------|
| Contracts | `contracts` | `crm_inventory_contract` |
| Contract Details | `contractdetails` | `crm_inventory_contractdetail` |

## Output contract

Each element in the JSON array includes `data_type` and `collection_time`. Objects are **sparse**: only fields for that entity type appear; missing fields are `null` in the DB via NiFi PutDatabaseRecord.

| `data_type` | UPSERT key |
|-------------|-----------|
| `crm_inventory_account` | `accountid` |
| `crm_inventory_product` | `productid` |
| `crm_inventory_pricelevel` | `pricelevelid` |
| `crm_inventory_productpricelevel` | `productpricelevelid` |
| `crm_inventory_opportunity` | `opportunityid` |
| `crm_inventory_opportunityproduct` | `opportunityproductid` |
| `crm_inventory_quote` | `quoteid` |
| `crm_inventory_quotedetail` | `quotedetailid` |
| `crm_inventory_salesorder` | `salesorderid` |
| `crm_inventory_salesorderdetail` | `salesorderdetailid` |
| `crm_inventory_invoice` | `invoiceid` |
| `crm_inventory_invoicedetail` | `invoicedetailid` |
| `crm_inventory_contract` | `contractid` |
| `crm_inventory_contractdetail` | `contractdetailid` |

## PostgreSQL tables

DDL: `datalake/SQL/CRM/discovery_crm_*.sql` (one file per table, with `COMMENT ON TABLE/COLUMN`).

| Table | data_type |
|-------|-----------|
| `discovery_crm_accounts` | `crm_inventory_account` |
| `discovery_crm_products` | `crm_inventory_product` |
| `discovery_crm_pricelevels` | `crm_inventory_pricelevel` |
| `discovery_crm_productpricelevels` | `crm_inventory_productpricelevel` |
| `discovery_crm_opportunities` | `crm_inventory_opportunity` |
| `discovery_crm_opportunityproducts` | `crm_inventory_opportunityproduct` |
| `discovery_crm_quotes` | `crm_inventory_quote` |
| `discovery_crm_quotedetails` | `crm_inventory_quotedetail` |
| `discovery_crm_salesorders` | `crm_inventory_salesorder` |
| `discovery_crm_salesorderdetails` | `crm_inventory_salesorderdetail` |
| `discovery_crm_invoices` | `crm_inventory_invoice` |
| `discovery_crm_invoicedetails` | `crm_inventory_invoicedetail` |
| `discovery_crm_contracts` | `crm_inventory_contract` |
| `discovery_crm_contractdetails` | `crm_inventory_contractdetail` |
| `discovery_crm_customer_alias` | *(populated by `seed_customer_alias_from_accounts.sql`)* |

## Avro schema (NiFi JsonTreeReader)

Single unified schema:

- `SQL/json_schemas/CRM/crm-dynamics-discovery.json` — record name `CrmDynamicsDiscovery`

Use the **same** schema text across all 14 NiFi routes. Stdout JSON is a subset of keys per row; the schema defines the full column contract for NiFi type coercion and DB mapping.

## NiFi flow checklist

```
ExecuteStreamCommand
  Command: python3 /Datalake_Project/collectors/CRM/Dynamics365/crm-dynamics-discovery.py
  Arguments: --tenant-id ${crm.tenant.id}
             --client-id ${crm.client.id}
             --client-secret ${crm.client.secret}
             --crm-url ${crm.crm.url}
             --lookback-hours 24
             --page-size 5000

SplitJson
  JsonPath: $.*

EvaluateJsonPath
  data_type → ${data_type}

RouteOnAttribute  (14 routes):
  crm_inventory_account           → PutDatabaseRecord → discovery_crm_accounts            (Update Keys: accountid)
  crm_inventory_product           → PutDatabaseRecord → discovery_crm_products            (Update Keys: productid)
  crm_inventory_pricelevel        → PutDatabaseRecord → discovery_crm_pricelevels         (Update Keys: pricelevelid)
  crm_inventory_productpricelevel → PutDatabaseRecord → discovery_crm_productpricelevels  (Update Keys: productpricelevelid)
  crm_inventory_opportunity       → PutDatabaseRecord → discovery_crm_opportunities       (Update Keys: opportunityid)
  crm_inventory_opportunityproduct → PutDatabaseRecord → discovery_crm_opportunityproducts (Update Keys: opportunityproductid)
  crm_inventory_quote             → PutDatabaseRecord → discovery_crm_quotes              (Update Keys: quoteid)
  crm_inventory_quotedetail       → PutDatabaseRecord → discovery_crm_quotedetails        (Update Keys: quotedetailid)
  crm_inventory_salesorder        → PutDatabaseRecord → discovery_crm_salesorders         (Update Keys: salesorderid)
  crm_inventory_salesorderdetail  → PutDatabaseRecord → discovery_crm_salesorderdetails   (Update Keys: salesorderdetailid)
  crm_inventory_invoice           → PutDatabaseRecord → discovery_crm_invoices            (Update Keys: invoiceid)
  crm_inventory_invoicedetail     → PutDatabaseRecord → discovery_crm_invoicedetails      (Update Keys: invoicedetailid)
  crm_inventory_contract          → PutDatabaseRecord → discovery_crm_contracts           (Update Keys: contractid)
  crm_inventory_contractdetail    → PutDatabaseRecord → discovery_crm_contractdetails     (Update Keys: contractdetailid)

PutDatabaseRecord (all routes):
  Statement Type: UPSERT
  Record Reader:  JsonTreeReader (Schema Access Strategy: Use 'Schema Text' Property)
  Schema Text:    <content of SQL/json_schemas/CRM/crm-dynamics-discovery.json>
```

Cron (suggested): every 30 minutes — `0 0/30 * * * ?`

For initial backfill (all records regardless of modifiedon):
```
... --full-snapshot
```

For catalog-only refresh (products and prices, no transactional data):
```
... --skip-accounts --skip-sales --skip-contracts --full-snapshot
```

## Customer identity resolution

CRM `accountid` ↔ platform canonical customer key mapping is maintained in `discovery_crm_customer_alias`. See:
- DDL: `SQL/CRM/discovery_crm_customer_alias.sql`
- Seed script: `SQL/CRM/seed_customer_alias_from_accounts.sql`
- ADR: `datalake-platform-knowledge-base/adrs/ADR-0008-crm-customer-identity-resolution.md`

## Manual test

```bash
python3 crm-dynamics-discovery.py \
  --tenant-id "<TENANT_ID>" \
  --client-id "<CLIENT_ID>" \
  --client-secret "<SECRET>" \
  --crm-url "https://<org>.crm4.dynamics.com" \
  --lookback-hours 24 \
  --skip-sales \
  --skip-contracts \
  | python3 -m json.tool | head -50
```

## Unit tests

```bash
cd datalake/collectors/CRM/Dynamics365
python3 -m pytest test_crm_dynamics_discovery.py -v
```

43 tests + 14 subtests covering all normalizers, OData helpers, pagination mock, error handling, and real fixture files.

## References

- [Collector & discovery template](../../docs/development-templates/collector_discovery_template.md)
- [Compliance checklist](../../docs/development-templates/collector_discovery_checklist.md)
- Knowledge base: `datalake-platform-knowledge-base/wiki/datalake-collectors/CRM-Dynamics365.md`
- Reference implementation: [`../../ServiceCore/servicecore-discovery.py`](../../ServiceCore/servicecore-discovery.py)
