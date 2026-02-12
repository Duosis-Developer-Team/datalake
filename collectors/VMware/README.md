# VMware Raw Data Collectors

This directory contains VMware vSphere data collectors that extract raw data from VMware API with **zero transformation** approach.

## 📋 Overview

The collectors follow a **ham veri (raw data)** approach:
- ✅ Extract data from VMware API objects as-is
- ❌ No calculations or aggregations (except for optimization tables)
- ❌ No unit conversions (bytes, MHz stay as-is)
- ✅ Multiple tables per entity for logical grouping
- ✅ Single JSON output per script with multiple `data_type` values

## 🗂️ Architecture

### Data Types per Entity

Each entity (VM, Host, Cluster, Datacenter) produces multiple data types:

#### VM (Virtual Machine)
1. **vmware_vm_config** - Configuration data (vm.summary.config, vm.config)
2. **vmware_vm_runtime** - Runtime state (vm.runtime, vm.guest, vm.summary.quickStats)
3. **vmware_vm_storage** - VM-Datastore relationships (one row per datastore)
4. **vmware_vm_perf_raw** - Raw performance samples (one row per sample)
5. **vmware_vm_perf_agg** - Aggregated performance (avg/min/max for optimization)

#### Host (ESXi)
1. **vmware_host_hardware** - Hardware configuration (host.hardware, host.summary.hardware)
2. **vmware_host_runtime** - Runtime state (host.runtime, host.summary.quickStats)
3. **vmware_host_storage** - Host-Datastore relationships
4. **vmware_host_perf_raw** - Raw performance samples
5. **vmware_host_perf_agg** - Aggregated performance

#### Cluster
1. **vmware_cluster_config** - Cluster configuration (cluster.configuration, cluster.summary)

#### Datacenter
1. **vmware_datacenter_config** - Datacenter configuration (minimal)
2. **vmware_datacenter_metrics_agg** - Pre-calculated aggregated metrics (optimization table)

## 📊 Database Tables

### Table Naming Convention

- **Raw data tables**: `raw_vmware_<entity>_<type>`
- **Examples**:
  - `raw_vmware_vm_config`
  - `raw_vmware_host_hardware`
  - `raw_vmware_cluster_config`
  - `raw_vmware_datacenter_metrics_agg`

### DDL Files Location

All DDL files are located in: `SQL/VMware/`

```
SQL/VMware/
├── raw_vmware_vm_config.sql
├── raw_vmware_vm_runtime.sql
├── raw_vmware_vm_storage.sql
├── raw_vmware_vm_perf_raw.sql
├── raw_vmware_vm_perf_agg.sql
├── raw_vmware_host_hardware.sql
├── raw_vmware_host_runtime.sql
├── raw_vmware_host_storage.sql
├── raw_vmware_host_perf_raw.sql
├── raw_vmware_host_perf_agg.sql
├── raw_vmware_cluster_config.sql
├── raw_vmware_datacenter_config.sql
└── raw_vmware_datacenter_metrics_agg.sql
```

### Primary Keys

#### Config/Runtime Tables
- `(vcenter_uuid, entity_moid, collection_timestamp)`

#### Storage Relationship Tables
- `(vcenter_uuid, entity_moid, datastore_moid, collection_timestamp)`

#### Performance Raw Tables
- `(vcenter_uuid, entity_moid, counter_id, instance, sample_timestamp)`

#### Performance Aggregated Tables
- `(vcenter_uuid, entity_moid, counter_id, instance, window_start, window_end)`

## 🔄 Data Flow

### Collection Flow

```
VMware vCenter API
  ↓
Collector Script (Python)
  ↓
JSON Array Output (stdout)
  ↓
NiFi ExecuteStreamCommand
  ↓
NiFi SplitJson
  ↓
NiFi RouteOnAttribute (by data_type)
  ↓
NiFi PutDatabaseRecord
  ↓
PostgreSQL Tables
```

### Example Output Structure

A single VM produces approximately 100+ records per collection cycle:

