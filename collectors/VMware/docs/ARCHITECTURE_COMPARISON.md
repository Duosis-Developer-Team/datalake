# VMware Collector Architecture Comparison & Analysis

**Date:** February 15, 2026  
**Author:** Datalake Team  
**Purpose:** Comprehensive analysis of new vs legacy VMware collector architectures

---

## 📊 Executive Summary

This document provides a detailed comparison between the **new raw data collectors** and **legacy performance metrics collectors**, analyzing:
1. Data collection methodologies
2. Data processing approaches
3. SQL table structures and stored data
4. Discovery script compatibility with both architectures

### Key Findings

✅ **New Architecture Advantages:**
- Zero transformation approach preserves data fidelity
- JSON output enables flexible NiFi routing
- Multiple data types per entity provide better data organization
- Raw + aggregated performance data supports both detailed analysis and optimization

⚠️ **Legacy Architecture Issues:**
- Plain text output requires complex parsing
- Unit conversions and calculations happen at collection time (data loss)
- Single table per entity limits data organization
- Only aggregated performance data (no raw samples)

---

## 🏗️ Architecture Comparison

### 1. Data Collection Methodology

#### New Collectors (Raw Data Approach)

**Philosophy:** Extract data AS-IS from VMware API with ZERO transformation.

**Data Flow:**
```
VMware API Object
    ↓
Extract attribute values AS-IS (no conversion)
    ↓
Group into logical data_types
    ↓
Serialize to JSON
    ↓
Output as JSON array
```

**Example: VM Collector (`vmware_vm_collector.py`)**

```python
# Extract configuration AS-IS
def extract_vm_config(vm, vcenter_uuid, collection_timestamp, hierarchy):
    record = {
        "data_type": "vmware_vm_config",
        "memory_size_mb": safe_get_attr(config, 'memorySizeMB'),  # AS-IS (MB)
        "num_cpu": safe_get_attr(config, 'numCpu'),               # AS-IS
        # ... more fields
    }
    return record

# Extract performance samples AS-IS
def extract_vm_perf_raw(vm, vcenter_uuid, ...):
    # Each sample becomes a separate record
    for i, value in enumerate(perf_metric.value):
        record = {
            "data_type": "vmware_vm_perf_raw",
            "counter_id": counter_id,
            "value": value,  # AS-IS from VMware (no conversion)
            "sample_timestamp": sample_time.isoformat(),
        }
        perf_raw_records.append(record)
```

**Key Characteristics:**
- ✅ No unit conversions (bytes stay bytes, MHz stay MHz)
- ✅ No calculations (no derived fields)
- ✅ Preserves all raw values from VMware API
- ✅ Multiple data_types per entity (config, runtime, storage, perf_raw, perf_agg)
- ✅ Performance data includes both raw samples AND aggregates

**Data Types Produced:**

| Entity | Data Types | Purpose |
|--------|------------|---------|
| **VM** | `vmware_vm_config` | Configuration (vm.config, vm.summary.config) |
| | `vmware_vm_runtime` | Runtime state (vm.runtime, vm.guest, quickStats) |
| | `vmware_vm_storage` | VM-Datastore relationships (one row per DS) |
| | `vmware_vm_perf_raw` | Raw performance samples (one row per sample) |
| | `vmware_vm_perf_agg` | Aggregated performance (avg/min/max) |
| **Host** | `vmware_host_hardware` | Hardware config (host.hardware) |
| | `vmware_host_runtime` | Runtime state (host.runtime, quickStats) |
| | `vmware_host_storage` | Host-Datastore relationships |
| | `vmware_host_perf_raw` | Raw performance samples |
| | `vmware_host_perf_agg` | Aggregated performance |
| **Cluster** | `vmware_cluster_config` | Cluster configuration |
| **Datacenter** | `vmware_datacenter_config` | Datacenter configuration |
| | `vmware_datacenter_metrics_agg` | Pre-calculated aggregations |

---

#### Legacy Collectors (Aggregated Metrics Approach)

**Philosophy:** Calculate and convert metrics at collection time, output human-readable text.

**Data Flow:**
```
VMware API Object
    ↓
Extract + Convert Units (bytes→GB, MHz→GHz)
    ↓
Aggregate performance samples immediately
    ↓
Calculate derived fields (capacity - used = free)
    ↓
Format as plain text
```

