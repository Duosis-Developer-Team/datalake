#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnose Dynamics 365 productpricelevels vs discovery_crm_productpricelevels.

Fetches productpricelevels and pricelevels with full @odata.nextLink pagination,
compares CRM payload keys to the PostgreSQL DDL contract, cross-checks price
list coverage, and optionally simulates collector normalization.

Usage (same auth style as crm-dynamics-discovery.py):

  cd datalake/collectors/CRM/Dynamics365/analyze_scripts
  python crm_productpricelevel_analyze.py \\
    --tenant-id ... --client-id ... --client-secret ... --crm-url https://org.crm4.dynamics.com

  python crm_productpricelevel_analyze.py ... --show-sample
  python crm_productpricelevel_analyze.py ... --save-raw ./out/
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import importlib.util
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Load collector normalizer from parent directory (same pattern as unit tests)
# ---------------------------------------------------------------------------
_ANALYZE_DIR = Path(__file__).resolve().parent
_COLLECTOR_DIR = _ANALYZE_DIR.parent
_SPEC = importlib.util.spec_from_file_location(
    "crm_dynamics_discovery",
    _COLLECTOR_DIR / "crm-dynamics-discovery.py",
)
if _SPEC is None or _SPEC.loader is None:
    sys.stderr.write("Failed to load crm-dynamics-discovery.py spec.\n")
    sys.exit(1)
_CRM = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CRM)  # type: ignore[union-attr]


# Columns expected in PostgreSQL (discovery_crm_productpricelevels) excluding
# data_type and collection_time (added by collector at emit time).
DB_COLUMNS_FOR_MAPPING: List[Tuple[str, str, str]] = [
    ("productpricelevelid", "productpricelevelid", "Scalar PK"),
    ("pricelevelid", "_pricelevelid_value", "Lookup GUID"),
    ("pricelevel_name", "_pricelevelid_value@OData.Community.Display.V1.FormattedValue", "Lookup label"),
    ("productid", "_productid_value", "Lookup GUID"),
    ("product_name", "_productid_value@OData.Community.Display.V1.FormattedValue", "Lookup label"),
    ("uomid", "_uomid_value", "Lookup GUID"),
    ("uomid_name", "_uomid_value@OData.Community.Display.V1.FormattedValue", "UoM formatted (collector uses _fv raw, _uomid_value)"),
    ("amount", "amount", "Decimal"),
    ("discounttypeid", "_discounttypeid_value", "Lookup GUID"),
    ("pricingmethodcode", "pricingmethodcode", "Option value"),
    ("pricingmethodcode_text", "pricingmethodcode@OData.Community.Display.V1.FormattedValue", "Option label"),
    ("transactioncurrencyid", "_transactioncurrencyid_value", "Lookup GUID"),
    ("transactioncurrency_text", "_transactioncurrencyid_value@OData.Community.Display.V1.FormattedValue", "Currency label"),
    ("modifiedon", "modifiedon", "DateTime"),
]


def _http_retry_policy(retries: int) -> Retry:
    base: Dict[str, Any] = dict(
        total=retries,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
    )
    get_only = frozenset({"GET"})
    try:
        return Retry(allowed_methods=get_only, **base)
    except TypeError:
        try:
            return Retry(method_whitelist=get_only, **base)
        except TypeError:
            return Retry(**base)


def get_access_token(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    crm_url: str,
    timeout: int,
) -> str:
    resource_url = crm_url.rstrip("/")
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": f"{resource_url}/.default",
    }
    resp = requests.post(token_url, data=payload, timeout=timeout)
    if resp.status_code != 200:
        sys.stderr.write(f"Token request failed ({resp.status_code}): {resp.text[:400]}\n")
        sys.exit(1)
    token = resp.json().get("access_token")
    if not token:
        sys.stderr.write("Token response missing access_token.\n")
        sys.exit(1)
    return token


