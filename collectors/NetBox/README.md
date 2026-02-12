# NetBox Virtualization VM Inventory Collector

**Version:** 1.0  
**Date:** 12.02.2026  

### 1. Purpose and Scope

#### 1.1 Purpose

This collector is responsible for retrieving virtual machine (VM) inventory data from a NetBox instance and feeding it into the central data lake.  
Unlike pure time-series collectors, this project is designed as **inventory**: for each VM, the latest state is stored and updated in-place (UPSERT) instead of inserting an endless stream of historical rows.

The goals are:

- Provide a reliable, up-to-date inventory of all virtual machines known to NetBox.  
- Keep the data model aligned with other virtualization discovery/collector scripts (e.g. VMware discovery, HPE iLO Redfish collector).  
- Enable Apache NiFi to orchestrate collection and write data into PostgreSQL using deterministic JSON schemas and UPSERT semantics.

#### 1.2 Scope

This design covers:

- **Data source:** NetBox (virtualization API: virtual machines).  
- **Data protocol:** HTTPS + NetBox REST API (JSON).  
- **Data collection:** Python script `loki-get-vm.py`.  
- **Orchestration:** Apache NiFi (ExecuteStreamCommand + SplitJson + EvaluateJsonPath + RouteOnAttribute + PutDatabaseRecord).  
- **Data storage:** PostgreSQL table `public.netbox_virtualization_vm`.  
- **Schema management:** Avro-style JSON schema (for NiFi JsonTreeReader) stored under `SQL/json_schemas/NetBox/loki-get-vm.json`.

---

### 2. Script Overview

#### 2.1 Main Script

- Path: `collectors/NetBox/loki-get-vm.py`  
- Responsibility:  
  - Reads configuration from `/Datalake_Project/configuration_file.json` (`Loki` section).  
  - Calls NetBox virtualization API (`virtualization_endpoint`) using an API token.  
  - Paginates through all VMs and builds a normalized JSON inventory record for each VM.  
  - Prints a single JSON array (`[ {...}, {...}, ... ]`) to `stdout`.

#### 2.2 Configuration (Loki section)

The script expects a `Loki` object in `configuration_file.json`, for example:

```json
{
  "Loki": {
    "ip2": "https://netbox.example.local",
    "virtualization_endpoint": "api/virtualization/virtual-machines/",
    "virtualization_table_name": "netbox_virtualization_vm",
    "api_token": "REPLACE_WITH_NETBOX_TOKEN"
  }
}
```

- **ip2**: Base URL of the NetBox instance.  
- **virtualization_endpoint**: Relative path to the virtualization VM endpoint.  
- **virtualization_table_name**: Target PostgreSQL table name (must match the table created by the SQL file in `SQL/NetBox`).  
- **api_token**: NetBox API token with at least read-only permissions on virtualization objects.

If any required key is missing, the script exits with a non-zero code.

---

### 3. Data Flow and NiFi Orchestration

The end-to-end pipeline follows the same pattern as the HPE iLO Redfish collector:

1. **ExecuteStreamCommand**  
   - Runs `python3 collectors/NetBox/loki-get-vm.py`.  
   - Uses the configuration file for connection parameters.  
   - The script writes a JSON array of VM inventory records to `stdout`.

2. **SplitJson**  
   - JsonPath: `$.*`  
   - Splits the JSON array into one FlowFile per VM record.

3. **EvaluateJsonPath**  
   - Extracts key fields into FlowFile attributes, for example:  
     - `data_type` → `$.data_type`  
     - `vm_id` → `$.id`  
     - `vm_uuid` → `$.custom_fields_uuid` (optional).

4. **RouteOnAttribute**  
   - Routes FlowFiles where `data_type == 'netbox_inventory_vm'` to the NetBox virtualization inventory path.  
   - This mirrors the `data_type`-based routing used in the Redfish collector.

5. **PutDatabaseRecord (UPSERT)**  
   - Uses a `JsonTreeReader` configured with the NetBox VM Avro schema (see section 4).  
   - Target table: `public.netbox_virtualization_vm`.  
   - `Update Keys`: at minimum, `id` (NetBox VM ID).  
   - Mode: insert-or-update (UPSERT).  
     - If a row with the same `id` already exists, it is updated.  
     - Otherwise, a new row is inserted.

This design guarantees that, for each NetBox VM, there is a single, up-to-date row in the inventory table.

---

### 4. JSON Output and Schema

#### 4.1 JSON Output Shape

For each VM, the script generates a flat JSON record with:

- **Core fields:**  
  - `data_type`: always `"netbox_inventory_vm"` for this collector.  
  - `id`: NetBox VM integer ID (primary identifier in the table).  
  - `name`, `display`, `url`, `display_url`.  
  - `status_value`, `status_label`.  
  - `site_*`, `cluster_*`, `device_*` information.  
- **VM attributes:**  
  - `serial`, `role`, `tenant`, `platform`.  
  - `primary_ip`, `primary_ip4`, `primary_ip6`.  
  - `vcpus`, `memory`, `disk`.  
  - `description`, `comments`, `config_template`.  
  - `local_context_data`, `config_context` (serialized JSON as string).
- **Tags:**  
  - Up to 5 tags are flattened as `tags1_*` … `tags5_*` (id, url, display_url, display, name, slug, color).
