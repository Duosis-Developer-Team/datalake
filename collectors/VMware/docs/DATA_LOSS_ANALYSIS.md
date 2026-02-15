# VMware Collector Data Loss Analysis

**Date:** February 15, 2026  
**Critical Assessment:** Migration Impact Analysis  
**Status:** ⚠️ ACTION REQUIRED

---

## 🔴 Executive Summary

This document identifies data fields present in **legacy collectors** but **MISSING or INACCESSIBLE** in **new collectors**.

### Critical Findings

| Finding | Severity | Impact | Mitigation Available |
|---------|----------|--------|---------------------|
| Entity Names (DC/Cluster/Host) | 🔴 **CRITICAL** | Cannot display human-readable names | ✅ YES - Via Discovery Script |
| VM Folder Path | 🟡 **MEDIUM** | Lost organizational hierarchy | ⚠️ PARTIAL - Can add to collector |
| Host UUID in VM Records | 🟡 **MEDIUM** | Need JOIN for host identification | ✅ YES - Via host_moid |
| Power Metrics (Host) | 🟡 **MEDIUM** | Power consumption data lost | ⚠️ PARTIAL - Can add counter |
| vCenter FQDN/Identifier | 🟢 **LOW** | Less flexible vCenter naming | ✅ YES - Can use about.fullName |
| Calculated "Free" Fields | 🟢 **LOW** | Convenience fields lost | ✅ YES - SQL can calculate |

**TOTAL CRITICAL ISSUES:** 1  
**TOTAL MEDIUM ISSUES:** 3  
**TOTAL LOW ISSUES:** 2

---

## 📊 Detailed Field-by-Field Comparison

### 1. VM Collector Comparison

#### 🔴 CRITICAL: Entity Names Missing

**Legacy Output:**
```python
Datacenter: DC1                    # ← Datacenter NAME
Cluster: Cluster-Production        # ← Cluster NAME
VMHost: esxi01.example.com         # ← Host NAME
VMName: web-server-01
```

**New Output:**
```json
{
  "datacenter_moid": "datacenter-21",  # ← Only MOID
  "cluster_moid": "domain-c7",         # ← Only MOID
  "host_moid": "host-32",              # ← Only MOID
  "vm_moid": "vm-1234",
  "name": "web-server-01"              # ✓ VM name exists
}
```

**IMPACT:**
- ❌ Cannot display "Datacenter: DC1" without additional lookup
- ❌ Cannot display "Cluster: Cluster-Production" without lookup
- ❌ Cannot display "VMHost: esxi01.example.com" without lookup
- ❌ Dashboards/reports showing names will break

**MITIGATION:**
✅ **SOLUTION EXISTS** - Use Discovery Script

```sql
-- JOIN with discovery data to get names
SELECT 
    vm.vm_moid,
    vm.name AS vm_name,
    dc_inv.name AS datacenter_name,
    cl_inv.name AS cluster_name,
    host_inv.name AS host_name
FROM raw_vmware_vm_config vm
JOIN raw_vmware_inventory_datacenter dc_inv 
    ON vm.datacenter_moid = dc_inv.component_moid
    AND vm.vcenter_uuid = dc_inv.vcenter_uuid
JOIN raw_vmware_inventory_cluster cl_inv 
    ON vm.cluster_moid = cl_inv.component_moid
    AND vm.vcenter_uuid = cl_inv.vcenter_uuid
JOIN raw_vmware_inventory_host host_inv 
    ON vm.host_moid = host_inv.component_moid
    AND vm.vcenter_uuid = host_inv.vcenter_uuid;
```

**ACTION REQUIRED:**
1. ✅ Discovery script MUST run before/alongside collectors
2. ✅ All queries MUST JOIN with inventory tables
3. ✅ Update all dashboards to use JOIN pattern
4. ⚠️ Discovery data must be kept in sync (same collection frequency)

---

#### 🟡 MEDIUM: VM Folder Path Missing

