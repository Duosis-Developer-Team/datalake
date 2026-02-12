### Collector & Discovery Development Template

This document defines a reusable template for implementing **collector** (time series) and **discovery** (inventory/UPSERT) flows across the data platform. It standardizes script design, output format, NiFi flows, JSON/Avro schemas, and database table structures.

---

### 1. Naming Conventions

#### 1.1 Table names

- **Collector (time series) tables**: prefix with `raw_`
  - Pattern: `raw_<domain>_<entity>[_metrics]`
  - Examples:
    - `raw_ilo_metrics_cpu`
    - `raw_vmware_vm_metrics`
    - `raw_nutanix_cluster_metrics`

- **Discovery (inventory / UPSERT) tables**: prefix with `discovery_`
  - Pattern: `discovery_<domain>_<entity>[_inventory]`
  - Examples:
    - `discovery_netbox_virtualization_vm`
    - `discovery_vmware_inventory_vm`
    - `discovery_ilo_inventory_disk`

> Existing tables may not yet follow this scheme; new work SHOULD use it, and older work SHOULD be migrated over time.

#### 1.2 Script names

- **Collector scripts (time series)**:
  - Use metric-oriented suffixes:
    - `*-metrics.py`, `*-stats.py`, `*-performance.py`
  - Examples:
    - `vmware_vm_performance_metrics.py`
    - `nutanix_cluster_stats.py`

- **Discovery scripts (inventory / UPSERT)**:
  - Use `*-discovery.py` or explicit inventory/domain names:
    - `vmware-discovery.py`
    - `loki-get-vm.py` (NetBox VM discovery)

#### 1.3 Schema and DDL file locations

- **JSON/Avro schemas**:
  - Path pattern: `SQL/json_schemas/<Domain>/<script_name>.json`
  - Example: `SQL/json_schemas/NetBox/loki-get-vm.json`

- **Table DDL (CREATE TABLE)**:
  - Path pattern: `SQL/<Domain>/<script_name>.sql`
  - Example: `SQL/NetBox/loki_get_virtualmachines.sql`

---

### 2. Collector (Time Series) Script Template

Collector scripts are responsible for producing time series data (metrics). They typically **INSERT only** (no UPSERT) into `raw_` tables.

#### 2.1 Responsibilities

- Load runtime configuration (endpoints, credentials, table names, batch size).
- Fetch data from source systems (API, SDK, CLI, etc.).
- Normalize source payloads into Python primitives (dicts, lists).
- Emit either:
  - JSON array to stdout (recommended, for NiFi `PutDatabaseRecord`), or
  - Batch `INSERT` SQL (legacy pattern; avoid for new work if possible).

#### 2.2 Recommended structure

- `load_config()`
  - Reads a central configuration file (e.g. `/Datalake_Project/configuration_file.json`) or environment variables.
  - Validates the presence of required keys.

- `fetch_data(...)`
  - Handles authentication, pagination, retry logic, and error handling.
  - Uses `requests`/SDK with sensible timeouts.

- `normalize_record(raw_item, collection_timestamp)`
  - Converts a single raw item into a dict of primitive fields:
    - Timestamps, keys, metric values, identifiers.
  - Returns `None` in case of irrecoverable mapping errors.

- `main()`
  - Loads config.
  - Calls `fetch_data`.
  - Computes a single `collection_timestamp` for the batch (for time-series this is often per-measurement, but you may want a consistent batch timestamp).
  - Builds a list of normalized dicts and prints them as a JSON array.

#### 2.3 Output format (collector)

Recommended JSON shape:

- Required fields:
  - `data_type`: string describing the metric type (e.g. `ilo_metrics_cpu`, `vmware_vm_metrics`).
  - `collection_timestamp`: ISO-8601 UTC timestamp (string in JSON).
  - Metric key fields (e.g. `chassis_serial_number`, `cpu_id`, `vm_id`).
  - Metric values (e.g. `power_watts`, `frequency_mhz`, `cpu_util_percent`).

- Example:

```json
{
  "data_type": "ilo_metrics_cpu",
  "collection_timestamp": "2026-02-12T11:30:45.123456+00:00",
  "chassis_serial_number": "CZJ12345AB",
  "cpu_id": 1,
  "power_watts": 95.2,
  "frequency_mhz": 2650.0
}
```