- **Custom fields:**  
  - `custom_fields_config_instance_uuid`, `custom_fields_config_uuid`, `custom_fields_datastore_name`, `custom_fields_endpoint`.  
  - `custom_fields_guest_os` (aligned with VMware `guest_os` semantics where possible).  
  - `custom_fields_hard_disk_info{1..5}_label/backing/capacity_kb`.  
  - `custom_fields_ip_addresses`, `custom_fields_moid`, `custom_fields_musteri`, `custom_fields_price_id`.  
  - `custom_fields_uuid`, `custom_fields_vm_name`, `custom_fields_vm_olusturulma_tarihi`, `custom_fields_vmx_path`.
- **Timestamps and counters:**  
- `created`, `last_updated`: timestamp fields coming from NetBox (ISO-8601 strings in the raw JSON, converted to timestamps in NiFi/DB).  
- `interface_count`, `virtual_disk_count`.  
- `collection_time`: ISO 8601 timestamp (UTC) representing the snapshot time for this run (string in the raw JSON, converted to timestamp in NiFi/DB).

Example (simplified) VM record:

```json
{
  "data_type": "netbox_inventory_vm",
  "id": 123,
  "name": "vm-example-01",
  "status_value": "active",
  "site_id": 10,
  "cluster_id": 5,
  "device_id": 42,
  "vcpus": 4,
  "memory": 8192,
  "disk": 100,
  "custom_fields_guest_os": "Ubuntu Linux (64-bit)",
  "custom_fields_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "collection_time": "2026-02-12T10:15:30.123456+00:00"
}
```

#### 4.2 Avro Schema for NiFi

- Path: `SQL/json_schemas/NetBox/loki-get-vm.json`  
- Purpose: Used by NiFi `JsonTreeReader` (Schema Access Strategy = `Use 'Schema Text' Property`).  
- Characteristics:
  - Defines all possible fields the script can emit.  
  - Uses unions like `["null", "string"]` or `["null", "long"]` for optional fields.  
  - Ensures NiFi does not drop fields which are absent from early records in a flow.

Additionally, the time fields (`created`, `last_updated`, `collection_time`) are defined as:

```json
{
  "name": "created",
  "type": [
    "null",
    {
      "type": "long",
      "logicalType": "timestamp-millis"
    }
  ]
}
```

with the same pattern applied to `last_updated` and `collection_time`.

In the `JsonTreeReader` controller service, set:

- **Schema Access Strategy**: `Use 'Schema Text' Property`  
- **Schema Text**: contents of `SQL/json_schemas/NetBox/loki-get-vm.json`  
- **Timestamp format**:

```text
yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXX
```

This format matches values such as `2024-10-03T17:56:05.398668+03:00` and `2026-02-12T11:18:43.524089+00:00`, allowing NiFi to parse them into `timestamp-millis` fields.

This is analogous to the Avro schema strategy explained in the Redfish README.

---

### 5. Database Model

#### 5.1 Target Table

- Path to DDL: `SQL/NetBox/loki_get_virtualmachines.sql`  
- Table name: `public.netbox_virtualization_vm`

Key points:

- `id BIGINT PRIMARY KEY`:  
  - Directly corresponds to NetBox VM ID.  
  - Used as the primary key for UPSERT operations.
- All JSON fields described above are mapped 1:1 to table columns.  
- `created`, `last_updated`, `collection_time` are stored as `TIMESTAMPTZ`.  
- Additional indexes:
  - `custom_fields_uuid` (optional, helps joining with other sources such as VMware or hypervisor-level collectors).  
  - `site_id` (optional, for filtering by location).

This layout makes it easy to:

- Join NetBox VM inventory with other virtualization metrics or discovery results.  
- Query current state per VM or per site/cluster.  
- Extend the schema with new fields while keeping NiFi and the collector stable.

---

### 6. How to Run and Test

#### 6.1 Manual Test (Command Line)

1. Ensure `/Datalake_Project/configuration_file.json` is present and contains the `Loki` section.  
2. From the project root:

```bash
python3 collectors/NetBox/loki-get-vm.py > sample_netbox_vms.json
```

3. Inspect the output:

```bash
head -n 50 sample_netbox_vms.json
```

4. Validate that:
   - The output is a valid JSON array.  
   - Each element contains `data_type = "netbox_inventory_vm"` and a non-null `id`.  
   - Critical attributes (e.g. `name`, `status_value`, `custom_fields_guest_os`, `collection_time`) are present.

#### 6.2 NiFi Flow Test

1. Configure a `JsonTreeReader` controller service with the schema from  
   `SQL/json_schemas/NetBox/loki-get-vm.json`.  
2. Build the following flow (simplified):

- `ExecuteStreamCommand` → `SplitJson` → `EvaluateJsonPath` → `RouteOnAttribute` → `PutDatabaseRecord`

3. In `PutDatabaseRecord`:
   - Set the target table to `public.netbox_virtualization_vm`.  
   - Configure `Update Keys` to `id`.  
   - Use an insert-or-update mode that respects these keys.

4. Run the flow twice:
   - First run should insert rows.  
   - Second run (with some changed VM attributes) should update existing rows with the same `id`.

If this behavior is observed, the inventory UPSERT pipeline is working as designed.

---

### 7. Future Extensions

The collector is designed to be easily extended:

- New NetBox fields or custom fields can be added to `generate_vm_record`, the table DDL, and the Avro schema.  
- Additional `data_type` values could be introduced for other NetBox entities (e.g. clusters, tenants) and handled in NiFi using `RouteOnAttribute`.  
- Views can be defined on top of `netbox_virtualization_vm` to provide:
  - Current VM inventory per site/cluster.  
  - Cross-source comparisons between NetBox inventory and hypervisor-level discovery scripts.

By following the same patterns as the Redfish and VMware collectors, this NetBox collector stays consistent with the overall data lake architecture.

