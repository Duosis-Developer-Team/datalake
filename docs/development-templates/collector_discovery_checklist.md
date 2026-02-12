### Collector & Discovery Compliance Checklist

This checklist is used to verify whether existing and new collector/discovery implementations comply with the standard development template and naming conventions.

---

### 1. Compliance Criteria

Each implementation should be evaluated against the following criteria:

1. **Script naming**
   - Collector scripts use metric-oriented suffixes (e.g. `-metrics.py`, `-stats.py`).
   - Discovery scripts use discovery/inventory naming (e.g. `-discovery.py`, domain-specific names like `loki-get-vm.py`).

2. **Output format**
   - Script outputs a JSON array to stdout (preferred), or a well-structured SQL batch if legacy.
   - For JSON:
     - Contains `data_type`.
     - Contains a snapshot timestamp (`collection_time` or `collection_timestamp`).
     - Uses flat fields that map directly to DB columns.

3. **NiFi flow pattern**
   - Uses `ExecuteStreamCommand → SplitJson → EvaluateJsonPath → RouteOnAttribute → PutDatabaseRecord` (or a justified variant).
   - `ExecuteStreamCommand` runs the correct script and passes required parameters.
   - `SplitJson` uses `JsonPath = $.*`.

4. **JSON/Avro schema**
   - A schema file exists under `SQL/json_schemas/<Domain>/<script_name>.json`.
   - Schema uses unions like `["null", "string"]` or `["null", "long"]` for optional fields.
   - Timestamp fields are defined as `long` with `logicalType: "timestamp-millis"`.
   - Schema fields match the DB table columns.

5. **Table design and naming**
   - Target table uses the `raw_` prefix for collectors (time series).
   - Target table uses the `discovery_` prefix for discovery/inventory (UPSERT).
   - Table DDL exists under `SQL/<Domain>/<script_name>.sql`.

6. **UPSERT configuration (discovery only)**
   - NiFi `PutDatabaseRecord` is configured with appropriate **Update Keys**.
   - Keys uniquely identify the entity (e.g. `id`, or composite keys like `vcenter_uuid,component_moid`).
   - Behaviour is “insert or update” (UPSERT) rather than pure INSERT.

---

### 2. Implementations That Comply (or Mostly Comply)

> Status values:
> - **Full**: Matches the template and naming fully (or with very minor deviations).
> - **Partial**: Generally follows the pattern but requires some cleanup or renaming.
> - **Planned**: Work in progress to reach compliance.

#### 2.1 NetBox VM Inventory (Discovery)

- **Name**: NetBox virtualization VM inventory (UPSERT)
- **Type**: Discovery
- **Script**: `collectors/NetBox/loki-get-vm.py`
- **Table**: `discovery_netbox_virtualization_vm` (recommended logical name; current physical table may still be `netbox_virtualization_vm`)
- **JSON schema**: `SQL/json_schemas/NetBox/loki-get-vm.json`
- **DDL**: `SQL/NetBox/loki_get_virtualmachines.sql`
- **NiFi flow** (expected):
  - `ExecuteStreamCommand (loki-get-vm.py)`  
  - `SplitJson ($.*)`  
  - `EvaluateJsonPath (data_type, id, custom_fields_uuid, ...)`  
  - `RouteOnAttribute (data_type == 'netbox_inventory_vm')`  
  - `PutDatabaseRecord (Update Keys: id)`
- **Status**: **Partial**
  - Strong alignment with discovery template (JSON output, schema, NiFi pattern, UPSERT).
  - Table name should adopt the `discovery_` prefix for full compliance.

#### 2.2 HPE iLO Redfish Collector (Inventory + Metrics)

- **Name**: HPE iLO Redfish inventory + metrics
- **Type**: Mixed (collector + discovery-style inventory)
- **Script**: `collectors/ILO/Redfis-API/redfish_collector.py`
- **Tables** (examples; actual names may vary):
  - Inventory-style: logical `discovery_ilo_inventory_*` (e.g. `discovery_ilo_inventory_disk`).
  - Metrics-style: logical `raw_ilo_metrics_*` (e.g. `raw_ilo_metrics_cpu`).