def build_session(token: str, page_size: int, retries: int) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Accept": "application/json",
        "Prefer": f'odata.include-annotations="*",odata.maxpagesize={page_size}',
    })
    adapter = HTTPAdapter(max_retries=_http_retry_policy(retries))
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_all_pages(
    session: requests.Session,
    first_url: str,
    timeout: int,
) -> Tuple[List[Dict[str, Any]], int, int, Optional[int]]:
    """
    Follow @odata.nextLink until exhausted.

    Returns: (records, page_count, total_http_ok_pages, last_http_status)
    """
    results: List[Dict[str, Any]] = []
    page_count = 0
    next_url: Optional[str] = first_url
    last_status: Optional[int] = None

    while next_url:
        page_count += 1
        resp = session.get(next_url, timeout=timeout)
        last_status = resp.status_code
        if not resp.ok:
            return results, page_count, page_count, last_status
        try:
            payload = resp.json()
        except ValueError:
            return results, page_count, page_count, last_status

        batch = payload.get("value")
        if not isinstance(batch, list):
            return results, page_count, page_count, last_status
        for item in batch:
            if isinstance(item, dict):
                results.append(item)
        next_url = payload.get("@odata.nextLink")

    return results, page_count, page_count, last_status


def collect_all_keys(records: Iterable[Dict[str, Any]], sample_limit: int = 500) -> Set[str]:
    """Union of JSON keys seen across up to sample_limit records (shallow keys only)."""
    keys: Set[str] = set()
    for i, rec in enumerate(records):
        if i >= sample_limit:
            break
        keys.update(rec.keys())
    return keys


def field_coverage_report(crm_keys: Set[str]) -> List[Tuple[str, str, str]]:
    """Rows: (db_column, odata_hint, status)."""
    rows: List[Tuple[str, str, str]] = []
    for db_col, hint, desc in DB_COLUMNS_FOR_MAPPING:
        present = hint in crm_keys
        # Alternate OData patterns for labels
        if not present and "FormattedValue" in hint:
            short = hint.split("@")[0]
            present = any(k.startswith(short + "@") for k in crm_keys)
        status = "OK" if present else "MISSING (check $select / annotations)"
        rows.append((db_col, hint, status))
    return rows


