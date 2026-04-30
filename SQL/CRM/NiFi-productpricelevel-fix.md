# NiFi — ProductPriceLevel route not receiving flowfiles

## Symptom

- `PutDatabaseRecord` for `discovery_crm_productpricelevels` shows **0 In / 0 Out / 0 Tasks**.
- `RouteOnAttribute` **unmatched** queue grows by ~800 flowfiles while other CRM routes receive data.
- Collector / OData side is healthy: `raw_catalog_productpricelevels.json` contains many `productpricelevel` rows.

## Root cause

The `RouteOnAttribute` processor is missing the dynamic property for `crm_inventory_productpricelevel`, or the relationship is not wired to the correct `PutDatabaseRecord`.

See also the six-route checklist in [`NiFi-scope-note.md`](NiFi-scope-note.md).

## Fix (NiFi UI)

1. Open the **RouteOnAttribute** that follows **EvaluateJsonPath** / **SplitJson** for CRM discovery JSON.
2. Under **Routing Strategy** = *Route to Property name*, add a dynamic property:
   - **Property name (relationship):** `crm_inventory_productpricelevel`
   - **Value:** `${data_type:equals('crm_inventory_productpricelevel')}`
3. Connect relationship **`crm_inventory_productpricelevel`** to the **`PutDatabaseRecord`** that targets table **`discovery_crm_productpricelevels`** with **Update Keys** = `productpricelevelid` (UPSERT / ON CONFLICT as per `NiFi-scope-note.md`).
4. Ensure **autoterminate** is disabled for matched routes that should flow to PutDatabaseRecord.

## Verify

- After the next collector run, the ProductPriceLevel route should show non-zero **In** counts matching the number of `crm_inventory_productpricelevel` records in the batch (~808 in a known test snapshot).
- In PostgreSQL: `SELECT count(*) FROM discovery_crm_productpricelevels;` should increase after NiFi processes the backlog (or replay unmatched flowfiles if still queued).
