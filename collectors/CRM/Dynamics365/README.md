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
| `--lookback-hours` | | `24` | Rolling window for `modifiedon` on realized salesorders (UTC) |
| `--page-size` | | `5000` | OData `maxpagesize` preference header |
| `--http-timeout-sec` | | `60` | Per-request timeout (seconds) |
| `--http-retries` | | `3` | urllib3 retry count for 429 / 5xx responses |
| `--skip-accounts` | | off | Skip accounts (master data) — faster smoke tests |
| `--skip-catalog` | | off | Skip product catalog entities |
| `--skip-sales` | | off | Skip realized sales (salesorders + order line items) |
| `--full-snapshot` | | off | Ignore `lookback-hours`; fetch all matching records (initial backfill) |
| `--include-active-orders` | | off | Skip Fulfilled/Invoiced-only filter on `salesorders` (include Active statecode 0; use for sandbox/test CRM) |

**Security:** Never commit real secrets. Pass `--client-secret` via NiFi Parameter Context, HashiCorp Vault, or equivalent.

## Scope — realized sales only

The collector does **not** call Dynamics endpoints for invoices, contracts, opportunities, or
quotes. That reduces required app privileges and avoids 403 noise. Revenue and sold quantities
for the GUI come from **Fulfilled / Invoiced sales orders** and **sales order line items** only.
Rationale: [`datalake-platform-knowledge-base/adrs/ADR-0010-crm-realized-sales-only-scope.md`](../../../datalake-platform-knowledge-base/adrs/ADR-0010-crm-realized-sales-only-scope.md).

## Entities and incremental filters

### Master data — always full snapshot (no `modifiedon` filter)

| Entity | OData endpoint | `data_type` |
|--------|---------------|-------------|
| Accounts | `accounts?$filter=statecode eq 0` | `crm_inventory_account` |

### Product catalog — always full snapshot

| Entity | OData endpoint | `data_type` |
|--------|---------------|-------------|
| Products | `products?$filter=statecode eq 0` | `crm_inventory_product` |
| Price Lists | `pricelevels` | `crm_inventory_pricelevel` |
| Unit Prices | `productpricelevels` | `crm_inventory_productpricelevel` |

### Realized sales — incremental on header (`$filter=modifiedon ge <UTC>`) plus **state**

Only **Fulfilled** (`statecode eq 3`) and **Invoiced** (`statecode eq 4`) sales orders are collected (Microsoft Learn: `salesorder_statecode`). Line items are loaded in the same request via `$expand=order_details(...)`.

| Entity | OData endpoint | `data_type` |
|--------|---------------|-------------|
| Sales Orders | `salesorders?$expand=order_details(...)` | `crm_inventory_salesorder` |
| (expanded) Order lines | nested under `order_details` | `crm_inventory_salesorderdetail` |

## Output contract

Each element in the JSON array includes `data_type` and `collection_time`. Objects are **sparse**: only fields for that entity type appear; missing fields are `null` in the DB via NiFi PutDatabaseRecord.

| `data_type` | UPSERT key |
|-------------|-----------|
| `crm_inventory_account` | `accountid` |
| `crm_inventory_product` | `productid` |
| `crm_inventory_pricelevel` | `pricelevelid` |
| `crm_inventory_productpricelevel` | `productpricelevelid` |
| `crm_inventory_salesorder` | `salesorderid` |
| `crm_inventory_salesorderdetail` | `salesorderdetailid` |

## PostgreSQL tables

DDL: `datalake/SQL/CRM/discovery_crm_*.sql` (one file per table, with `COMMENT ON TABLE/COLUMN`).

| Table | data_type |
|-------|-----------|
| `discovery_crm_accounts` | `crm_inventory_account` |
| `discovery_crm_products` | `crm_inventory_product` |
| `discovery_crm_pricelevels` | `crm_inventory_pricelevel` |
| `discovery_crm_productpricelevels` | `crm_inventory_productpricelevel` |
| `discovery_crm_salesorders` | `crm_inventory_salesorder` |
| `discovery_crm_salesorderdetails` | `crm_inventory_salesorderdetail` |
| `discovery_crm_customer_alias` | *(populated by `seed_customer_alias_from_accounts.sql`)* |
| `gui_crm_service_pages` / `gui_crm_service_mapping_seed` / `gui_crm_service_mapping_override` / `v_gui_crm_product_mapping` | *(GUI service mapping — see `datalake/SQL/CRM/migrations/2026-04-24-gui-crm-service-mapping.sql` + `Datalake-Platform-GUI/shared/service_mapping/`)* |

## Avro schema (NiFi JsonTreeReader)

