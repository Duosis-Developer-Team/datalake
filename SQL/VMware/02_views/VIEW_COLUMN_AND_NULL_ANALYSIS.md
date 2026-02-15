# VMware View Column and NULL Analysis

This document confirms that all columns in VMware views are derived from real tables (raw_*, discovery_*) or deterministic expressions on those tables, and explains when and why columns can be NULL.

---

## 1. Data Source Verification

All view columns come from one of:

- **Base tables:** `raw_vmware_*` (collector data), `discovery_vmware_inventory_*` (discovery data)
- **Derived expressions:** CASE, ROUND, SPLIT_PART, SUM, COUNT, MAX, STRING_AGG on the above

There are no columns from non-existent or placeholder sources.

---

## 2. Why Columns Can Be NULL (General)

| Reason | Description | Example |
|--------|-------------|---------|
| **1. LEFT JOIN no match** | Main table has a row but the joined table has no row for the same key; joined columns become NULL. | Discovery not run or key mismatch → vc.name, dc.name, cl.name NULL. No runtime row for same timestamp → r.* NULL. |
| **2. Source column is NULL** | Raw and discovery columns are mostly nullable; API or discovery may leave them empty. | folder_path, annotation, guest_ip_address, vcenter_hostname. |
| **3. CASE / calculation** | Condition not met → ELSE NULL, or division by zero avoided → NULL. | cpu_usage_percent when max_cpu_usage = 0; usage_percent when capacity = 0. |
| **4. Pivot / MAX** | No row for that counter or instance → MAX(CASE ...) returns NULL. | vm_metrics / host_metrics: metric NULL when that counter was not collected for that entity/window. |

---

## 3. View-by-View Analysis

### 3.1 vmware_vm_inventory

**Main source:** `raw_vmware_vm_config c` (FROM).  
**LEFT JOINs:** discovery (vc, dc, cl, h), `raw_vmware_vm_runtime r`, `raw_vmware_vm_storage s`.

**Column sources:**
- Identification, config (c.*): from raw_vmware_vm_config.
- Entity names (vcenter_name, datacenter_name, vcenter_hostname, location, cluster_name, host_name, host_uuid): from discovery tables via LEFT JOIN.
- Runtime (power_state, quick_stats_*, guest_*): from raw_vmware_vm_runtime.
- Storage (total_committed_bytes, datastores, etc.): from raw_vmware_vm_storage (aggregated).
- Percent and calculated fields: CASE/ROUND on c and r.

**Columns that can be NULL:**

| Column(s) | Reason |
|-----------|--------|
| vcenter_name, datacenter_name, vcenter_hostname, location, cluster_name, host_name, host_uuid | Discovery LEFT JOIN: no row or key mismatch; vcenter_hostname nullable in discovery. |
| datacenter_moid, cluster_moid, host_moid | Can be NULL in raw_vmware_vm_config (API). |
| folder_path, annotation, guest_id, guest_full_name, firmware, version, etc. | Optional in API / collector. |
| power_state, connection_state, boot_time, all r.* (quick_stats, guest_*) | Runtime LEFT JOIN: no runtime row for same (vm_moid, collection_timestamp, vcenter_uuid). |
| total_committed_bytes, total_uncommitted_bytes, datastores, datastore_count | No storage rows for that VM/timestamp → aggregate 0/NULL; STRING_AGG empty/NULL. |
| cpu_usage_percent, memory_usage_percent | CASE: max_cpu_usage = 0 or memory_size_mb = 0 → NULL. |

---

### 3.2 vmware_host_inventory

**Main source:** `raw_vmware_host_hardware h` (FROM).  
**LEFT JOINs:** discovery (vc, dc, cl, host_disc), `raw_vmware_host_runtime r`, `raw_vmware_host_storage s`.

**Column sources:**
- Identification, hardware (h.*): from raw_vmware_host_hardware.
- Entity names: from discovery via LEFT JOIN.
- Runtime (connection_state, power_state, quick_stats_*, config_name): from raw_vmware_host_runtime.
- Storage (datastore_count, total_storage_*, datastores): from raw_vmware_host_storage (aggregated).
- Percent and free-* fields: CASE/ROUND on h and r.

**Columns that can be NULL:**

| Column(s) | Reason |
|-----------|--------|
| vcenter_name, datacenter_name, vcenter_hostname, location, cluster_name, host_name | Discovery LEFT JOIN: no match or vcenter_hostname null in discovery. |
| vendor, model, uuid, cpu_model, num_nics, num_hbas, product_* | Optional in API / raw_vmware_host_hardware. |
| connection_state, power_state, config_name, quick_stats_*, etc. | Runtime LEFT JOIN: no runtime row for same (host_moid, collection_timestamp, vcenter_uuid). |
| datastore_count, total_storage_*, datastores | No storage rows for that host/timestamp. |
| cpu_usage_percent, memory_usage_percent, free_cpu_ghz, free_memory_gb, uptime_days | CASE: zero denominator or r.* NULL. |