**Example: Legacy VM Collector (`vmware_vm_performance_metrics.py`)**

```python
def process_vm(dc_name, cluster_name, host_name, host_uuid, vm, ...):
    # Convert units at collection time
    used_space_gb = committed / (1024**3)  # Bytes → GB conversion
    prov_space_gb = (committed + uncommitted) / (1024**3)
    
    # Aggregate performance immediately
    stats = query_metrics(perf_mgr, vm, mids, cmap, start, end, interval)
    cpu = stats.get(cpu_id, {'avg':0,'min':0,'max':0})  # Only aggregates
    
    # Calculate derived fields
    cpu_free = cpu_cap - cpu_used  # Calculation at collection time
    
    # Output as plain text
    return "\n".join([
        f"VMName: {vm_name}",
        f"Used Space GB: {used_space_gb:.2f}",
        f"CPU Usage Avg Mhz: {cpu['avg']}",
        # ...
    ])
```

**Key Characteristics:**
- ❌ Unit conversions (data loss: can't recover original bytes from GB)
- ❌ Calculations (derived fields, can't verify calculation logic later)
- ❌ Only aggregated performance data (raw samples discarded)
- ❌ Plain text output (requires complex parsing in NiFi)
- ❌ Single output format (no data type separation)

**Output Format:**
```
Datacenter: DC1
Cluster: Cluster1
VMHost: esxi01.example.com
VMName: web-server-01
Timestamp: 2026-02-15 10:00
Number of CPUs: 4
Total CPU Capacity Mhz: 8380
CPU Usage Avg Mhz: 1250
Memory Usage Avg perc: 0.65
Used Space GB: 50.00
...
```

---

### 2. Data Processing Methodology

#### New Collectors: Zero Transformation

**Principle:** NO processing at collection time, ALL processing in SQL/views.

**Processing Locations:**

| Task | Legacy (Collection Time) | New (Query Time) |
|------|--------------------------|------------------|
| Unit Conversion | ✓ Python | ✗ SQL Views |
| Aggregation | ✓ Python | ✗ SQL Views |
| Calculations | ✓ Python | ✗ SQL Views |
| Derived Fields | ✓ Python | ✗ SQL Views |

**Example: Capacity Calculation**

**Legacy (Lost flexibility):**
```python
# Conversion happens at collection - original bytes lost
used_space_gb = committed / (1024**3)
```

**New (Maximum flexibility):**
```sql
-- Raw data preserved, convert at query time in any unit needed
SELECT 
    committed AS committed_bytes,                  -- Original value
    committed / (1024^3) AS committed_gb,          -- Gigabytes
    committed / (1024^4) AS committed_tb,          -- Terabytes
    committed / 1000000000 AS committed_gb_decimal -- GB (decimal)
FROM raw_vmware_vm_storage;
```

**Benefits:**
- ✅ Can change unit conversions without re-collection
- ✅ Can verify calculations with raw data
- ✅ Can add new derived fields retroactively
- ✅ Audit trail of original VMware API values

---

#### Legacy Collectors: Transformation at Collection

**Example: Memory Usage Percentage**

**Legacy:**
```python
# Calculation embedded in collection script
cpu_pct = stats.get(cmap['cpu.usage.average']['id'], {'avg':0,'min':0,'max':0})
# If this calculation is wrong, must recollect all data
```

**New:**
```sql
-- Calculation in SQL view, can be changed anytime
SELECT 
    quick_stats_overall_cpu_usage,  -- Raw MHz value preserved
    max_cpu_usage,                   -- Raw max MHz preserved
    CASE 
        WHEN max_cpu_usage > 0 THEN 
            ROUND((quick_stats_overall_cpu_usage::numeric / max_cpu_usage) * 100, 2)
        ELSE NULL 
    END AS cpu_usage_percent  -- Calculated at query time
FROM raw_vmware_vm_runtime r
JOIN raw_vmware_vm_config c USING (vcenter_uuid, vm_moid, collection_timestamp);
```

---

### 3. SQL Table Structure Comparison

#### New SQL Tables: Multi-Table per Entity

**Philosophy:** Logical grouping of related fields into separate tables.

**VM Entity Tables:**

1. **`raw_vmware_vm_config`** - Configuration data (rarely changes)
   - Source: `vm.summary.config`, `vm.config`
   - Update frequency: Low
   - Fields: `num_cpu`, `memory_size_mb`, `uuid`, `guest_id`, etc.
   - Primary Key: `(vcenter_uuid, vm_moid, collection_timestamp)`

2. **`raw_vmware_vm_runtime`** - Runtime state (frequently changes)
   - Source: `vm.runtime`, `vm.guest`, `vm.summary.quickStats`
   - Update frequency: High
   - Fields: `power_state`, `boot_time`, `guest_ip_address`, `quick_stats_overall_cpu_usage`, etc.
   - Primary Key: `(vcenter_uuid, vm_moid, collection_timestamp)`

3. **`raw_vmware_vm_storage`** - VM-Datastore relationships (one row per datastore)
   - Source: `vm.datastore[]`, `vm.summary.storage`
   - Update frequency: Medium
   - Fields: `datastore_moid`, `datastore_name`, `datastore_capacity`, `committed`, etc.
   - Primary Key: `(vcenter_uuid, vm_moid, datastore_moid, collection_timestamp)`

4. **`raw_vmware_vm_perf_raw`** - Raw performance samples (one row per sample)
   - Source: `perfManager.QueryPerf()`
   - Update frequency: Very High (every 5 minutes)
   - Fields: `counter_id`, `counter_name`, `instance`, `sample_timestamp`, `value`
   - Primary Key: `(vcenter_uuid, vm_moid, counter_id, instance, sample_timestamp)`
   - **Partitioning recommended** for large environments

5. **`raw_vmware_vm_perf_agg`** - Aggregated performance (optimization table)
   - Source: Calculated from perf_raw by script
   - Update frequency: High
   - Fields: `counter_id`, `window_start`, `window_end`, `value_avg`, `value_min`, `value_max`
   - Primary Key: `(vcenter_uuid, vm_moid, counter_id, instance, window_start, window_end)`

**Advantages:**
- ✅ Smaller table sizes (related fields grouped together)
- ✅ Better query performance (only join needed tables)
- ✅ Easier to maintain (update frequency per table)
- ✅ Better indexing strategies (optimized per data type)

**Example Query:**
```sql
-- Get VM inventory without performance data (fast)
SELECT * FROM vmware_vm_inventory 
WHERE collection_timestamp > NOW() - INTERVAL '1 day';

-- Get VM performance metrics (separate query)
SELECT * FROM vmware_vm_metrics
WHERE collection_timestamp > NOW() - INTERVAL '1 hour';
```

---

#### Legacy SQL Tables: Inferred from Views

**Note:** Legacy collectors output plain text, so SQL tables are likely custom-designed per NiFi flow.

Based on the new view definitions (`vmware_vm_inventory`, `vmware_vm_metrics`), the legacy approach likely had:
- Single table per entity with all fields combined
- Pre-calculated fields stored directly
- Less flexibility for querying

**Inferred Legacy Structure:**
```sql
-- Hypothetical legacy table (inferred)
CREATE TABLE vmware_vm_metrics_legacy (
    collection_timestamp TIMESTAMPTZ,
    datacenter TEXT,
    cluster TEXT,
    vmhost TEXT,
    vmname TEXT,
    num_cpus INT,
    cpu_capacity_mhz BIGINT,       -- Pre-calculated
    cpu_used_mhz BIGINT,            -- Pre-calculated
    cpu_free_mhz BIGINT,            -- Pre-calculated (can't verify)
    memory_capacity_gb NUMERIC,    -- Converted (lost original bytes)
    memory_used_gb NUMERIC,        -- Converted
    disk_usage_avg_kbps NUMERIC,   -- Aggregated only (no raw samples)
    -- ...
);
```

**Issues:**
- ❌ Can't separate config changes from runtime changes
- ❌ Can't query raw performance samples
- ❌ Can't verify pre-calculated fields
- ❌ Large table size (all fields in one table)

---

#### SQL Views: Query Optimization Layer

**New architecture provides SQL views** for common query patterns:

1. **`vmware_vm_inventory`** - Combines config + runtime + storage
   - Joins: `raw_vmware_vm_config`, `raw_vmware_vm_runtime`, `raw_vmware_vm_storage`
   - Purpose: Single view for inventory/configuration queries
   - Features: Human-readable units (GB conversion), calculated percentages

2. **`vmware_vm_metrics`** - Pivots performance data into columns
   - Source: `raw_vmware_vm_perf_agg`
   - Purpose: Time-series metrics per VM
   - Features: All key metrics as columns (CPU, memory, disk, network)

3. **`vmware_host_inventory`**, **`vmware_host_metrics`**, etc.
   - Similar patterns for Host, Cluster, Datacenter

**View Benefits:**
- ✅ Encapsulates complex joins
- ✅ Provides human-readable units
- ✅ Maintains raw data integrity
- ✅ Can be updated without touching raw tables

---

### 4. Data Volume & Storage Analysis

**Estimated records per 15-minute collection (100 VM environment, 15 hosts):**

| Data Type | Records | Size Impact | Legacy Equivalent |
|-----------|---------|-------------|-------------------|
| VM Config | 100 | Low | Included in single VM table |
| VM Runtime | 100 | Medium | Included in single VM table |
| VM Storage | 200 | Medium | Included in single VM table |
| **VM Perf Raw** | **15,000** | **HIGH** | ❌ Not available |
| VM Perf Agg | 5,000 | Medium-High | ✓ Similar data |
| Host Hardware | 15 | Very Low | Included in single Host table |
| Host Runtime | 15 | Medium | Included in single Host table |
| Host Storage | 30 | Low | Included in single Host table |
| **Host Perf Raw** | **4,500** | **HIGH** | ❌ Not available |
| Host Perf Agg | 1,500 | Medium | ✓ Similar data |
| **TOTAL** | **~26,500** | - | **~215** (est.) |

**Key Differences:**
- New: **26,500 records** (includes raw samples)
- Legacy: **~215 records** (only aggregated metrics)
- New storage is ~120x more records, but provides:
  - ✅ Raw performance samples for detailed analysis
  - ✅ Historical performance trends
  - ✅ Anomaly detection capabilities
  - ✅ Data integrity verification

**Storage Recommendations:**
- Partition `*_perf_raw` tables by time (weekly or monthly)
- Implement data retention policies (e.g., keep raw samples for 30 days)
- Archive older aggregated data for long-term trends

---

## 🔍 Discovery Script Compatibility Analysis

### Current Discovery Script

**Location:** `collectors/VMware/discovery/vmware-discovery.py`  
**Status:** ✅ PRODUCTION (v5)

**Purpose:**
- Discovers VMware infrastructure hierarchy (vCenter → Datacenter → Cluster → Host → VM)
- Outputs JSON with data_type labels for NiFi routing

**Data Types Produced:**
- `vmware_inventory_vcenter`
- `vmware_inventory_datacenter`
- `vmware_inventory_cluster`
- `vmware_inventory_host`
- `vmware_inventory_vm`

---

### Compatibility with New Collectors

**Analysis:**

✅ **FULLY COMPATIBLE** - Discovery script uses the same architectural principles as new collectors:

1. **JSON Output Format**
   - Discovery: JSON array with `data_type` field
   - New collectors: JSON array with `data_type` field
   - ✓ Both use same NiFi routing pattern

2. **Identifier Fields**
   - Discovery: `vcenter_uuid`, `component_moid`
   - New collectors: `vcenter_uuid`, `vm_moid`/`host_moid`/`cluster_moid`
   - ✓ Consistent naming convention

3. **Zero Transformation**
   - Discovery: Extracts hierarchy AS-IS
   - New collectors: Extract attributes AS-IS
   - ✓ Both follow raw data principle

**Integration Pattern:**

```
┌─────────────────────────────────┐
│ Discovery Script (v5)           │
│ Output: Inventory hierarchy     │
│ data_type: vmware_inventory_*   │
└────────────┬────────────────────┘
             │
             ↓
┌─────────────────────────────────┐
│ NiFi: RouteOnAttribute          │
│ Route by: ${data_type}          │
└────────────┬────────────────────┘
             │
             ├─→ vmware_inventory_vcenter → raw_vmware_inventory_vcenter
             ├─→ vmware_inventory_vm → raw_vmware_inventory_vm
             └─→ ... (other inventory tables)

┌─────────────────────────────────┐
│ VM Collector (new)              │
│ Output: VM metrics              │
│ data_type: vmware_vm_*          │
└────────────┬────────────────────┘
             │
             ↓
┌─────────────────────────────────┐
│ NiFi: RouteOnAttribute          │
│ Route by: ${data_type}          │
└────────────┬────────────────────┘
             │
             ├─→ vmware_vm_config → raw_vmware_vm_config
             ├─→ vmware_vm_runtime → raw_vmware_vm_runtime
             └─→ vmware_vm_perf_raw → raw_vmware_vm_perf_raw
```

**JOIN Operations:**

Discovery + collectors can be joined on common keys:

```sql
-- Join discovery inventory with VM config
SELECT 
    inv.name AS vm_name,
    inv.parent_component_moid AS host_moid,
    inv.status,
    cfg.num_cpu,
    cfg.memory_size_mb,
    cfg.guest_full_name
FROM raw_vmware_inventory_vm inv
JOIN raw_vmware_vm_config cfg 
    ON inv.vcenter_uuid = cfg.vcenter_uuid 
    AND inv.component_moid = cfg.vm_moid
WHERE inv.collection_timestamp = (
    SELECT MAX(collection_timestamp) FROM raw_vmware_inventory_vm
);
```

---

### Compatibility with Legacy Collectors

**Analysis:**

⚠️ **INCOMPATIBLE** - Discovery script and legacy collectors use different paradigms:

1. **Output Format Mismatch**
   - Discovery: JSON with structured `data_type`
   - Legacy: Plain text with key-value pairs
   - ✗ Requires different NiFi processors

2. **NiFi Integration**
   - Discovery: Simple `RouteOnAttribute` by `data_type`
   - Legacy: Complex text parsing with `ExtractText` + `SplitText`
   - ✗ Different flow patterns

3. **Identifier Format**
   - Discovery: `vcenter_uuid`, `component_moid` (VMware managed object IDs)
   - Legacy: Custom concatenated UUIDs (`VirtualMachine-{moid}:{instanceUuid}`)
   - ✗ JOIN operations require custom mapping

**Integration Challenges:**

```
Discovery (JSON) + Legacy Collectors (Plain Text)
        ↓                           ↓
   Different NiFi flows needed
        ↓                           ↓
   Different table structures
        ↓                           ↓
   Complex JOIN operations with UUID mapping
```

**Example JOIN Complexity:**

```sql
-- Complex join between discovery and legacy data
SELECT 
    inv.name,
    inv.component_moid,
    leg.cpu_usage_avg_mhz
FROM raw_vmware_inventory_vm inv
JOIN vmware_vm_metrics_legacy leg 
    ON CONCAT('VirtualMachine-', inv.component_moid, ':', inv.component_uuid) = leg.vm_uuid
    -- ↑ Complex string manipulation required
WHERE inv.collection_timestamp > NOW() - INTERVAL '1 hour';
```

---

## 📈 Comparative Benefits Analysis

### New Collectors

**Strengths:**
1. ✅ **Data Fidelity**: Raw VMware API values preserved
2. ✅ **Flexibility**: Unit conversions and calculations in SQL (changeable)
3. ✅ **Granularity**: Raw performance samples + aggregates
4. ✅ **Organization**: Logical data type separation
5. ✅ **Integration**: Simple NiFi routing with JSON
6. ✅ **Auditability**: Can verify all calculations against source data
7. ✅ **Extensibility**: Easy to add new data types
8. ✅ **Discovery Compatible**: Works seamlessly with discovery script

**Weaknesses:**
1. ⚠️ Higher storage requirements (raw samples)
2. ⚠️ More complex SQL queries (multiple table joins)
3. ⚠️ Requires view layer for human-readable units

**Best For:**
- ✅ Data lake / data warehouse environments
- ✅ Advanced analytics and ML workloads
- ✅ Audit and compliance requirements
- ✅ Long-term data retention
- ✅ Integration with discovery data

---

### Legacy Collectors

**Strengths:**
1. ✅ Lower storage requirements (only aggregates)
2. ✅ Human-readable output (no conversion needed)
3. ✅ Simple single-table structure

**Weaknesses:**
1. ❌ Data loss (original values unrecoverable)
2. ❌ No flexibility (conversions/calculations fixed)
3. ❌ No raw samples (can't do detailed analysis)
4. ❌ Plain text output (complex NiFi parsing)
5. ❌ Discovery incompatible (different paradigm)
6. ❌ Hard to extend (output format changes break parsers)
7. ❌ Limited auditability (can't verify calculations)

**Best For:**
- ⚠️ Legacy systems (not recommended for new deployments)
- ⚠️ Simple monitoring use cases (basic alerting only)

---

## 🎯 Recommendations

### For New Deployments

**Use new collectors exclusively:**
1. Deploy `vmware_vm_collector.py`, `vmware_host_collector.py`, etc.
2. Use discovery script (`vmware-discovery.py`) for hierarchy
3. Create all `raw_vmware_*` tables
4. Configure NiFi with `RouteOnAttribute` pattern
5. Use provided SQL views for reporting

### For Existing Deployments

**Migration path:**
1. **Phase 1**: Deploy new collectors in parallel with legacy
2. **Phase 2**: Validate data in new tables
3. **Phase 3**: Update dashboards/reports to use new tables
4. **Phase 4**: Deprecate legacy collectors
5. **Phase 5**: Remove legacy collectors after validation period

### Discovery Script Usage

**Current state:**
- ✅ Keep `discovery/vmware-discovery.py` as production script
- ✅ Use with new collectors for complete infrastructure view
- ✅ JOIN discovery data with collector data on `component_moid`

**Recommendation:**
- No changes needed to discovery script
- Already compatible with new collector architecture

---

## 🔗 Data Relationships

### Entity Relationship Diagram

```
┌─────────────────────┐
│ raw_vmware_inventory│
│      _vcenter       │
└──────────┬──────────┘
           │
           ├─→ Datacenter ─→ raw_vmware_datacenter_config
           │                 raw_vmware_datacenter_metrics_agg
           │
           ├─→ Cluster ─────→ raw_vmware_cluster_config
           │
           ├─→ Host ────────→ raw_vmware_host_hardware
           │                  raw_vmware_host_runtime
           │                  raw_vmware_host_storage
           │                  raw_vmware_host_perf_raw
           │                  raw_vmware_host_perf_agg
           │
           └─→ VM ──────────→ raw_vmware_vm_config
                              raw_vmware_vm_runtime
                              raw_vmware_vm_storage
                              raw_vmware_vm_perf_raw
                              raw_vmware_vm_perf_agg
```

### Key Relationships

```sql
-- Discovery → VM Config
raw_vmware_inventory_vm.component_moid = raw_vmware_vm_config.vm_moid

-- VM Config → VM Runtime (same collection timestamp)
raw_vmware_vm_config.{vcenter_uuid, vm_moid, collection_timestamp} =
raw_vmware_vm_runtime.{vcenter_uuid, vm_moid, collection_timestamp}

-- VM → Datastore (one-to-many)
raw_vmware_vm_storage.vm_moid → multiple datastore_moid records

-- VM → Performance Raw (one-to-many)
raw_vmware_vm_perf_raw.vm_moid → multiple counter samples

-- VM → Performance Agg (one-to-many)
raw_vmware_vm_perf_agg.vm_moid → multiple counter aggregates
```

---

## 📝 Conclusion

**The new collector architecture provides:**
1. ✅ **Superior data quality** through zero transformation
2. ✅ **Maximum flexibility** for analysis and reporting
3. ✅ **Complete compatibility** with discovery script
4. ✅ **Future-proof design** for extensibility
5. ✅ **Production-ready** with comprehensive SQL views

**The legacy collectors should be:**
- ⚠️ Deprecated for new deployments
- ⚠️ Migrated away from in existing deployments
- ⚠️ Kept in `deprecated/` folder for reference only

**Discovery script:**
- ✅ Continue using as production script
- ✅ Fully compatible with new collector architecture
- ✅ No modifications needed

---

## 📚 References

- [VMware Collector README](./README.md)
- [Legacy Collectors Documentation](./deprecated/README.md)
- [Discovery Script](./discovery/vmware-discovery.py)
- [SQL Table Definitions](../../SQL/VMware/)
- [SQL Views](../../SQL/VMware/view_*.sql)

---

**Last Updated:** February 15, 2026  
**Status:** ✅ Production Ready