```json
[
  {
    "data_type": "vmware_vm_config",
    "collection_timestamp": "2026-02-12T11:30:00+00:00",
    "vcenter_uuid": "550e8400-...",
    "vm_moid": "vm-1234",
    "name": "web-server-01",
    "num_cpu": 4,
    "memory_size_mb": 8192,
    ...
  },
  {
    "data_type": "vmware_vm_runtime",
    "collection_timestamp": "2026-02-12T11:30:00+00:00",
    "vm_moid": "vm-1234",
    "power_state": "poweredOn",
    "quick_stats_overall_cpu_usage": 1250,
    ...
  },
  {
    "data_type": "vmware_vm_storage",
    "vm_moid": "vm-1234",
    "datastore_moid": "datastore-12",
    "datastore_name": "datastore1",
    "datastore_capacity": 549755813888,
    "committed": 53687091200,
    ...
  },
  {
    "data_type": "vmware_vm_perf_raw",
    "vm_moid": "vm-1234",
    "counter_id": 6,
    "counter_name": "cpu.usage.average",
    "sample_timestamp": "2026-02-12T11:25:00+00:00",
    "value": 1250,
    ...
  },
  ... (50+ more perf_raw samples)
  {
    "data_type": "vmware_vm_perf_agg",
    "vm_moid": "vm-1234",
    "counter_id": 6,
    "value_avg": 1250.0,
    "value_min": 1200,
    "value_max": 1300,
    ...
  },
  ... (15+ more perf_agg records)
]
```

## 📝 Scripts

### New Collectors (Raw Data Approach)

#### `vmware_vm_collector.py`
Collects all VM data types.

**Usage:**
```bash
python3 vmware_vm_collector.py \
  --vmware-ip 10.132.2.184 \
  --vmware-port 443 \
  --vmware-username administrator@vsphere.local \
  --vmware-password 'password'
```

**Output:** JSON array with ~100 records per VM

#### `vmware_host_collector.py`
Collects all ESXi host data types.

**Usage:**
```bash
python3 vmware_host_collector.py \
  --vmware-ip 10.132.2.184 \
  --vmware-port 443 \
  --vmware-username administrator@vsphere.local \
  --vmware-password 'password'
```

**Output:** JSON array with ~100 records per host

#### `vmware_cluster_collector.py`
Collects cluster configuration data.

**Usage:**
```bash
python3 vmware_cluster_collector.py \
  --vmware-ip 10.132.2.184 \
  --vmware-port 443 \
  --vmware-username administrator@vsphere.local \
  --vmware-password 'password'
```

**Output:** JSON array with 1-2 records per cluster

#### `vmware_datacenter_collector.py`
Collects datacenter configuration and aggregated metrics.

**Usage:**
```bash
python3 vmware_datacenter_collector.py \
  --vmware-ip 10.132.2.184 \
  --vmware-port 443 \
  --vmware-username administrator@vsphere.local \
  --vmware-password 'password'
```

**Output:** JSON array with 2 records per datacenter

### Legacy Scripts (Deprecated)

These scripts are kept for reference but will be replaced:
- `vmware_vm_performance_metrics.py` (plain text output)
- `vmware_host_performance_metrics.py` (plain text output)
- `vmware_cluster_performance_metrics.py` (plain text output)
- `vmware_datacenter_performance_metrics.py` (plain text output)

## 🔧 NiFi Configuration

### Universal Flow Pattern

Each collector follows the same NiFi flow pattern:

```
┌─────────────────────────────────┐
│ ExecuteStreamCommand            │
│ Command: python3 <collector.py> │
│ Arguments: --vmware-ip ...      │
└────────────┬────────────────────┘
             │
             ↓
┌─────────────────────────────────┐
│ SplitJson                       │
│ JsonPath Expression: $.*        │
└────────────┬────────────────────┘
             │
             ↓
┌─────────────────────────────────┐
│ EvaluateJsonPath                │
│ Extract: data_type              │
│          collection_timestamp   │
│          vcenter_uuid           │
│          *_moid                 │
└────────────┬────────────────────┘
             │
             ↓
┌─────────────────────────────────┐
│ RouteOnAttribute                │
│ Route by: ${data_type}          │
└────────────┬────────────────────┘
             │
             ├─→ vmware_vm_config ───→ PutDatabaseRecord
             ├─→ vmware_vm_runtime ──→ PutDatabaseRecord
             ├─→ vmware_vm_storage ──→ PutDatabaseRecord
             ├─→ vmware_vm_perf_raw ─→ PutDatabaseRecord
             └─→ vmware_vm_perf_agg ─→ PutDatabaseRecord
```

### PutDatabaseRecord Configuration

**JsonTreeReader Properties:**
- **Schema Access Strategy:** Use 'Schema Text' Property
- **Schema Text:** `${schema.text}` (from lookup service)
- **Schema Name:** `${data_type}`

