# VMware SQL Schema Documentation

This directory contains all SQL objects for VMware data collection and reporting.

---

## 📁 Directory Structure

```
SQL/VMware/
├── 01_tables/              Collector raw data table definitions (INSERT only)
├── 02_views/               Enhanced views (discovery + collector JOINs)
├── 03_materialized_views/  Latest snapshot materialized views (fast queries)
└── 04_functions/           Utility functions (refresh, etc.)
```

**Discovery tables** are located in: `SQL/All Tables/discovery_vmware_inventory_*.sql`

---

## 🗄️ Table Categories

### 1. Discovery Tables (Inventory/UPSERT)

**Location:** `SQL/All Tables/`

**Pattern:** `discovery_vmware_inventory_<entity>`

**Purpose:** Store entity names and hierarchy (MOID → Name mapping)

| Table | Purpose | UPSERT Key |
|-------|---------|------------|
| `discovery_vmware_inventory_vcenter` | vCenter info | `vcenter_uuid` |
| `discovery_vmware_inventory_datacenter` | Datacenter names | `vcenter_uuid, component_moid` |
| `discovery_vmware_inventory_cluster` | Cluster names | `vcenter_uuid, component_moid` |
| `discovery_vmware_inventory_host` | Host names and UUIDs | `vcenter_uuid, component_moid` |
| `discovery_vmware_inventory_vm` | VM names and status | `vcenter_uuid, component_moid` |

**Features:**
- Auto-managed timestamps: `first_observed`, `last_observed`
- Trigger-based `last_observed` update
- Unique constraints on business keys

### 2. Collector Tables (Time Series)

**Location:** `01_tables/`

**Pattern:** `raw_vmware_<entity>_<type>`

**Purpose:** Store metrics and configuration with timestamps (INSERT only)

#### VM Tables
- `raw_vmware_vm_config` - Configuration data
- `raw_vmware_vm_runtime` - Runtime state
- `raw_vmware_vm_storage` - VM-Datastore relationships
- `raw_vmware_vm_perf_raw` - Raw performance samples
- `raw_vmware_vm_perf_agg` - Aggregated performance

#### Host Tables
- `raw_vmware_host_hardware` - Hardware configuration
- `raw_vmware_host_runtime` - Runtime state
- `raw_vmware_host_storage` - Host-Datastore relationships
- `raw_vmware_host_perf_raw` - Raw performance samples (includes power metrics)
- `raw_vmware_host_perf_agg` - Aggregated performance

#### Cluster/Datacenter Tables
- `raw_vmware_cluster_config` - Cluster configuration
- `raw_vmware_cluster_metrics_agg` - Pre-aggregated cluster metrics (collector-calculated; for Grafana)
- `raw_vmware_datacenter_config` - Datacenter configuration
- `raw_vmware_datacenter_metrics_agg` - Pre-aggregated datacenter metrics

#### ETL Routing by data_type

Collectors output a single JSON array; each record has a `data_type` field. The pipeline must route by `data_type` into the correct table:

| Collector | data_type values | Target table(s) |
|-----------|------------------|-----------------|
| vmware_cluster_collector.py | `vmware_cluster_config` | raw_vmware_cluster_config |
| vmware_cluster_collector.py | `vmware_cluster_metrics_agg` | raw_vmware_cluster_metrics_agg |
| vmware_datacenter_collector.py | `vmware_datacenter_config` | raw_vmware_datacenter_config |
| vmware_datacenter_collector.py | `vmware_datacenter_metrics_agg` | raw_vmware_datacenter_metrics_agg |

Insert each record into the table that matches its `data_type` (append-only; use ON CONFLICT if needed per table PK).

### 3. Enhanced Views (Discovery + Collector)

**Location:** `02_views/`

**Purpose:** Combine discovery (entity names) + collector (metrics) via JOINs

| View | Purpose | Data Sources |
|------|---------|--------------|
| `vmware_vm_inventory` | Complete VM inventory | vm_config + vm_runtime + vm_storage + discovery |
| `vmware_vm_metrics` | VM performance metrics | vm_perf_agg |
| `vmware_host_inventory` | Complete host inventory | host_hardware + host_runtime + host_storage + discovery |
| `vmware_host_metrics` | Host performance metrics | host_perf_agg + power data |
| `vmware_host_capacity` | Host capacity analysis | host_hardware + host_runtime |
| `vmware_host_health` | Host health status | host_runtime + host_hardware |
| `vmware_host_power` | Host power consumption | host_perf_agg (power counter) |
| `vmware_host_storage_detail` | Host storage details | host_storage |
| `vmware_cluster_inventory` | Cluster config with entity names | cluster_config + discovery |
| `vmware_cluster_metrics` | Cluster aggregated metrics with entity names | cluster_metrics_agg + discovery |
| `vmware_datacenter_inventory` | Datacenter config with entity names | datacenter_config + discovery |
| `vmware_datacenter_metrics` | Datacenter aggregated metrics with entity names | datacenter_metrics_agg + discovery |

**Key Features:**
- ✅ Entity names included (datacenter_name, cluster_name, host_name)
- ✅ Human-readable units (GB, GHz, percent)
- ✅ Calculated fields (usage_percent, free resources)
- ✅ All historical data (all timestamps)

### 4. Materialized Views (Latest Snapshot)

**Location:** `03_materialized_views/`

**Purpose:** Ultra-fast queries for dashboards (latest data only)