---

### 3. Discovery (Inventory / UPSERT) Script Template

Discovery scripts provide **inventory views** of systems. They should support UPSERT (update existing row if key exists, insert otherwise) into `discovery_` tables.

#### 3.1 Responsibilities

- Load configuration and connect to the source (e.g. NetBox, vCenter, iLO).
- Enumerate entities (VM, host, cluster, physical asset, etc.).
- Produce a **flattened JSON inventory record** per entity.
- Mark each record clearly with:
  - `data_type` describing the inventory domain.
  - A **stable UPSERT key** (or composite key).
  - A **snapshot timestamp**.

#### 3.2 Naming and data_type standard

- `data_type` pattern: `<domain>_inventory_<entity>`
  - Examples:
    - `netbox_inventory_vm`
    - `vmware_inventory_vm`
    - `ilo_inventory_disk`

#### 3.3 Snapshot timestamp

- Field name: usually `collection_time` or `collection_timestamp`.
- JSON: ISO-8601 string, UTC if possible.
  - Example: `2026-02-12T11:27:27.089+00:00`.
- Avro: `long` with `logicalType: "timestamp-millis"`.
- DB: `TIMESTAMPTZ` (or equivalent).

#### 3.4 UPSERT key strategy

- Keys MUST uniquely identify an entity within the dataset.
- Examples:
  - NetBox VM: `id` (NetBox VM ID); optional `custom_fields_uuid` for broader correlation.
  - VMware: combination of `vcenter_uuid` and `component_moid`.
  - Redfish/ILO: `chassis_serial_number` + component identifier (e.g. `disk_id`, `interface_id`).

These keys are configured as **Update Keys** in NiFi `PutDatabaseRecord`.

#### 3.5 Output format (discovery)

- Output is always a JSON array of inventory records.
- Each item is a flat dict whose fields map 1:1 to DB columns.
- Example (NetBox VM inventory, simplified):

```json
{
  "data_type": "netbox_inventory_vm",
  "id": 22542,
  "name": "Aps_Tekstil-APSDCAD",
  "status_value": "poweredOn",
  "site_id": 1,
  "cluster_id": 31,
  "device_id": 10550,
  "vcpus": 2,
  "memory": 4096,
  "disk": 50,
  "custom_fields_guest_os": "Microsoft Windows Server 2016 (64-bit)",
  "custom_fields_uuid": "b628e342-a744-4734-9075-5c83211dfa69",
  "created": "2024-10-03T15:05:40.59+00",
  "last_updated": "2026-02-12T10:33:52.445+00",
  "collection_time": "2026-02-12T11:27:27.089+00:00"
}
```

---

### 4. Standard NiFi Flow Templates

NiFi is the orchestration layer that runs scripts, splits JSON, and writes to PostgreSQL using `PutDatabaseRecord`.

#### 4.1 Collector (raw / time series) flow

Recommended pattern:

```text
ExecuteStreamCommand → SplitJson → EvaluateJsonPath (optional) → RouteOnAttribute (optional) → PutDatabaseRecord
```

- **ExecuteStreamCommand**:
  - Runs the collector script (`python3 collectors/...-metrics.py`).
  - Reads any required parameters from a configuration file or FlowFile attributes.
  - Stdout must be a JSON array.

- **SplitJson**:
  - JsonPath: `$.*`
  - Creates one FlowFile per record.

- **EvaluateJsonPath** (optional):
  - Extracts `data_type`, key fields, etc., into attributes for routing.

- **RouteOnAttribute** (optional):
  - Routes based on `data_type` or environment attributes when multiple tables are involved.

- **PutDatabaseRecord**:
  - Uses a `JsonTreeReader` with an Avro schema.
  - Target table: `raw_<domain>_<entity>[_metrics]`.
  - No UPSERT; all records are INSERTs.

#### 4.2 Discovery (UPSERT / inventory) flow

Flow structure is similar, but `PutDatabaseRecord` performs UPSERT into a `discovery_` table:

```text
ExecuteStreamCommand → SplitJson → EvaluateJsonPath → RouteOnAttribute → PutDatabaseRecord
```

- **ExecuteStreamCommand**:
  - Runs the discovery script (`python3 collectors/...-discovery.py`, `loki-get-vm.py`, etc.).

- **SplitJson**:
  - Same as collector: `JsonPath = $.*`.