**Schema Lookup Service Setup:**
Create an AvroSchemaRegistry with mappings:
- Key: `vmware_vm_config`
- Value: Content of `SQL/json_schemas/VMware/vmware_vm_config.json`

Repeat for all 13 data types.

**PutDatabaseRecord Properties:**
- **Record Reader:** JsonTreeReader (configured above)
- **Statement Type:** INSERT
- **Table Name:** `raw_vmware_${data_type:substringAfter('vmware_')}`
- **Database Connection Pool:** PostgreSQL connection pool

## 🗃️ JSON/Avro Schemas

All Avro schemas are located in: `SQL/json_schemas/VMware/`

```
SQL/json_schemas/VMware/
├── vmware_vm_config.json
├── vmware_vm_runtime.json
├── vmware_vm_storage.json
├── vmware_vm_perf_raw.json
├── vmware_vm_perf_agg.json
├── vmware_host_hardware.json
├── vmware_host_runtime.json
├── vmware_host_storage.json
├── vmware_host_perf_raw.json
├── vmware_host_perf_agg.json
├── vmware_cluster_config.json
├── vmware_datacenter_config.json
└── vmware_datacenter_metrics_agg.json
```

### Schema Format

All schemas follow Avro format with:
- Nullable fields: `["null", "type"]`
- Timestamp fields: `{"type": "long", "logicalType": "timestamp-millis"}`
- Array fields: `{"type": "array", "items": "type"}`

### Example Schema Usage in NiFi

```json
{
  "type": "record",
  "name": "vmware_vm_config",
  "namespace": "datalake.vmware",
  "fields": [
    { "name": "data_type", "type": ["null", "string"] },
    { "name": "collection_timestamp", "type": ["null", {"type": "long", "logicalType": "timestamp-millis"}] },
    { "name": "vcenter_uuid", "type": ["null", "string"] },
    ...
  ]
}
```

## 📈 Data Volume Estimates

For a **100 VM environment** with **15 hosts** per 15-minute collection:

| Data Type | Records per Collection | Table Size (approx) |
|-----------|------------------------|---------------------|
| VM Config | 100 | Low (rarely changes) |
| VM Runtime | 100 | Medium (frequent updates) |
| VM Storage | 200 | Medium (2 datastores/VM avg) |
| VM Perf Raw | 15,000 | **High** (partition recommended) |
| VM Perf Agg | 5,000 | Medium-High |
| Host Hardware | 15 | Very Low |
| Host Runtime | 15 | Medium |
| Host Storage | 30 | Low |
| Host Perf Raw | 4,500 | **High** (partition recommended) |
| Host Perf Agg | 1,500 | Medium |
| Cluster Config | 3 | Very Low |
| Datacenter Config | 1 | Very Low |
| Datacenter Metrics Agg | 1 | Low |
| **TOTAL** | **~26,500** | - |

### Partitioning Recommendations

For `*_perf_raw` tables, consider **time-based partitioning**:

```sql
-- Example: Weekly partitions
CREATE TABLE raw_vmware_vm_perf_raw_2026_w07 
  PARTITION OF raw_vmware_vm_perf_raw
  FOR VALUES FROM ('2026-02-10') TO ('2026-02-17');
```

## 🔑 VMware API Object Mapping

### VM Data Sources

| Field | VMware API Source | Example Value |
|-------|-------------------|---------------|
| `name` | `vm.summary.config.name` | "web-server-01" |
| `num_cpu` | `vm.summary.config.numCpu` | 4 |
| `memory_size_mb` | `vm.summary.config.memorySizeMB` | 8192 |
| `power_state` | `vm.runtime.powerState` | "poweredOn" |
| `boot_time` | `vm.runtime.bootTime` | "2026-01-15T08:30:00+00:00" |
| `quick_stats_overall_cpu_usage` | `vm.summary.quickStats.overallCpuUsage` | 1250 (MHz) |
| `quick_stats_guest_memory_usage` | `vm.summary.quickStats.guestMemoryUsage` | 5324 (MB) |
| `datastore_capacity` | `vm.datastore[].summary.capacity` | 549755813888 (bytes) |
| `committed` | `vm.summary.storage.committed` | 53687091200 (bytes) |

**Note:** All values are **AS-IS** from VMware API with no conversion.

### Host Data Sources