---

### 3.3 vmware_host_health

**Main source:** `raw_vmware_host_runtime r` (FROM), `raw_vmware_host_hardware h` (LEFT JOIN).  
**LEFT JOINs:** discovery (vc, dc, cl), `raw_vmware_host_storage s`, view `vmware_host_metrics m`.

**Column sources:**
- Timestamp, host_moid, r.*: from raw_vmware_host_runtime.
- Entity names: from discovery.
- h.* (num_cpu_cores, memory_size, product_*, vendor, model): from raw_vmware_host_hardware.
- Storage aggregates and m.*: from host_storage and vmware_host_metrics.
- Health status and percent fields: CASE on r, h, s, m.

**Columns that can be NULL:**

| Column(s) | Reason |
|-----------|--------|
| vcenter_name, datacenter_name, vcenter_hostname, location, cluster_name | Discovery LEFT JOIN. |
| datacenter_moid, cluster_moid | From h; h missing or API null. |
| health_system_runtime_system_health_info (health_info), boot_time, quick_stats_* | Optional in raw_vmware_host_runtime (API). |
| num_cpu_cores, memory_size, product_*, vendor, model | Hardware LEFT JOIN: no h row for same timestamp. |
| Storage-related aggregates, m.* (metrics) | Storage / metrics LEFT JOIN: no rows. |
| cpu_usage_percent, memory_usage_percent, *_health_status | CASE: zero denominator or missing r/h. |

---

### 3.4 vmware_host_capacity

**Main source:** `raw_vmware_host_hardware h` (FROM).  
**LEFT JOINs:** discovery (vc, dc, cl), `raw_vmware_host_runtime r`, `raw_vmware_host_storage s`.

**Column sources:**
- Identification, hardware, entity names: h and discovery.
- Runtime and storage: r and s (aggregated).
- All capacity and threshold fields: expressions on h, r, s.

**Columns that can be NULL:**

| Column(s) | Reason |
|-----------|--------|
| vcenter_name, datacenter_name, vcenter_hostname, location, cluster_name | Discovery LEFT JOIN. |
| hostname, power_state, connection_state, quick_stats_* | Runtime LEFT JOIN. |
| cpu_usage_percent, memory_usage_percent, storage_usage_percent | CASE: zero denominator. |
| cpu_free_*, memory_free_*, storage_* | LEFT JOIN or zero capacity. |
| *_threshold_status, overall_capacity_status | CASE: no data or zero denominator → 'UNKNOWN' or NULL. |

---

### 3.5 vmware_host_storage_detail

**Main source:** `raw_vmware_host_storage s` (FROM).  
**LEFT JOINs:** `raw_vmware_host_runtime r`, `raw_vmware_host_hardware h`, discovery (vc, dc, cl).

**Column sources:**
- Timestamp, host_moid, datastore_*: from raw_vmware_host_storage.
- Entity names, hostname, r.*, h.*: from JOINs.
- usage_percent, free_percent, health/threshold flags: CASE on s.

**Columns that can be NULL:**

| Column(s) | Reason |
|-----------|--------|
| vcenter_name, datacenter_name, vcenter_hostname, location, cluster_name | Discovery LEFT JOIN. |
| hostname, host_connection_state, host_power_state | Runtime LEFT JOIN. |
| datastore_capacity, datastore_free_space, datastore_type, etc. | Nullable in raw_vmware_host_storage or API. |
| host_vendor, host_model, host_hba_count | Hardware LEFT JOIN. |
| usage_percent, free_percent | CASE: datastore_capacity = 0 or NULL. |
| storage_health_status, free_space_threshold | CASE: capacity 0/NULL → 'OK' or NULL. |

---

### 3.6 vmware_host_power

**Main source:** CTE `power_metrics` from `raw_vmware_host_perf_agg` (power.* counters), then LEFT JOIN h, r, vc, dc, cl.

**Column sources:**
- Power/energy metrics: MAX(CASE ...) on raw_vmware_host_perf_agg for power counters.
- Entity names, hostname, h.*, r.*: from JOINs.

**Columns that can be NULL:**