- **EvaluateJsonPath**:
  - Extracts:
    - `data_type`
    - UPSERT key fields (e.g. `id`, `custom_fields_uuid`, `vcenter_uuid`, `component_moid`).

- **RouteOnAttribute**:
  - Routes by `data_type` to the correct discovery table path.

- **PutDatabaseRecord**:
  - Record Reader: `JsonTreeReader` with `Use 'Schema Text' Property`.
  - Record Writer: any appropriate JSON/Avro writer (for logging only).
  - Table Name: `discovery_<domain>_<entity>[_inventory]`.
  - Update Keys: UPSERT keys (e.g. `id`, or `vcenter_uuid,component_moid`).
  - Insert or Update: use NiFi’s `Update Keys` functionality to achieve UPSERT.

---

### 5. JSON / Avro Schema Standard

#### 5.1 Data types

- Use a small, consistent set of Avro types:
  - `string`, `long`, `double`, `boolean`.
  - Unions with `null` for optional fields, e.g. `["null", "string"]`.

#### 5.2 Timestamp fields

- Raw JSON:
  - ISO-8601 with timezone information, e.g.:  
    `2026-02-12T11:27:27.089+00:00`
  - Recommended parsing pattern in NiFi `JsonTreeReader`:

    ```text
    yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXX
    ```

- Avro schema:

```json
{
  "name": "created",
  "type": [
    "null",
    { "type": "long", "logicalType": "timestamp-millis" }
  ]
}
```

Apply the same pattern to all timestamp fields (`last_updated`, `collection_time`, `collection_timestamp`, etc.).

- Database:
  - Use `TIMESTAMPTZ` (or equivalent) for time zone-aware timestamps.

#### 5.3 Schema–DDL alignment

- Every field defined in the Avro schema should have a corresponding column in the target table, with compatible types.
- Field names in the script’s JSON output, the Avro schema, and the DB columns should be identical, unless a deliberate mapping layer is introduced (not recommended for most cases).

---

### 6. Table Design Templates

#### 6.1 Collector (raw) table example

- Name pattern: `raw_<domain>_<entity>_metrics`
- Example structure (CPU metrics):

```sql
CREATE TABLE raw_ilo_metrics_cpu (
  collection_timestamp TIMESTAMPTZ NOT NULL,
  chassis_serial_number TEXT NOT NULL,
  cpu_id INT NOT NULL,
  power_watts DOUBLE PRECISION,
  frequency_mhz DOUBLE PRECISION,
  PRIMARY KEY (collection_timestamp, chassis_serial_number, cpu_id)
);
```

#### 6.2 Discovery (inventory / UPSERT) table example

- Name pattern: `discovery_<domain>_<entity>_inventory`
- Example structure (NetBox VM inventory):

```sql
CREATE TABLE discovery_netbox_virtualization_vm (
  id BIGINT PRIMARY KEY,
  data_type TEXT,
  name TEXT,
  status_value TEXT,
  site_id BIGINT,
  cluster_id BIGINT,
  device_id BIGINT,
  vcpus BIGINT,
  memory BIGINT,
  disk BIGINT,
  custom_fields_guest_os TEXT,
  custom_fields_uuid TEXT,
  created TIMESTAMPTZ,
  last_updated TIMESTAMPTZ,
  collection_time TIMESTAMPTZ
  -- plus additional inventory fields as required
);
```

Indexes on key fields (e.g. `custom_fields_uuid`, `site_id`) are recommended to support joins and filters.

---

### 7. Example References

When implementing new collectors/discovery flows, use these existing components as references:

- **NetBox VM inventory (discovery)**:
  - Script: `collectors/NetBox/loki-get-vm.py`
  - Table DDL: `SQL/NetBox/loki_get_virtualmachines.sql`
  - JSON schema: `SQL/json_schemas/NetBox/loki-get-vm.json`
  - README: `collectors/NetBox/README.md`

- **HPE iLO Redfish collector (inventory + metrics)**:
  - Script: `collectors/ILO/Redfis-API/redfish_collector.py`
  - Design doc: `collectors/ILO/Redfis-API/README.md`

- **VMware discovery**:
  - Script: `discovery/vmware/vmware-discovery.py`

These examples demonstrate the patterns described in this template and should be used as starting points for new work.