- **Design doc**: `collectors/ILO/Redfis-API/README.md`
- **JSON schema**: Defined in NiFi as a comprehensive Avro schema (see README).
- **NiFi flow**:
  - `ExecuteStreamCommand`  
  - `SplitJson`  
  - `EvaluateJsonPath (data_type)`  
  - `RouteOnAttribute (by data_type)`  
  - `PutDatabaseRecord` per table.
- **Status**: **Partial**
  - Pattern and schema strategy already match the template (JsonTreeReader with Schema Text, data_type-based routing).
  - Table names and Some UPSERT key configurations may need to be revisited to adopt `raw_` / `discovery_` prefixes and consistent primary keys.

#### 2.3 VMware Discovery

- **Name**: VMware vSphere discovery
- **Type**: Discovery (inventory)
- **Scripts**:
  - `discovery/vmware/vmware-discovery.py`
  - `collectors/VMware/discovery/vmware-discovery.py` (host-centric variant)
- **Output**: JSON inventory records with `data_type` values like `vmware_inventory_vm`, `vmware_inventory_host`, etc.
- **NiFi flow** (expected/typical):
  - `ExecuteStreamCommand (vmware-discovery.py)`  
  - `SplitJson`  
  - `EvaluateJsonPath (data_type, vcenter_uuid, component_moid)`  
  - `RouteOnAttribute (by data_type)`  
  - `PutDatabaseRecord` for each logical table.
- **Target tables**:
  - Logical pattern: `discovery_vmware_inventory_*` (e.g. `discovery_vmware_inventory_vm`).
- **Status**: **Partial**
  - Behaves like a discovery script and follows the data_type pattern.
  - Table naming and explicit UPSERT keys (e.g. `vcenter_uuid, component_moid`) need to be standardized and documented in DDL + schema files.

---

### 3. Implementations That Do Not Yet Fully Comply

> This section is not exhaustive; it highlights only representative examples and known gaps.

#### 3.1 Legacy SQL-Generating Collectors

- **Pattern**: Scripts that build `INSERT ... VALUES (...)` SQL batches directly and print them, without structured JSON or Avro schema.
- **Typical issues**:
  - No JSON output → cannot use JsonTreeReader / schema-based processing.
  - NiFi cannot easily perform UPSERT or schema evolution.
  - Table naming does not use `raw_` / `discovery_` prefixes.
- **Status**: **Non-compliant**
  - Recommended remediation:
    - Refactor scripts to output JSON arrays with `data_type` and timestamps.
    - Introduce Avro schemas under `SQL/json_schemas/<Domain>/`.
    - Update NiFi flows to use `PutDatabaseRecord` with JsonTreeReader.

#### 3.2 Tables Without `raw_` or `discovery_` Prefixes

- **Pattern**: Existing tables (e.g. `netbox_virtualization_vm`, various `ilo_*` tables) created before the prefix standard.
- **Issues**:
  - Inconsistent naming reduces discoverability and makes responsibilities less obvious.
  - Harder to automatically infer whether a table is time series or inventory.
- **Status**: **Non-compliant (naming only)**
  - Recommended remediation:
    - For new work, always use prefix-compliant names.
    - For existing tables:
      - Option 1: Introduce new `raw_` / `discovery_` tables and migrate data.
      - Option 2: Use views with prefix-compliant names that wrap the old physical tables as an intermediate step.

---

### 4. Future Work and Migration Plan (High Level)

- **Short term**:
  - Ensure all new collectors/discovery scripts strictly follow the template.
  - Document schema and DDL for any existing flows that still lack them.

- **Medium term**:
  - Gradually refactor legacy SQL-only collectors to JSON + Avro schema + `PutDatabaseRecord`.
  - Introduce `raw_`/`discovery_`-prefixed views for critical existing tables where immediate physical rename is not practical.

- **Long term**:
  - Standardize all production flows so that:
    - Every script has a corresponding template-compliant design.
    - Every table uses `raw_` or `discovery_` prefixes.
    - Every NiFi flow uses JsonTreeReader with Schema Text for deterministic schema handling.

This checklist should be updated whenever new collectors/discovery flows are added or existing ones are refactored, to keep the architecture coherent and maintainable.