| Column(s) | Reason |
|-----------|--------|
| power_avg_watts, power_min_watts, power_max_watts, energy_*_joules, power_cap_watts | Counter not present in raw_vmware_host_perf_agg for that host/timestamp → MAX(CASE...) NULL. |
| vcenter_name, datacenter_name, vcenter_hostname, location, cluster_name | Discovery LEFT JOIN. |
| hostname, power_state, connection_state, quick_stats_* | Runtime LEFT JOIN. |
| h.* (vendor, model, num_cpu_cores, etc.) | Hardware LEFT JOIN. |
| watts_per_ghz_*, power_cap_usage_percent, power_status, etc. | CASE: required value NULL or zero → NULL or 'NO_DATA'/'UNKNOWN'. |

---

### 3.7 vmware_vm_metrics

**Source:** Only `raw_vmware_vm_perf_agg`. CTE pivots with `MAX(CASE WHEN counter_name = '...' AND instance = '...' THEN value_* END)`.

**Column sources:**
- collection_timestamp, vcenter_uuid, vm_moid, window_*: from raw_vmware_vm_perf_agg.
- All metric columns: pivot of value_avg/value_min/value_max for specific counter_name and instance.

**Columns that can be NULL:**

| Column(s) | Reason |
|-----------|--------|
| Every metric column (cpu_usage_avg_mhz, mem_*, disk_*, net_*, datastore_*) | That counter/instance not present for that VM in that collection window → MAX(...) NULL. |

No other tables are used; NULL means no data for that counter/instance in perf_agg.

---

### 3.8 vmware_host_metrics

**Source:** Only `raw_vmware_host_perf_agg`. Same pivot pattern as vm_metrics.

**Column sources:**
- collection_timestamp, vcenter_uuid, host_moid: from raw_vmware_host_perf_agg.
- All metric columns: pivot of value_* for specific counter_name.

**Columns that can be NULL:**

| Column(s) | Reason |
|-----------|--------|
| Every metric column (cpu_*, mem_*, disk_*, net_*, datastore_*) | That counter not present for that host in that collection → MAX(CASE...) NULL. |

No other tables; NULL means that performance counter was not collected or has no samples for that host.

---

### 3.9 vmware_cluster_inventory

**Main source:** `raw_vmware_cluster_config c` (FROM).  
**LEFT JOINs:** discovery (vc, dc, cl).

**Column sources:**
- Identification (collection_timestamp, vcenter_uuid, datacenter_moid, cluster_moid): from raw_vmware_cluster_config.
- Entity names (vcenter_name, datacenter_name, vcenter_hostname, location, cluster_name): from discovery via LEFT JOIN.
- Config and summary (name, summary_*, config_das_*, config_drs_*, config_dpm_*): from raw_vmware_cluster_config.
- total_cpu_ghz, total_memory_gb: CASE/ROUND on summary_total_cpu and summary_total_memory (NULL when denominator 0).

**Columns that can be NULL:**

| Column(s) | Reason |
|-----------|--------|
| vcenter_name, datacenter_name, vcenter_hostname, location, cluster_name | Discovery LEFT JOIN: no match or vcenter_hostname null in discovery. |
| datacenter_moid, name, summary_* | Nullable in raw_vmware_cluster_config (API). |
| config_das_*, config_drs_*, config_dpm_* | Optional in API. |
| total_cpu_ghz, total_memory_gb | CASE: summary_total_cpu = 0 or summary_total_memory NULL/0. |

---

### 3.10 vmware_cluster_metrics

**Main source:** `raw_vmware_cluster_metrics_agg m` (FROM).  
**LEFT JOINs:** discovery (vc, dc, cl).

**Column sources:**
- All metric and count columns: from raw_vmware_cluster_metrics_agg (collector-calculated aggregations).
- Entity names (vcenter_name, datacenter_name, vcenter_hostname, location, cluster_name_discovery): from discovery via LEFT JOIN.
- total_cpu_ghz, total_memory_gb: ROUND on total_cpu_mhz_capacity and total_memory_bytes_capacity.

**Columns that can be NULL:**

| Column(s) | Reason |
|-----------|--------|
| vcenter_name, datacenter_name, vcenter_hostname, location, cluster_name_discovery | Discovery LEFT JOIN: no match. |
| datacenter_moid, cluster_name, window_*, total_host_count, total_vm_count | Nullable in raw table or collector. |
| cpu_usage_*_percent, memory_usage_*_percent, disk_*_kbps, network_*_kbps | No host perf data for that cluster in that window → collector leaves NULL. |

---

## 4. Summary

- **All view columns** are backed by real tables (raw_*, discovery_*) or deterministic expressions on them.
- **NULL causes** are: (1) LEFT JOIN no match, (2) source column NULL, (3) CASE/calculation (e.g. divide by zero), (4) pivot (counter/instance missing in perf_agg).
- Reducing NULLs in entity names and runtime requires: discovery populated and in sync (vc, dc, cl, h), and collector writing config, runtime, and storage for the same timestamps and keys.