**Legacy Output:**
```python
Folder: production/web-servers      # ← Folder hierarchy path
```

**New Output:**
```json
{
  "vm_path_name": "[datastore1] web-server-01/web-server-01.vmx"  # ← Datastore path only
}
```

**IMPACT:**
- ❌ Lost VM organizational hierarchy (folder structure)
- ❌ Cannot filter/group by folder in reports
- ❌ Compliance reports requiring folder grouping will fail

**EXTRACTION LOGIC (Legacy):**
```python
# Legacy parsing of folder from vmx path
vmx = vm.summary.config.vmPathName or ''
try:
    folder = vmx.split(']')[1].rsplit('/',1)[0].lstrip('/')
except:
    folder = ''
```

**MITIGATION:**
⚠️ **PARTIAL SOLUTION** - Add to collector OR use discovery

**Option 1: Add to VM Config Extraction**
```python
# Add to vmware_vm_collector.py
def extract_vm_config(vm, vcenter_uuid, collection_timestamp, hierarchy):
    # ... existing code ...
    
    # Parse folder from vmx path
    vmx = safe_get_attr(vm.summary.config, 'vmPathName', '')
    folder_path = ''
    try:
        if vmx:
            folder_path = vmx.split(']')[1].rsplit('/', 1)[0].lstrip('/')
    except:
        pass
    
    record = {
        # ... existing fields ...
        "vm_path_name": vmx,
        "folder_path": folder_path,  # ← NEW FIELD
    }
```

**Option 2: Get from vm.parent hierarchy**
```python
# Better approach - traverse folder hierarchy
def get_folder_path(vm):
    path_parts = []
    entity = vm.parent
    while entity:
        if isinstance(entity, vim.Folder):
            if entity.name not in ['vm', 'Datacenters']:  # Skip default folders
                path_parts.append(entity.name)
        entity = getattr(entity, 'parent', None)
    return '/'.join(reversed(path_parts))
```

**ACTION REQUIRED:**
1. ⚠️ Decide if folder path is business-critical
2. ⚠️ If yes, add to collector (recommended Option 2)
3. ⚠️ Update DDL: `ALTER TABLE raw_vmware_vm_config ADD COLUMN folder_path TEXT;`

---

#### 🟡 MEDIUM: ESXi System UUID Not in VM Record

**Legacy Output:**
```python
ESXi System UUID: 4c4c4544-0034-...  # ← Host UUID directly in VM record
```

**New Output:**
```json
{
  "vm_moid": "vm-1234",
  "host_moid": "host-32"  # ← Only host MOID reference
}
```

**IMPACT:**
- ❌ Need JOIN to get host UUID
- ❌ Cannot directly identify physical host from VM record
- ❌ Migration tracking by host UUID requires extra query

**MITIGATION:**
✅ **SOLUTION EXISTS** - JOIN with host hardware table

```sql
-- Get host UUID for VMs
SELECT 
    vm.vm_moid,
    vm.name AS vm_name,
    vm.host_moid,
    host_hw.uuid AS esxi_system_uuid
FROM raw_vmware_vm_config vm
JOIN raw_vmware_host_hardware host_hw 
    ON vm.host_moid = host_hw.host_moid
    AND vm.vcenter_uuid = host_hw.vcenter_uuid
WHERE vm.collection_timestamp = (
    SELECT MAX(collection_timestamp) FROM raw_vmware_vm_config
);
```

**NOTE:**
- ✅ All data is available, just requires JOIN
- ✅ Normalized design is actually better (no redundancy)
- ⚠️ Queries become more complex

**ACTION REQUIRED:**
1. ✅ Update all queries to JOIN with host table if host UUID needed
2. ✅ Document JOIN pattern in view definitions
3. ✅ Consider creating view with pre-joined data

---

#### 🟢 LOW: Custom UUID Format

**Legacy Output:**
```python
UUID: VirtualMachine-vm-1234:502f1234-5678-...  # ← Custom concatenated format
```

