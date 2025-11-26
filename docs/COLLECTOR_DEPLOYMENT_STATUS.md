# Collector Deployment Status Report

## 1. Introduction
This document outlines the deployment status of data collectors across the Datalake environment. The analysis is based on the inventory data (`datalake_envanter.csv`) and the ETL topology (`data-collector-etl-topology.jpg`).

## 2. Architecture & Topology Overview
The Datalake architecture follows a **Hub-and-Spoke** topology:
*   **Central Hub (DC-13):** Hosts the Datalake, Main NiFi cluster, and central storage. All data flows here.
*   **Remote Sites:** (DC-11, DC-12, DC-14, DC-15, DC-16, DC-17, AZ-11, ICT-11) act as data sources.
*   **Data Flow:** Remote Sites -> Remote NiFi/Postgres Queue -> Central NiFi (DC-13) -> Datalake.

## 3. Collector Deployment Status
Based on the inventory analysis, the status of developed collectors is categorized below.

### ✅ Fully Deployed / Widely Active
These collectors are active in almost all target sites.

| Collector Type | Sites Deployed | Status |
| :--- | :--- | :--- |
| **Vmware** | DC-11, DC-12, DC-13, DC-14, DC-15, DC-16, DC-17, AZ-11, ICT-11 | **Active** |
| **Nutanix** | DC-11, DC-12, DC-13, DC-14, DC-15, DC-16, DC-17, AZ-11 | **Active** |
| **Netbackup** | DC-11, DC-13, DC-14, DC-15, DC-16, DC-17, AZ-11, ICT-11 | **Active** |
| **Zerto** | DC-11, DC-12, DC-13, DC-14, DC-15, DC-16 | **Active** |
| **IBM-HMC** | DC-11, DC-13, DC-14, DC-15, DC-16 | **Active** |

### ⚠️ Partially Deployed
These collectors are active in some sites but have pending or inactive instances in others.

| Collector Type | Active Sites | Inactive/Planned Sites | Notes |
| :--- | :--- | :--- | :--- |
| **Veeam** | DC-11, DC-13, DC-14, DC-15 | DC-12, DC-16, AZ-11, ICT-11 | New templates or agents identified but not marked active (-) in inventory. |

### 🛑 Not Deployed / Inactive
These collectors appear in the inventory but are currently marked as inactive (-) across all or most sites.

| Collector Type | Status | Notes |
| :--- | :--- | :--- |
| **IBM-Virtualize** | Inactive | Defined for DC-11, 13, 14, 15, 16, 17, AZ-11, ICT-11 but marked inactive. |
| **ILO-Redfish** | Inactive | Found in DC-14 (Inactive). |
| **s3icos** | Inactive | Found in DC-14 (Inactive). |

## 4. Recommendations
1.  **Veeam Expansion:** Verify status of Veeam agents in DC-12, 16, and international sites (AZ-11, ICT-11) to complete coverage.
2.  **IBM-Virtualize:** Determine if this collector is deprecated or scheduled for future deployment.
3.  **Topology Consistency:** Ensure all active collectors in Remote Sites are correctly configured to push to their respective Remote NiFi clusters as per the topology diagram.

