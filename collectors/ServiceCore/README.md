# ServiceCore ITSM discovery collector

Python script `servicecore-discovery.py` calls the ServiceCore OData API (`Incident/GetAll`, `ServiceRequest/GetAll`), applies incremental `$filter` windows, paginates with `$top`/`$skip`, normalizes records to a **unified flat JSON shape** (all schema fields present; type-specific fields are `null` on the other ticket type), and prints a **UTF-8 JSON array** on **stdout** for Apache NiFi `ExecuteStreamCommand` → `SplitJson` → `PutDatabaseRecord`.

## CLI parameters (same pattern as other collectors, e.g. Zabbix Network, S3)

All connection and tuning options are passed **explicitly** via `argparse` (kebab-case long options). There is **no** `--config` / JSON file path for this script.

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--api-url` | yes | — | Base URL, e.g. `https://operationsupportapi.bulutistan.com/api/v1` |
| `--api-key` | yes | — | API key sent as `ApiKey` header |
| `--lookback-hours` | no | `24` | Rolling window for OData filters (UTC) |
| `--page-size` | no | `100` | OData `$top` page size |
| `--username` | no | — | Reserved for future User API flows (not used for Incident/SR GET) |
| `--password` | no | — | Reserved for future User API flows (not used for Incident/SR GET) |

`configuration_file.json.example` remains a **template** for documenting the same keys when operators store secrets in a shared JSON file elsewhere; NiFi should expand values into the command line or use parameterized arguments.

**Security:** Do not commit real secrets; pass `--api-key` via NiFi Parameter Context, secrets manager, or equivalent.

## Incremental filters

- **Incidents:** `$filter=LastUpdatedDate ge <UTC ISO Z>`
- **Service Requests:** `$filter=RequestDate ge <UTC ISO Z>`

The cutoff is `now() - lookback_hours` in UTC.

## Output contract

Each element includes `data_type`:

- `servicecore_inventory_incident` — UPSERT key: `ticket_id`
- `servicecore_inventory_servicerequest` — UPSERT key: `service_request_id`

Every record includes **all** unified fields; fields that belong only to the other type are JSON `null` (for a single Avro schema and one `JsonTreeReader`).

HTML-heavy fields are **not** emitted; plain-text analytics use `TicketDescriptionTextFormat` / `RequestDescriptionTextFormat` as `description_text_format` / `request_description_text_format`.

Timestamp fields are **ISO-8601 strings** (UTC), aligned with the Avro schema and PostgreSQL `TIMESTAMPTZ`.

## PostgreSQL tables

| Layer | Table |
|-------|--------|
| Bronze (raw JSONB) | `raw_servicecore_logs` |
| Silver (discovery UPSERT) | `discovery_servicecore_incidents`, `discovery_servicecore_servicerequests` |

DDL: `SQL/ServiceCore/*.sql`

## Avro schema (NiFi JsonTreeReader)

Single record definition:

- `SQL/json_schemas/ServiceCore/servicecore-discovery.json` — record name `ServiceCoreDiscovery`

Use the **same** schema text for both discovery routes. Each target table only contains a subset of columns; if your NiFi version rejects extra fields, narrow the record with `UpdateRecord` / `JoltTransformJSON` per route, or enable the processor option that ignores unmatched fields when supported.

## NiFi checklist

1. **ExecuteStreamCommand** — pass arguments explicitly, for example:
   `python3 /Datalake_Project/collectors/ServiceCore/servicecore-discovery.py --api-url https://operationsupportapi.bulutistan.com/api/v1 --api-key ${servicecore.api.key} --lookback-hours 24 --page-size 100`
2. **SplitJson:** JsonPath `$.*`
3. **EvaluateJsonPath:** `data_type` → attribute `data_type`
4. **RouteOnAttribute:** route `servicecore_inventory_incident` vs `servicecore_inventory_servicerequest`
5. **PutDatabaseRecord:** Statement Type `UPSERT`; Update Keys `ticket_id` (incidents) / `service_request_id` (SR); **same** `JsonTreeReader` + `servicecore-discovery.json` on both paths when compatible with your NiFi/DBCP settings
6. **Cron (example):** every 30 minutes — `0 0/30 * * * ?`

## Manual test

```bash
python3 servicecore-discovery.py --api-url "https://operationsupportapi.bulutistan.com/api/v1" --api-key "YOUR_KEY" --lookback-hours 24 --page-size 100 | python3 -m json.tool | head
```

## References

- [Collector & discovery template](../../docs/development-templates/collector_discovery_template.md)
- Knowledge base: `datalake-platform-knowledge-base/wiki/datalake-collectors/ServiceCore-ITSM.md`