Single unified schema:

- `SQL/json_schemas/CRM/crm-dynamics-discovery.json` — record name `CrmDynamicsDiscovery`

Use the **same** schema text across all **6** NiFi routes. Stdout JSON is a subset of keys per row; the schema defines the full column contract for NiFi type coercion and DB mapping.

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
  JsonPath: $[*]

EvaluateJsonPath
  data_type → ${data_type}

RouteOnAttribute  (6 routes):
  crm_inventory_account           → PutDatabaseRecord → discovery_crm_accounts            (Update Keys: accountid)
  crm_inventory_product           → PutDatabaseRecord → discovery_crm_products            (Update Keys: productid)
  crm_inventory_pricelevel        → PutDatabaseRecord → discovery_crm_pricelevels         (Update Keys: pricelevelid)
  crm_inventory_productpricelevel → PutDatabaseRecord → discovery_crm_productpricelevels  (Update Keys: productpricelevelid)
  crm_inventory_salesorder        → PutDatabaseRecord → discovery_crm_salesorders         (Update Keys: salesorderid)
  crm_inventory_salesorderdetail  → PutDatabaseRecord → discovery_crm_salesorderdetails   (Update Keys: salesorderdetailid)

PutDatabaseRecord (all routes):
  Statement Type: UPSERT
  Record Reader:  JsonTreeReader (Schema Access Strategy: Use 'Schema Text' Property)
  Schema Text:    <content of SQL/json_schemas/CRM/crm-dynamics-discovery.json>
```

Cron (suggested): every 30 minutes — `0 0/30 * * * ?`

For initial backfill (all Fulfilled/Invoiced orders regardless of `modifiedon`):

```
... --full-snapshot
```

For **test / sandbox** CRM where orders stay **Active** (not Fulfilled/Invoiced):

```
... --include-active-orders
```

Combine with `--full-snapshot` to load all active orders without a `modifiedon` window.

For catalog-only refresh (products and prices, no sales data):

```
... --skip-accounts --skip-sales --full-snapshot
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
  | python3 -m json.tool | head -50
```

**Stderr histogram (every run):** After all fetches, the script writes one `[INFO] crm-dynamics-discovery: stdout_json_array_length=…` line to **stderr** listing counts for each of the six `data_type` values (zeros included). Check NiFi / container logs for this line — if `crm_inventory_productpricelevel=0` while `analyze_scripts/crm_productpricelevel_analyze.py` shows hundreds of OData rows, the process is likely started with **`--skip-catalog`** or a **different app registration** than the one used for the analyze script (403 on `productpricelevels` yields an empty OData list and a `[WARN] 403` line).

**Deep fetch logging:** Add `--verbose-fetch` to log per-entity `odata_rows` vs `emitted` on stderr (confirms whether the Web API returned rows before normalization).

**Quick catalog-only JSON check:**

```bash
python3 crm-dynamics-discovery.py ... --skip-accounts --skip-sales --full-snapshot 2>crm-stats.log | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for x in d if x.get('data_type')=='crm_inventory_productpricelevel'))"
```

## Diagnostic: product price levels (empty table troubleshooting)

When `discovery_crm_productpricelevels` stays empty, use the analyze helper (full pagination, field coverage vs DDL, optional collector normalization preview):

```bash
cd datalake/collectors/CRM/Dynamics365/analyze_scripts
python3 crm_productpricelevel_analyze.py \
  --tenant-id "<TENANT_ID>" \
  --client-id "<CLIENT_ID>" \
  --client-secret "<SECRET>" \
  --crm-url "https://<org>.crm4.dynamics.com" \
  --show-sample
```

Optional: `--save-raw ./out/` writes `raw_catalog_productpricelevels.json` and `raw_catalog_pricelevels.json`. If OData returns rows but the DB table is still empty, verify NiFi `RouteOnAttribute` includes `crm_inventory_productpricelevel` (see `datalake/SQL/CRM/NiFi-productpricelevel-fix.md`).

## Unit tests

```bash
cd datalake/collectors/CRM/Dynamics365
python3 -m pytest test_crm_dynamics_discovery.py test_crm_productpricelevel_analyze.py -v
```

## References

- [Collector & discovery template](../../docs/development-templates/collector_discovery_template.md)
- [Compliance checklist](../../docs/development-templates/collector_discovery_checklist.md)
- Knowledge base: `datalake-platform-knowledge-base/wiki/datalake-collectors/CRM-Dynamics365.md`
- Reference implementation: [`../../ServiceCore/servicecore-discovery.py`](../../ServiceCore/servicecore-discovery.py)
