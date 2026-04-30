# NiFi — CRM Dynamics 365 discovery

## Template reference

`datalake/etl-pipelines/nifi-collect-data-from-source-all.xml` **template `<description>`** points here for CRM wiring. The monolithic template does not embed a CRM process group; add CRM processors on the NiFi canvas (or merge from a PG export) using the checklist below.

Verified: that XML file contains **no** Dynamics entity names such as `invoices`, `contracts`, `opportunities`, or `quotes` in CRM-specific processors (grep for those strings only hits unrelated keys such as `put-db-record-quoted-*`).

## Required `data_type` values

NiFi must route **exactly six** `data_type` values emitted by `crm-dynamics-discovery.py`:

| `data_type` | PostgreSQL table | UPSERT / conflict column |
|-------------|------------------|---------------------------|
| `crm_inventory_account` | `discovery_crm_accounts` | `accountid` |
| `crm_inventory_product` | `discovery_crm_products` | `productid` |
| `crm_inventory_pricelevel` | `discovery_crm_pricelevels` | `pricelevelid` |
| `crm_inventory_productpricelevel` | `discovery_crm_productpricelevels` | `productpricelevelid` |
| `crm_inventory_salesorder` | `discovery_crm_salesorders` | `salesorderid` |
| `crm_inventory_salesorderdetail` | `discovery_crm_salesorderdetails` | `salesorderdetailid` |

Use a single **JsonTreeReader** with schema text from [`json_schemas/CRM/crm-dynamics-discovery.json`](../json_schemas/CRM/crm-dynamics-discovery.json).

## RouteOnAttribute (six dynamic properties)

Routing strategy: **Route to Property name**. Add one dynamic property per row (property name = relationship name; value = EL):

| Property name (relationship) | Value |
|------------------------------|--------|
| `crm_inventory_account` | `${data_type:equals('crm_inventory_account')}` |
| `crm_inventory_product` | `${data_type:equals('crm_inventory_product')}` |
| `crm_inventory_pricelevel` | `${data_type:equals('crm_inventory_pricelevel')}` |
| `crm_inventory_productpricelevel` | `${data_type:equals('crm_inventory_productpricelevel')}` |
| `crm_inventory_salesorder` | `${data_type:equals('crm_inventory_salesorder')}` |
| `crm_inventory_salesorderdetail` | `${data_type:equals('crm_inventory_salesorderdetail')}` |

Upstream **EvaluateJsonPath** must set flowfile attribute `data_type` from `$.data_type` (Destination: flowfile-attribute), after **SplitJson** with JsonPath `$[*]` on the collector JSON array.

If only **account** and **product** routes exist today, add the **four** missing rows above so `pricelevels`, `productpricelevels`, `salesorders`, and `salesorderdetails` reach their `PutDatabaseRecord` processors (otherwise those records are **unmatched** and never written).

## PutDatabaseRecord (per route)

Use the same **DBCPConnectionPool** as other datalake writers (e.g. `BulutDBDataLake`). For **each** of the six relationships:

| Setting | Value |
|---------|--------|
| **Database Type** | `PostgreSQL` |
| **Table Name** | Table from the first table above |
| **Statement Type** | `UPSERT` (PostgreSQL `ON CONFLICT` … `DO UPDATE`) |
| **Update Keys** | Conflict column from the first table above (single column) |
| **Record Reader** | `JsonTreeReader` |
| **Translate Field Names** | `false` (JSON keys match DB column names) |
| **Unmatched Field Behavior** | `Ignore Unmatched Fields` |
| **Unmatched Column Behavior** | Match your environment (`Fail on Unmatched Columns` is strict) |

## Collector flag for test CRM (Active sales orders)

Production default: only **Fulfilled / Invoiced** sales orders (`statecode` 3 or 4). Test orgs often keep orders **Active** (`statecode` 0). Use:

`--include-active-orders`

so the OData filter does not require state 3/4 (still uses `--lookback-hours` unless `--full-snapshot`). See `datalake/collectors/CRM/Dynamics365/README.md`.

## ProductPriceLevel troubleshooting

If `discovery_crm_productpricelevels` stays empty while other CRM tables fill, see [`NiFi-productpricelevel-fix.md`](NiFi-productpricelevel-fix.md).