| Field | VMware API Source | Example Value |
|-------|-------------------|---------------|
| `uuid` | `host.hardware.systemInfo.uuid` | "4c4c4544-0034-..." |
| `memory_size` | `host.summary.hardware.memorySize` | 274877906944 (bytes) |
| `cpu_mhz` | `host.summary.hardware.cpuMhz` | 2095 |
| `num_cpu_cores` | `host.summary.hardware.numCpuCores` | 32 |
| `connection_state` | `host.runtime.connectionState` | "connected" |
| `in_maintenance_mode` | `host.runtime.inMaintenanceMode` | false |
| `quick_stats_overall_cpu_usage` | `host.summary.quickStats.overallCpuUsage` | 15360 (MHz) |
| `quick_stats_overall_memory_usage` | `host.summary.quickStats.overallMemoryUsage` | 204800 (MB) |

### Performance Counter Mapping

Performance metrics come from `perfManager.QueryPerf()`:

| Counter ID | Counter Name | Group | Unit | Description |
|------------|--------------|-------|------|-------------|
| 6 | cpu.usage.average | cpu | percent | CPU usage percentage |
| 24 | mem.usage.average | mem | percent | Memory usage percentage |
| 143 | disk.read.average | disk | KBps | Disk read rate |
| 144 | disk.write.average | disk | KBps | Disk write rate |
| 143 | net.usage.average | net | KBps | Network usage rate |

**Raw samples** are stored with original counter values.  
**Aggregated values** are calculated by the script (avg/min/max).

## ⚠️ Important Notes

### Zero Transformation Principle

1. **NO unit conversions**
   - Bytes stay as bytes (not converted to GB)
   - MHz stay as MHz (not converted to GHz)
   - Percentages from VMware are raw values (may need division by 100)

2. **NO calculations**
   - No capacity - used = free calculations
   - No aggregations (except in optimization tables)
   - No derived fields (folder path parsing, UUID concatenation)

3. **AS-IS values**
   - All VMware API object fields are extracted as-is
   - Null values remain null
   - Empty strings remain empty strings

### Aggregation Exception

The **only exceptions** to zero transformation:
- `raw_vmware_*_perf_agg` tables: Pre-calculated avg/min/max for query optimization
- `raw_vmware_datacenter_metrics_agg`: Pre-calculated datacenter-wide aggregations

These are **optimization tables** - the same data can be derived from raw tables via SQL.

### Timestamp Format

- **collection_timestamp**: When the script ran (ISO-8601 UTC)
- **sample_timestamp**: When the performance sample was taken (from VMware)
- **window_start/end**: Aggregation window boundaries

All timestamps are stored as ISO-8601 strings in JSON, converted to `TIMESTAMPTZ` in PostgreSQL.

## 🚀 Migration from Legacy Scripts

### Comparison

| Aspect | Legacy Scripts | New Collectors |
|--------|----------------|----------------|
| Output Format | Plain text | JSON array |
| Data Transformation | Multiple conversions | Zero transformation |
| Tables per Entity | 1 | 5 (VM/Host), 1-2 (Cluster/DC) |
| NiFi Integration | Complex parsing | RouteOnAttribute |
| Schema Definition | None | Avro schemas |
| Performance Data | Aggregated only | Raw + Aggregated |
| Extensibility | Limited | High (add data_types) |

### Migration Steps

1. **Create new tables** using DDL files in `SQL/VMware/`
2. **Configure NiFi flows** with new collectors
3. **Run both old and new** collectors in parallel initially
4. **Validate data** in new tables
5. **Switch dashboards** to use new tables
6. **Deprecate old scripts** after validation period

## 📚 References

- VMware vSphere API Documentation: https://developer.vmware.com/apis/vsphere-automation/latest/
- pyVmomi Documentation: https://github.com/vmware/pyvmomi
- Development Template: `docs/development-templates/collector_discovery_template.md`
- Compliance Checklist: `docs/development-templates/collector_discovery_checklist.md`

## 🤝 Contributing

When adding new data types:
1. Define VMware API source clearly
2. Create DDL in `SQL/VMware/`
3. Create Avro schema in `SQL/json_schemas/VMware/`
4. Add extraction function in collector script
5. Update this README with new data_type
6. Add NiFi route for new data_type

## 📞 Support

For questions or issues:
- Check VMware API documentation for field meanings
- Verify DDL matches Avro schema
- Test with small dataset first
- Monitor NiFi bulletins for routing issues