| Materialized View | Based On | Refresh Frequency |
|-------------------|----------|-------------------|
| `mv_vmware_vm_latest` | `vmware_vm_inventory` | Every 15 minutes |
| `mv_vmware_vm_metrics_latest` | `vmware_vm_metrics` | Every 15 minutes |
| `mv_vmware_host_latest` | `vmware_host_inventory` | Every 15 minutes |
| `mv_vmware_host_metrics_latest` | `vmware_host_metrics` | Every 15 minutes |
| `mv_vmware_cluster_latest` | Aggregated from hosts | Every 15 minutes |
| `mv_vmware_cluster_metrics_latest` | `raw_vmware_cluster_metrics_agg` (latest window) | Every 15 minutes |
| `mv_vmware_datacenter_latest` | Aggregated from clusters/hosts | Every 15 minutes |
| `mv_vmware_datacenter_metrics_latest` | `raw_vmware_datacenter_metrics_agg` (latest window) | Every 15 minutes |

**Performance Benefits:**
- 50-400x faster than regular views
- Pre-computed JOINs and aggregations
- Indexed for fast lookups

### 5. Functions

**Location:** `04_functions/`

- `refresh_vmware_materialized_views()` - Refreshes all materialized views

---

## 🚀 Deployment Order

### Initial Setup (One-Time)

```bash
# 1. Deploy discovery tables (if not already done)
psql -f SQL/All\ Tables/discovery_vmware_inventory_vcenter.sql
psql -f SQL/All\ Tables/discovery_vmware_inventory_datacenter.sql
psql -f SQL/All\ Tables/discovery_vmware_inventory_cluster.sql
psql -f SQL/All\ Tables/discovery_vmware_inventory_host.sql
psql -f SQL/All\ Tables/discovery_vmware_inventory_vm.sql

# 2. Deploy collector tables
for file in SQL/VMware/01_tables/*.sql; do
    psql -f "$file"
done

# 3. Deploy views
for file in SQL/VMware/02_views/*.sql; do
    psql -f "$file"
done

# 4. Deploy materialized views
for file in SQL/VMware/03_materialized_views/*.sql; do
    psql -f "$file"
done

# 5. Deploy functions
psql -f SQL/VMware/04_functions/fn_refresh_vmware_mvs.sql

# 6. Schedule automatic refresh
psql << 'EOF'
CREATE EXTENSION IF NOT EXISTS pg_cron;
SELECT cron.schedule(
    'refresh-vmware-mvs',
    '*/15 * * * *',
    'SELECT * FROM refresh_vmware_materialized_views();'
);
EOF
```

### Add folder_path Column (If Upgrading)

```sql
ALTER TABLE raw_vmware_vm_config 
ADD COLUMN IF NOT EXISTS folder_path TEXT;

CREATE INDEX IF NOT EXISTS idx_raw_vmware_vm_config_folder_path 
    ON raw_vmware_vm_config(folder_path);
```

---

## 📊 Query Patterns

### Dashboard Queries (Use Materialized Views)

```sql
-- Current VM inventory
SELECT * FROM mv_vmware_vm_latest 
ORDER BY datacenter_name, cluster_name, folder_path, vm_name;

-- Current host inventory
SELECT * FROM mv_vmware_host_latest 
ORDER BY datacenter_name, cluster_name, host_name;

-- Cluster capacity overview
SELECT 
    datacenter_name,
    cluster_name,
    total_hosts,
    total_cpu_ghz,
    current_cpu_usage_ghz,
    cpu_usage_percent
FROM mv_vmware_cluster_latest;
```

### Historical Analysis (Use Regular Views)

```sql
-- VM usage over time
SELECT 
    collection_timestamp,
    datacenter_name,
    vm_name,
    cpu_usage_percent,
    memory_usage_percent
FROM vmware_vm_inventory
WHERE vm_name = 'web-server-01'
  AND collection_timestamp > NOW() - INTERVAL '7 days'
ORDER BY collection_timestamp;
```

### Raw Performance Data (Detailed Analysis)

```sql
-- Individual performance samples
SELECT 
    sample_timestamp,
    counter_name,
    value,
    counter_unit_label
FROM raw_vmware_vm_perf_raw
WHERE vm_moid = 'vm-1234'
  AND sample_timestamp > NOW() - INTERVAL '1 hour'
ORDER BY sample_timestamp;
```

---

## 🔧 Maintenance

### Manual Refresh

```sql
-- Refresh all materialized views
SELECT * FROM refresh_vmware_materialized_views();

-- Refresh single view
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_vmware_vm_latest;
```

### Monitor Materialized Views

```sql
-- Check MV sizes
SELECT 
    schemaname,
    matviewname,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) as size,
    (SELECT MAX(materialized_at) FROM mv_vmware_vm_latest LIMIT 1) as last_refresh
FROM pg_matviews
WHERE matviewname LIKE 'mv_vmware%'
ORDER BY matviewname;

-- Check pg_cron job status
SELECT * FROM cron.job WHERE jobname = 'refresh-vmware-mvs';
SELECT * FROM cron.job_run_details 
WHERE jobid = (SELECT jobid FROM cron.job WHERE jobname = 'refresh-vmware-mvs')
ORDER BY start_time DESC LIMIT 5;
```

---

## 📚 References

- Collector scripts: `../../collectors/VMware/`
- Discovery script: `../../collectors/VMware/discovery/vmware-discovery.py`
- Development template: `../../docs/development-templates/collector_discovery_template.md`
- Collector README: `../../collectors/VMware/README.md`

---

**Last Updated:** February 15, 2026  
**Status:** Production Ready
