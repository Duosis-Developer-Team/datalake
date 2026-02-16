# VMware Grafana Dashboards

Grafana dashboards for VMware collector data stored in the Datalake (PostgreSQL). Each dashboard is **ready for external use**: on import you will be prompted to select a PostgreSQL datasource.

## Folder structure

```
dashboards/
└── VMware/
    ├── README.md
    ├── vmware-datacenter-overview.json
    ├── vmware-cluster-overview.json
    ├── vmware-host-overview.json
    ├── vmware-vm-overview.json
    └── vmware-executive-summary.json
```

## Prerequisites

- Grafana 9.x or later
- PostgreSQL datasource configured in Grafana (pointing to the Datalake database)
- VMware SQL objects deployed: discovery tables, collector raw tables, views, and materialized views (see [SQL/VMware/README.md](../../SQL/VMware/README.md))
- Materialized views refreshed on a schedule (e.g. every 15 minutes via `refresh_vmware_materialized_views()`)

## Import (datasource selectable)

1. In Grafana: **Dashboards** → **New** → **Import**.
2. Upload the JSON file or paste its content.
3. When prompted for **PostgreSQL**, choose your Datalake PostgreSQL datasource (or create one). This makes the dashboard work in any environment without editing UIDs.
4. Click **Import**.

Repeat for each JSON file under `dashboards/VMware/`.

## Dashboards overview

| Dashboard | Description |
|-----------|-------------|
| **VMware - Datacenter Overview** | Datacenter counts; CPU/Memory/Storage **time series**; current usage bar gauges; capacity table. Multi-select: vCenter, Datacenter. |
| **VMware - Cluster Overview** | Cluster counts; CPU/Memory/Disk/Network **time series**; bar comparison; capacity table. Multi-select: vCenter, Datacenter, Location, Cluster. |
| **VMware - Host Overview** | Host counts (connected, maintenance); CPU/Memory/Power **time series**; top hosts; health table. Multi-select: vCenter, Datacenter, Location, Cluster, Host. |
| **VMware - VM Overview** | VM counts (powered on); CPU/Memory/CPU ready/Disk/Network **time series**; top VMs; VM list. Multi-select: vCenter, Datacenter, Location, Cluster, Host, VM. |
| **VMware - Executive Summary** | Single-page: DC/Cluster/Host/VM counts, CPU % by datacenter and cluster, datacenter table. All variables multi-select. |

All dashboards use the same template variables where applicable: **vCenter**, **Datacenter**, **Location**, **Cluster**, **Host**, **VM**. Variables are loaded from discovery and inventory data.

### Multi-select filters

Every template variable supports **multi-select**: you can select multiple vCenters, datacenters, locations, clusters, hosts, or VMs at once. The dashboard shows data for the union of selected values (e.g. several datacenters or clusters together). Choose **All** to clear the filter for that variable.

**SQL pattern for multi-value:** Panel and variable queries use `IN ($var)` with an empty check `'$var' = ''`. For multi-value to produce valid SQL (e.g. `IN ('VC1','VC2')`), variable **Format** must be **Single quote** in Grafana (dashboard JSON sets `multiValueFormat: "singlequote"`). Do not change variable format to something that would break the IN list.

**Leaf-only panel filters:** In each dashboard, **only the bottom-level (leaf) variable** is used in panel SQL. Upper-level variables (vCenter, Datacenter, Location, Cluster) are used only to populate the dropdown options; they do not appear in the panel WHERE clause. This avoids duplication and quote conflicts. Summary:

| Dashboard | Leaf variable | Panel SQL filter |
|-----------|---------------|------------------|
| Datacenter Overview | Datacenter | `('$datacenter' = '' OR datacenter_name IN ($datacenter))` |
| Cluster Overview | Cluster | `('$cluster' = '' OR COALESCE(cluster_name, cluster_name_discovery) IN ($cluster))` |
| Host Overview | Host | `('$host' = '' OR host_name IN ($host))` |
| VM Overview | VM | `('$vm' = '' OR vm_name IN ($vm))` |
| Executive Summary | Per panel type | DC panels → `$datacenter`; cluster panels → `$cluster`; VM panels → `$vm` |

### Operational use and root cause analysis

Dashboards are designed for **operational use** and **root cause analysis**:

- **Time series panels** are central: each layer dashboard includes CPU, Memory, and (where relevant) Storage, Disk I/O, Network, Power, and CPU ready over time. Use the time range picker to zoom into incidents; compare multiple entities (e.g. several clusters or VMs) on the same graph when using multi-select.
- **Current-state panels** (bar gauges, tables) show the latest snapshot for quick comparison and "top N" views.
- Use **multi-select** to compare a subset of vCenters/datacenters/clusters/hosts/VMs without switching dashboards.

## Tags

Dashboards are tagged with: `vmware`, `datalake`, and the layer (`datacenter`, `cluster`, `host`, `vm`, `summary`) for easier filtering in Grafana.
