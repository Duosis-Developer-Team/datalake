# ServiceCore ITSM discovery collector

Python script `servicecore-discovery.py` calls the ServiceCore OData API (`Incident/GetAll`, `ServiceRequest/GetAll`, `User/GetAllUsers`), applies incremental `$filter` windows for incidents and service requests, paginates with `$top`/`$skip`, normalizes records to **per-type sparse JSON** (only keys relevant to each `data_type`; no cross-type null padding), and prints a **UTF-8 JSON array** on **stdout** for Apache NiFi `ExecuteStreamCommand` → `SplitJson` → `PutDatabaseRecord`.

## CLI parameters (same pattern as other collectors, e.g. Zabbix Network, S3)

All connection and tuning options are passed **explicitly** via `argparse` (kebab-case long options). There is **no** `--config` / JSON file path for this script.

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--api-url` | yes | — | Base URL, e.g. `https://operationsupportapi.bulutistan.com/api/v1` |
| `--api-key` | yes | — | API key sent as `ApiKey` header |
| `--lookback-hours` | no | `24` | Rolling window for OData filters on incidents and SR (UTC) |
| `--page-size` | no | `100` | OData `$top` page size |
| `--skip-users` | no | off | If set, do not call `User/GetAllUsers` |
| `--username` | no | — | Reserved for future auth flows (not used for GET endpoints) |
| `--password` | no | — | Reserved for future auth flows (not used for GET endpoints) |

`configuration_file.json.example` remains a **template** for documenting the same keys when operators store secrets in a shared JSON file elsewhere; NiFi should expand values into the command line or use parameterized arguments.

**Security:** Do not commit real secrets; pass `--api-key` via NiFi Parameter Context, secrets manager, or equivalent.

## Incremental filters

- **Incidents:** `$filter=LastUpdatedDate ge <UTC ISO Z>`
- **Service Requests:** `$filter=RequestDate ge <UTC ISO Z>`
- **Users:** `$filter=1 eq 1` (full catalog each run; use `--skip-users` to omit)

The cutoff for incidents and SR is `now() - lookback_hours` in UTC.

**Note:** SR use **request** date, not last-updated date. A run can return incidents but zero service requests if no SR was *created* in the window. See the wiki for details.

## Output contract

Each element includes `data_type`:

- `servicecore_inventory_incident` — UPSERT key: `ticket_id`
- `servicecore_inventory_servicerequest` — UPSERT key: `service_request_id`
- `servicecore_inventory_user` — UPSERT key: `user_id`

**Sparse JSON:** Objects contain only fields for that type (plus `collection_time`). Keys whose normalized value is `null` are omitted. Other types’ fields never appear (no `user_id` on incident rows, etc.).

**Avro:** [`servicecore-discovery.json`](../../SQL/json_schemas/ServiceCore/servicecore-discovery.json) still defines **all** possible fields (`ServiceCoreDiscovery`) so NiFi knows column names and types; missing JSON keys map to null in the database when using PutDatabaseRecord.

HTML-heavy fields are **not** emitted; plain-text analytics use `TicketDescriptionTextFormat` / `RequestDescriptionTextFormat` as `description_text_format` / `request_description_text_format`.

Timestamp fields are **ISO-8601 strings** (UTC), aligned with the Avro schema and PostgreSQL `TIMESTAMPTZ`.

**Origin channel:** `origin_from_name` prefers the flat API field `OriginFromName`, then nested `Ticket_OriginFrom.TicketOriginFromName`.

## PostgreSQL tables

| Layer | Table |
|-------|-------|
| Bronze (raw JSONB) | `raw_servicecore_logs` |
| Silver (discovery UPSERT) | `discovery_servicecore_incidents`, `discovery_servicecore_servicerequests`, `discovery_servicecore_users` |

DDL: `SQL/ServiceCore/*.sql` (includes `COMMENT ON TABLE` / `COMMENT ON COLUMN`).

## Avro schema (NiFi JsonTreeReader)

Single record definition:

- `SQL/json_schemas/ServiceCore/servicecore-discovery.json` — record name `ServiceCoreDiscovery`

Use the **same** schema text for all discovery routes. Stdout JSON is a **subset** of keys per row; the schema is the **full** contract for typing and NiFi column mapping.

## NiFi checklist

1. **ExecuteStreamCommand** — pass arguments explicitly, for example:
   `python3 /Datalake_Project/collectors/ServiceCore/servicecore-discovery.py --api-url https://operationsupportapi.bulutistan.com/api/v1 --api-key ${servicecore.api.key} --lookback-hours 24 --page-size 100`
2. **SplitJson:** JsonPath `$.*`
3. **EvaluateJsonPath:** `data_type` → attribute `data_type`
4. **RouteOnAttribute:** route `servicecore_inventory_incident` vs `servicecore_inventory_servicerequest` vs `servicecore_inventory_user`
5. **PutDatabaseRecord:** Statement Type `UPSERT`; Update Keys `ticket_id` (incidents) / `service_request_id` (SR) / `user_id` (users); **same** `JsonTreeReader` + `servicecore-discovery.json` on all paths when compatible with your NiFi/DBCP settings
6. **Cron (example):** every 30 minutes — `0 0/30 * * * ?`

## Manual test

```bash
python3 servicecore-discovery.py --api-url "https://operationsupportapi.bulutistan.com/api/v1" --api-key "YOUR_KEY" --lookback-hours 24 --page-size 100 --skip-users | python3 -m json.tool | head
```

## Unit tests

```bash
python3 -m unittest test_servicecore_discovery.py -v
```

## References

- [Collector & discovery template](../../docs/development-templates/collector_discovery_template.md)
- Knowledge base: `datalake-platform-knowledge-base/wiki/datalake-collectors/ServiceCore-ITSM.md`