def pricelevel_cross_check(
    ppl_records: List[Dict[str, Any]],
    pl_records: List[Dict[str, Any]],
) -> Tuple[int, int, List[str]]:
    """
    Count productpricelevels per pricelevelid vs declared price lists.

    Returns: (distinct_pricelevel_ids_in_ppl, pricelevel_rows, warnings)
    """
    warnings: List[str] = []
    ppl_pl_ids: Set[str] = set()
    for r in ppl_records:
        guid = r.get("_pricelevelid_value")
        if guid:
            ppl_pl_ids.add(str(guid))

    pl_ids: Set[str] = set()
    for r in pl_records:
        pid = r.get("pricelevelid")
        if pid:
            pl_ids.add(str(pid))

    orphan_ppl = ppl_pl_ids - pl_ids
    if orphan_ppl:
        warnings.append(
            f"{len(orphan_ppl)} productpricelevel row(s) reference pricelevelid not in fetched pricelevels "
            f"(pagination mismatch or deleted lists)."
        )

    empty_lists = pl_ids - ppl_pl_ids
    if empty_lists:
        sample = list(sorted(empty_lists))[:5]
        warnings.append(
            f"{len(empty_lists)} price list(s) have no productpricelevel rows in this fetch. "
            f"Sample IDs: {sample}"
        )

    return len(ppl_pl_ids), len(pl_ids), warnings


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Diagnose CRM productpricelevels vs discovery_crm_productpricelevels.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--tenant-id", required=True, help="Azure AD tenant ID.")
    p.add_argument("--client-id", required=True, help="App registration client ID.")
    p.add_argument("--client-secret", required=True, help="Client secret.")
    p.add_argument("--crm-url", required=True, help="CRM base URL.")
    p.add_argument("--api-version", default="v9.2", help="Web API version.")
    p.add_argument("--page-size", type=int, default=5000, help="OData maxpagesize.")
    p.add_argument("--http-timeout-sec", type=int, default=120, help="HTTP timeout.")
    p.add_argument("--http-retries", type=int, default=3, help="Retry count for GET.")
    p.add_argument(
        "--show-sample",
        action="store_true",
        help="Print first 3 raw records and normalized sparse JSON (collector simulation).",
    )
    p.add_argument(
        "--save-raw",
        type=str,
        default="",
        help="If set, write raw_catalog_productpricelevels.json and raw_catalog_pricelevels.json under this directory.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    crm_url = args.crm_url.rstrip("/")
    api_base = f"{crm_url}/api/data/{args.api_version}/"
    timeout = args.http_timeout_sec

    token = get_access_token(
        args.tenant_id, args.client_id, args.client_secret, crm_url, timeout,
    )
    session = build_session(token, args.page_size, args.http_retries)
    collection_time = int(datetime.now(timezone.utc).timestamp() * 1000)

    print("=" * 80)
    print("CRM ProductPriceLevel diagnostic")
    print("=" * 80)

    # --- productpricelevels ---
    ppl_url = f"{api_base}productpricelevels"
    ppl_rows, ppl_pages, _, ppl_status = fetch_all_pages(session, ppl_url, timeout)
    print(f"\nEndpoint: productpricelevels")
    print(f"  HTTP last status: {ppl_status}")
    print(f"  Pages fetched:    {ppl_pages}")
    print(f"  Total rows:       {len(ppl_rows)}")

    # --- pricelevels ---
    pl_url = f"{api_base}pricelevels"
    pl_rows, pl_pages, _, pl_status = fetch_all_pages(session, pl_url, timeout)
    print(f"\nEndpoint: pricelevels")
    print(f"  HTTP last status: {pl_status}")
    print(f"  Pages fetched:    {pl_pages}")
    print(f"  Total rows:       {len(pl_rows)}")

    if args.save_raw:
        out_dir = Path(args.save_raw)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "raw_catalog_productpricelevels.json").write_text(
            json.dumps({"value": ppl_rows}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out_dir / "raw_catalog_pricelevels.json").write_text(
            json.dumps({"value": pl_rows}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nSaved raw JSON under: {out_dir.resolve()}")

    crm_keys = collect_all_keys(ppl_rows)
    print(f"\nDistinct shallow keys (first 500 rows): {len(crm_keys)}")

    print("\n--- Field coverage vs PostgreSQL discovery_crm_productpricelevels ---")
    print(f"{'DB column':<28} | {'OData key hint':<55} | Status")
    print("-" * 110)
    for db_col, hint, status in field_coverage_report(crm_keys):
        print(f"{db_col:<28} | {hint:<55} | {status}")

    dist_ppl, dist_pl, warns = pricelevel_cross_check(ppl_rows, pl_rows)
    print("\n--- Price list cross-check ---")
    print(f"Distinct _pricelevelid_value in productpricelevels: {dist_ppl}")
    print(f"Distinct pricelevelid in pricelevels:              {dist_pl}")
    for w in warns:
        print(f"  NOTE: {w}")

    print("\n--- Next steps (if discovery_crm_productpricelevels is empty) ---")
    if len(ppl_rows) == 0 and ppl_status == 200:
        print("  - CRM returned zero productpricelevel rows: verify catalog / price lists in CRM UI.")
    elif len(ppl_rows) > 0:
        print("  - OData side has rows: if DB table is still empty, verify NiFi RouteOnAttribute includes")
        print("    relationship crm_inventory_productpricelevel (see SQL/CRM/NiFi-productpricelevel-fix.md).")

    if args.show_sample and ppl_rows:
        print("\n--- Sample records (raw + normalized sparse) ---")
        for i, raw in enumerate(ppl_rows[:3]):
            norm = _CRM.normalize_productpricelevel(raw, collection_time)
            sparse = _CRM.sparse_record(norm)
            print(f"\n--- Record index {i} ---")
            print("RAW keys:", sorted(raw.keys())[:40], "..." if len(raw) > 40 else "")
            print("NORMALIZED (sparse JSON):\n", json.dumps(sparse, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