**New Output:**
```json
{
  "vm_moid": "vm-1234",           # ← Separate fields
  "uuid": "502f1234-5678-...",
  "instance_uuid": "502f1234-5678-..."
}
```

**IMPACT:**
- ⚠️ Systems using custom UUID format will need UPDATE
- ⚠️ JOIN operations expecting `VirtualMachine-{moid}:{uuid}` format will fail

**MITIGATION:**
✅ **EASY FIX** - SQL concatenation

```sql
-- Recreate legacy UUID format if needed
SELECT 
    vm_moid,
    uuid,
    instance_uuid,
    CONCAT('VirtualMachine-', vm_moid, ':', instance_uuid) AS legacy_uuid_format
FROM raw_vmware_vm_config;
```

**ACTION REQUIRED:**
1. ✅ Identify systems using legacy UUID format
2. ✅ Update those systems to use separate moid/uuid fields
3. ✅ OR create SQL view with legacy format for backward compatibility

---

#### 🟢 LOW: Calculated Fields

**Legacy Output:**
```python
Total CPU Capacity Mhz: 0          # ← Hardcoded to 0 (useless!)
Total Memory Capacity GB: 0.00     # ← Hardcoded to 0 (useless!)
CPU GHz Free: {calculated}         # ← capacity - used
Memory Free GB: {calculated}       # ← capacity - used
Used Space GB: {committed / 1024^3}
Provisioned Space GB: {(committed + uncommitted) / 1024^3}
```

**New Output:**
```json
{
  "memory_size_mb": 8192,           # ← Raw MB value
  "committed": 53687091200,         # ← Raw bytes
  "uncommitted": 10737418240        # ← Raw bytes
}
```

**IMPACT:**
- ✅ NO REAL IMPACT - Legacy "Total CPU/Memory Capacity" were hardcoded to 0!
- ✅ All calculations can be done in SQL with MORE flexibility

**MITIGATION:**
✅ **SUPERIOR SOLUTION** - SQL views

```sql
-- Better than legacy: accurate calculations with multiple unit options
SELECT 
    vm_moid,
    memory_size_mb,
    memory_size_mb / 1024.0 AS memory_size_gb,           -- GB
    memory_size_mb / 1024.0 / 1024.0 AS memory_size_tb,  -- TB
    
    committed AS committed_bytes,
    committed / POWER(1024, 3) AS committed_gb_binary,   -- GiB
    committed / POWER(1000, 3) AS committed_gb_decimal,  -- GB
    
    (committed + uncommitted) AS provisioned_bytes,
    (committed + uncommitted) / POWER(1024, 3) AS provisioned_gb
FROM raw_vmware_vm_storage;
```

**ADVANTAGE OF NEW:**
- ✅ Can change unit conversions without re-collection
- ✅ Can use binary (1024) or decimal (1000) units
- ✅ Original values preserved for audit

**ACTION REQUIRED:**
1. ✅ Create SQL views for common calculations
2. ✅ Use views in dashboards (already done)

---

### 2. Host Collector Comparison

#### 🟡 MEDIUM: Power Metrics Missing

**Legacy Collector:**
```python
desired = [
    'cpu.usage.average', 'mem.usage.average',
    'disk.read.average', 'disk.write.average',
    'net.usage.average', 
    'power.power.average'  # ← Power consumption counter
]

# Output:
Power Usage: 450  # ← Average watts
```

**New Collector:**
```python
desired_counters = [
    'cpu.usage.average',
    'mem.usage.average',
    'disk.read.average',
    'disk.write.average',
    'net.usage.average'
    # ← NO power.power.average!
]
```

**IMPACT:**
- ❌ Power consumption data NOT collected
- ❌ Energy efficiency reports will fail
- ❌ Cannot track datacenter power usage trends

**MITIGATION:**
⚠️ **EASY FIX** - Add counter to new collector

