# analyze_scripts — Archive

This directory contains **proof-of-concept / analysis scripts** used during the initial CRM data discovery phase. These scripts are **not production collectors** and should not be used for NiFi pipeline ingestion.

## Contents

| File | Purpose |
|------|---------|
| `crm_discovery.py` | One-shot raw data pull for `products`, `pricelevels`, `productpricelevels`. Credentials replaced with placeholders — do not commit real secrets. |
| `csv-script.py` | Converts the raw JSON catalog dumps to CSV for ad-hoc analysis. |
| `raw_catalog_products.json` | Raw OData snapshot of the products endpoint (analysis sample). |
| `raw_catalog_pricelevels.json` | Raw OData snapshot of the pricelevels endpoint (analysis sample). |
| `raw_catalog_productpricelevels.json` | Raw OData snapshot of the productpricelevels endpoint (analysis sample). |
| `dc_standard_price_catalog.csv` | Processed standard price catalog CSV (analysis output). |
| `standart_fiyat_katalogu.csv` | Same as above, Turkish column headers (analysis output). |

## Production Collector

The production-grade discovery script is located one level up:

```
datalake/collectors/CRM/Dynamics365/crm-dynamics-discovery.py
```

That script follows the platform's ServiceCore-style unified discovery pattern:
single script → single Avro schema → single NiFi flow → 14 UPSERT tables.
See [`../README.md`](../README.md) for full documentation.