```python
# In vmware_host_collector.py line ~419
desired_counters = [
    'cpu.usage.average',
    'mem.usage.average',
    'disk.read.average',
    'disk.write.average',
    'net.usage.average',
    'power.power.average'  # ← ADD THIS
]
```

**NOTE:**
- ⚠️ Power metrics may not be available on all hosts
- ⚠️ Requires compatible hardware (IPMI, iLO, iDRAC support)
- ⚠️ If counter not available, collection will still succeed (counter just won't have data)

**ACTION REQUIRED:**
1. ⚠️ **CRITICAL**: Add `power.power.average` to new host collector
2. ⚠️ Test in production environment (some hosts may not support power metrics)
3. ⚠️ Update host perf counter list in README

---

#### 🟢 LOW: vCenter Identifier/FQDN

**Legacy Datacenter Collector:**
```python
# Advanced setting for identifier
try:
    opts = {opt.key: opt.value for opt in content.setting.QueryOptions()
            if opt.key in ('config.vpxd.hostnameUrl','VirtualCenter.FQDN')}
    identifier = opts.get('config.vpxd.hostnameUrl') or opts.get('VirtualCenter.FQDN') or vc
except Exception:
    identifier = vc

# Output:
Datacenter: vcenter.example.com  # ← FQDN from advanced settings
```

**New Collectors:**
```python
vcenter_uuid = content.about.instanceUuid  # ← Uses UUID only
```

**IMPACT:**
- ⚠️ vCenter identified by UUID instead of hostname/FQDN
- ⚠️ Less human-readable in reports
- ⚠️ Cannot easily group by vCenter name in dashboards

**MITIGATION:**
✅ **MULTIPLE OPTIONS**

**Option 1: Use about.fullName**
```python
vcenter_uuid = content.about.instanceUuid
vcenter_name = content.about.fullName  # "VMware vCenter Server 8.0.2 build-12345"
```

**Option 2: Use hostname from connection**
```python
vcenter_uuid = content.about.instanceUuid
vcenter_hostname = args.vmware_ip  # Hostname used for connection
```

**Option 3: Store vCenter metadata separately**
```python
# Create vcenter_info table
vcenter_record = {
    "vcenter_uuid": content.about.instanceUuid,
    "vcenter_hostname": args.vmware_ip,
    "vcenter_fqdn": get_advanced_setting('config.vpxd.hostnameUrl'),
    "vcenter_name": content.about.name,
    "vcenter_full_name": content.about.fullName,
    "vcenter_version": content.about.version,
    "vcenter_build": content.about.build,
}
```

**ACTION REQUIRED:**
1. ✅ Decide on vCenter identification strategy
2. ⚠️ If FQDN is critical, add vCenter metadata collection
3. ✅ Discovery script already captures vCenter info (can use that)

---

### 3. Cluster Collector Comparison

**Legacy Cluster Collector:**
- Aggregates metrics from all hosts in cluster
- Outputs computed totals (capacity, used, free)

**New Cluster Collector:**
- Stores cluster configuration only
- NO performance aggregation

**IMPACT:**
- ⚠️ Cluster-level aggregated metrics not pre-computed
- ⚠️ Need SQL aggregation queries

**MITIGATION:**
✅ **SOLUTION EXISTS** - SQL aggregation is better

```sql
-- Cluster-level metrics via SQL (more flexible)
SELECT 
    cluster_moid,
    SUM(hw.memory_size) AS total_memory_bytes,
    SUM(hw.num_cpu_cores * hw.cpu_mhz) AS total_cpu_mhz,
    AVG(rt.quick_stats_overall_cpu_usage) AS avg_cpu_usage_mhz,
    SUM(rt.quick_stats_overall_memory_usage) AS total_memory_used_mb
FROM raw_vmware_host_hardware hw
JOIN raw_vmware_host_runtime rt 
    ON hw.host_moid = rt.host_moid
    AND hw.vcenter_uuid = rt.vcenter_uuid
    AND hw.collection_timestamp = rt.collection_timestamp
GROUP BY cluster_moid;
```

**NOTE:**
- ✅ SQL aggregation is more flexible (can aggregate different time windows)
- ✅ Pre-computed aggregates can still be added if needed
- ✅ Consider creating materialized views for performance

**ACTION REQUIRED:**
1. ✅ Document cluster aggregation queries
2. ✅ Create SQL views for common cluster metrics
3. ⚠️ If pre-computed aggregates are critical, add to collector

---

### 4. Datacenter Collector Comparison

**Similar to Cluster:**
- Legacy: Pre-computed datacenter-wide aggregates
- New: Configuration + datacenter_metrics_agg table (optimization)

**STATUS:**
✅ New collector DOES include `vmware_datacenter_metrics_agg` data type!

**NO DATA LOSS** - Aggregates are preserved.

---

## 🎯 Summary of Required Actions

### Immediate Actions (Critical)

| Action | Priority | Effort | Component |
|--------|----------|--------|-----------|
| **Enable Discovery Script** | 🔴 CRITICAL | Low | Infrastructure |
| Document JOIN patterns for names | 🔴 CRITICAL | Low | Documentation |
| Update dashboards to use JOINs | 🔴 CRITICAL | High | Dashboards |
| Add power metrics to host collector | 🟡 MEDIUM | Low | Collector Code |
| Decide on folder path requirement | 🟡 MEDIUM | Low | Business Decision |

### Optional Improvements

| Action | Priority | Effort | Benefit |
|--------|----------|--------|---------|
| Add folder_path to VM collector | 🟡 MEDIUM | Medium | Organizational hierarchy |
| Create convenience views | 🟢 LOW | Medium | Query simplification |
| Add vCenter metadata collection | 🟢 LOW | Low | Better identification |

---

## 📝 Migration Checklist

### Before Migration

- [ ] Ensure discovery script is deployed and running
- [ ] Test discovery + collector JOIN queries
- [ ] Identify dashboards using entity names
- [ ] Identify reports using folder paths
- [ ] Check if power metrics are business-critical
- [ ] Verify vCenter identification requirements

### During Migration

- [ ] Run legacy and new collectors in parallel
- [ ] Compare data availability
- [ ] Update all dashboards to use JOINs
- [ ] Test power metrics on sample hosts
- [ ] Validate folder path extraction (if added)

### After Migration

- [ ] Verify all reports working
- [ ] Monitor query performance (JOINs may be slower)
- [ ] Document new query patterns
- [ ] Train team on new table structure
- [ ] Archive legacy collectors

---

## 🔗 Related Documents

- [Architecture Comparison](./ARCHITECTURE_COMPARISON.md)
- [Collector README](./README.md)
- [Discovery Script](./discovery/vmware-discovery.py)
- [SQL Views](../../SQL/VMware/view_*.sql)

---

## ✅ Conclusion

### Data Loss Summary

**NO CRITICAL DATA LOSS** - All data is recoverable with proper JOINs and SQL.

**Key Points:**
1. ✅ **Entity names**: Available via Discovery Script (JOIN required)
2. ⚠️ **Folder path**: Can be added to collector if needed
3. ✅ **Host UUID**: Available via JOIN with host tables
4. ⚠️ **Power metrics**: Should be added to host collector
5. ✅ **Calculated fields**: Better handled in SQL

**Migration is SAFE** with proper preparation:
- Discovery script MUST be enabled
- Dashboards MUST be updated to use JOINs
- Power metrics SHOULD be added to collector
- Folder path SHOULD be evaluated for business need

**Overall Assessment:** ✅ **MIGRATION RECOMMENDED**

The new architecture provides:
- ✅ Better data quality (zero transformation)
- ✅ More flexibility (SQL-based transformations)
- ✅ Better extensibility (easy to add fields)
- ⚠️ Higher complexity (requires JOINs)

**Last Updated:** February 15, 2026  
**Reviewed By:** Datalake Team  
**Status:** ✅ Ready for Review
