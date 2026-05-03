#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynamics 365 CRM discovery collector.

Fetches **active** Accounts (`statecode eq 0`), **active** Product Catalog (`statecode eq 0`),
and realized Sales only — Fulfilled / Invoiced salesorders (`statecode` 3 or 4) with
`order_details` line items — via the Dynamics 365 Web API (OData v4). Does **not** call
invoices, contracts, opportunities, or quotes (narrower privilege surface).
Normalizes records
to sparse flat JSON for NiFi PutDatabaseRecord (UPSERT into discovery_crm_* tables).
Timestamps use Avro logicalType timestamp-millis (epoch ms UTC) so JDBC binds TIMESTAMPTZ.

Each array element is sparse: only keys relevant to that record's data_type are emitted;
omitted keys correspond to null in the unified Avro schema (crm-dynamics-discovery.json).

Output: UTF-8 JSON array on stdout.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------

def normalize_string(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    return str(value)


def normalize_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return bool(value)


def _parse_odata_datetime(value: Any) -> Optional[datetime]:
    """Parse Dynamics / OData datetime string to aware UTC datetime, or None."""
    if value is None or value == "":
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def normalize_timestamp_millis(value: Any) -> Optional[int]:
    """Epoch milliseconds UTC for Avro timestamp-millis / NiFi JDBC."""
    dt = _parse_odata_datetime(value)
    if dt is None:
        return None
    return int(dt.timestamp() * 1000)


def normalize_date(value: Any) -> Optional[str]:
    """Return date as ISO-8601 date string (YYYY-MM-DD) or None."""
    dt = _parse_odata_datetime(value)
    if dt is None:
        return None
    return dt.date().isoformat()


def _fv(raw: Dict[str, Any], field: str) -> Optional[str]:
    """Extract OData FormattedValue annotation for a field."""
    return normalize_string(
        raw.get(f"{field}@OData.Community.Display.V1.FormattedValue")
    )


def _lookup_id(raw: Dict[str, Any], field: str) -> Optional[str]:
    """Extract OData lookup GUID (_<field>_value)."""
    return normalize_string(raw.get(f"_{field}_value"))


def _lookup_name(raw: Dict[str, Any], field: str) -> Optional[str]:
    """Extract OData formatted value for a lookup field (_<field>_value@FormattedValue)."""
    return normalize_string(
        raw.get(f"_{field}_value@OData.Community.Display.V1.FormattedValue")
    )


# ---------------------------------------------------------------------------
# Retry / session
# ---------------------------------------------------------------------------

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
    debug: bool = False,
) -> str:
    resource_url = crm_url.rstrip("/")
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": f"{resource_url}/.default",
    }
    if debug:
        sys.stderr.write(f"[DEBUG] Token URL: {token_url}\n")
        sys.stderr.write(f"[DEBUG] scope: {resource_url}/.default\n")

    resp = requests.post(token_url, data=payload, timeout=timeout)
    if resp.status_code != 200:
        sys.stderr.write(f"Token request failed ({resp.status_code}): {resp.text[:200]}\n")
        sys.exit(1)
    token = resp.json().get("access_token")
    if not token:
        sys.stderr.write("Token response missing access_token.\n")
        sys.exit(1)

    if debug:
        # Decode JWT payload (no signature check — diagnostic only)
        try:
            import base64 as _b64
            parts = token.split(".")
            padding = 4 - len(parts[1]) % 4
            raw = _b64.urlsafe_b64decode(parts[1] + "=" * padding)
            claims = json.loads(raw)
            sys.stderr.write(
                f"[DEBUG] Token claims: aud={claims.get('aud')!r} "
                f"appid={claims.get('appid') or claims.get('azp')!r} "
                f"iss={claims.get('iss')!r} "
                f"roles={claims.get('roles', [])!r}\n"
            )
        except Exception as exc:
            sys.stderr.write(f"[DEBUG] Could not decode token: {exc}\n")

    return token


def build_session(token: str, page_size: int, retries: int) -> requests.Session:
    session = requests.Session()
    # Use wildcard annotation (same as the analyze script) to maximise D365 compatibility.
    # The maxpagesize preference is merged into the same Prefer header as per OData spec.
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


# ---------------------------------------------------------------------------
# Paginated fetch — follows @odata.nextLink
# ---------------------------------------------------------------------------

def fetch_paginated(
    session: requests.Session,
    url: str,
    odata_filter: Optional[str],
    timeout: int,
    extra_params: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch all pages from an OData endpoint, following @odata.nextLink.

    Optional ``extra_params`` (e.g. ``$expand``) are merged into the first request
    only; ``@odata.nextLink`` responses carry their own query string.

    Permission / access errors (403 Forbidden, 401 Unauthorized) are treated as
    "this endpoint is not accessible with the current service principal" — the
    function logs a warning and returns an empty list so that other entity
    fetches continue unaffected.

    Transient server errors (429, 5xx) are handled by the urllib3 Retry policy
    on the session adapter. Any other unexpected HTTP error is also logged and
    returns an empty list rather than exiting.
    """
    params: Dict[str, Any] = {}
    if odata_filter:
        params["$filter"] = odata_filter
    if extra_params:
        params.update(extra_params)

    results: List[Dict[str, Any]] = []
    next_url: Optional[str] = url

    while next_url:
        try:
            if params and next_url == url:
                resp = session.get(next_url, params=params, timeout=timeout)
            else:
                # nextLink already includes query parameters
                resp = session.get(next_url, timeout=timeout)
        except requests.RequestException as exc:
            sys.stderr.write(f"[WARN] Network error fetching {url}: {exc} — skipping entity.\n")
            return []

        # Permission / auth errors: skip entity, do not abort the whole run
        if resp.status_code in (401, 403):
            try:
                detail = resp.json().get("error", {}).get("message", resp.text[:200])
            except Exception:
                detail = resp.text[:200]
            sys.stderr.write(
                f"[WARN] {resp.status_code} {resp.reason} for {url} — "
                f"app registration may lack the required Dynamics 365 privilege. "
                f"Skipping entity. Detail: {detail}\n"
            )
            return []

        # Any other HTTP error: log and skip
        if not resp.ok:
            sys.stderr.write(
                f"[WARN] HTTP {resp.status_code} {resp.reason} for {url} — skipping entity.\n"
            )
            return []

        try:
            payload = resp.json()
        except ValueError as exc:
            sys.stderr.write(f"[WARN] Invalid JSON from {url}: {exc} — skipping entity.\n")
            return []

        batch = payload.get("value")
        if not isinstance(batch, list):
            sys.stderr.write(f"[WARN] Unexpected API response from {url}: missing 'value' array — skipping entity.\n")
            return []

        results.extend(batch)
        next_url = payload.get("@odata.nextLink")

    return results


# ---------------------------------------------------------------------------
# Sparse record helper
# ---------------------------------------------------------------------------

def sparse_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Drop None values so NiFi/Avro treats missing keys as null."""
    return {k: v for k, v in rec.items() if v is not None}


# Order matches NiFi RouteOnAttribute checklist (SQL/CRM/NiFi-scope-note.md).
CRM_DATA_TYPES_ORDERED: List[str] = [
    "crm_inventory_account",
    "crm_inventory_product",
    "crm_inventory_pricelevel",
    "crm_inventory_productpricelevel",
    "crm_inventory_salesorder",
    "crm_inventory_salesorderdetail",
]


def _stderr_fetch_summary(entity: str, odata_rows: int, emitted: int) -> None:
    """One line per OData entity — use NiFi / container logs to compare with DB row counts."""
    sys.stderr.write(
        f"[INFO] crm-dynamics-discovery: {entity} odata_rows={odata_rows} emitted={emitted}\n"
    )


def _stderr_emit_histogram(records: List[Dict[str, Any]], verbose: bool) -> None:
    """
    Always emit a compact histogram to stderr so operators can confirm each data_type
    is present without parsing the single-line stdout JSON array.
    """
    dc = Counter((r.get("data_type") or "missing_data_type") for r in records)
    parts = [f"{t}={dc.get(t, 0)}" for t in CRM_DATA_TYPES_ORDERED]
    miss = dc.get("missing_data_type", 0)
    extra = ""
    if miss:
        extra = f" missing_data_type={miss}"
    sys.stderr.write(
        f"[INFO] crm-dynamics-discovery: stdout_json_array_length={len(records)} "
        f"{' '.join(parts)}{extra}\n"
    )
    if verbose:
        sys.stderr.write(f"[INFO] crm-dynamics-discovery: data_type_histogram_full={dict(dc)}\n")


# ---------------------------------------------------------------------------
# Normalizers — one per entity (6 data_types)
# ---------------------------------------------------------------------------

def normalize_account(raw: Dict[str, Any], collection_time: int) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_account",
        "accountid": normalize_string(raw.get("accountid")),
        "name": normalize_string(raw.get("name")),
        "accountnumber": normalize_string(raw.get("accountnumber")),
        "customertypecode_value": normalize_int(raw.get("customertypecode")),
        "customertypecode_text": _fv(raw, "customertypecode"),
        "parentaccountid": _lookup_id(raw, "parentaccountid"),
        "parentaccount_name": _lookup_name(raw, "parentaccountid"),
        "primarycontactid": _lookup_id(raw, "primarycontactid"),
        "primarycontact_name": _lookup_name(raw, "primarycontactid"),
        "ownerid": _lookup_id(raw, "ownerid"),
        "owner_name": _lookup_name(raw, "ownerid"),
        "statecode": normalize_int(raw.get("statecode")),
        "statecode_text": _fv(raw, "statecode"),
        "statuscode": normalize_int(raw.get("statuscode")),
        "statuscode_text": _fv(raw, "statuscode"),
        "telephone1": normalize_string(raw.get("telephone1")),
        "address1_line1": normalize_string(raw.get("address1_line1")),
        "address1_city": normalize_string(raw.get("address1_city")),
        "address1_country": normalize_string(raw.get("address1_country")),
        "industrycode": normalize_int(raw.get("industrycode")),
        "industrycode_text": _fv(raw, "industrycode"),
        "revenue": normalize_float(raw.get("revenue")),
        "numberofemployees": normalize_int(raw.get("numberofemployees")),
        "transactioncurrencyid": _lookup_id(raw, "transactioncurrencyid"),
        "transactioncurrency_text": _lookup_name(raw, "transactioncurrencyid"),
        "createdon": normalize_timestamp_millis(raw.get("createdon")),
        "modifiedon": normalize_timestamp_millis(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_product(raw: Dict[str, Any], collection_time: int) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_product",
        "productid": normalize_string(raw.get("productid")),
        "name": normalize_string(raw.get("name")),
        "productnumber": normalize_string(raw.get("productnumber")),
        "statecode": normalize_int(raw.get("statecode")),
        "statecode_text": _fv(raw, "statecode"),
        "statuscode": normalize_int(raw.get("statuscode")),
        "statuscode_text": _fv(raw, "statuscode"),
        "defaultuomid": _lookup_id(raw, "defaultuomid"),
        "defaultuomid_name": _fv(raw, "_defaultuomid_value"),
        "currentcost": normalize_float(raw.get("currentcost")),
        "standardcost": normalize_float(raw.get("standardcost")),
        "pricelevelid": _lookup_id(raw, "pricelevelid"),
        "pricelevel_name": _lookup_name(raw, "pricelevelid"),
        "blt_productgroup": normalize_int(raw.get("blt_productgroup")),
        "blt_productgroup_text": _fv(raw, "blt_productgroup"),
        "blt_productmodel": normalize_int(raw.get("blt_productmodel")),
        "blt_productmodel_text": _fv(raw, "blt_productmodel"),
        "blt_sectionorder": normalize_int(raw.get("blt_sectionorder")),
        "createdon": normalize_timestamp_millis(raw.get("createdon")),
        "modifiedon": normalize_timestamp_millis(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_pricelevel(raw: Dict[str, Any], collection_time: int) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_pricelevel",
        "pricelevelid": normalize_string(raw.get("pricelevelid")),
        "name": normalize_string(raw.get("name")),
        "transactioncurrencyid": _lookup_id(raw, "transactioncurrencyid"),
        "transactioncurrency_text": _lookup_name(raw, "transactioncurrencyid"),
        "exchangerate": normalize_float(raw.get("exchangerate")),
        "begindate": normalize_date(raw.get("begindate")),
        "enddate": normalize_date(raw.get("enddate")),
        "statecode": normalize_int(raw.get("statecode")),
        "statecode_text": _fv(raw, "statecode"),
        "createdon": normalize_timestamp_millis(raw.get("createdon")),
        "modifiedon": normalize_timestamp_millis(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_productpricelevel(raw: Dict[str, Any], collection_time: int) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_productpricelevel",
        "productpricelevelid": normalize_string(raw.get("productpricelevelid")),
        "pricelevelid": _lookup_id(raw, "pricelevelid"),
        "pricelevel_name": _lookup_name(raw, "pricelevelid"),
        "productid": _lookup_id(raw, "productid"),
        "product_name": _lookup_name(raw, "productid"),
        "uomid": _lookup_id(raw, "uomid"),
        "uomid_name": _fv(raw, "_uomid_value"),
        "amount": normalize_float(raw.get("amount")),
        "discounttypeid": _lookup_id(raw, "discounttypeid"),
        "pricingmethodcode": normalize_int(raw.get("pricingmethodcode")),
        "pricingmethodcode_text": _fv(raw, "pricingmethodcode"),
        "transactioncurrencyid": _lookup_id(raw, "transactioncurrencyid"),
        "transactioncurrency_text": _lookup_name(raw, "transactioncurrencyid"),
        "modifiedon": normalize_timestamp_millis(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_salesorder(raw: Dict[str, Any], collection_time: int) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_salesorder",
        "salesorderid": normalize_string(raw.get("salesorderid")),
        "name": normalize_string(raw.get("name")),
        "ordernumber": normalize_string(raw.get("ordernumber")),
        "customerid": _lookup_id(raw, "customerid"),
        "customerid_name": _lookup_name(raw, "customerid"),
        "opportunityid": _lookup_id(raw, "opportunityid"),
        "quoteid": _lookup_id(raw, "quoteid"),
        "ownerid": _lookup_id(raw, "ownerid"),
        "owner_name": _lookup_name(raw, "ownerid"),
        "totalamount": normalize_float(raw.get("totalamount")),
        "totaltax": normalize_float(raw.get("totaltax")),
        "totallineitemamount": normalize_float(raw.get("totallineitemamount")),
        "submitdate": normalize_date(raw.get("submitdate")),
        "fulfilldate": normalize_date(raw.get("fulfilldate")),
        "statecode": normalize_int(raw.get("statecode")),
        "statecode_text": _fv(raw, "statecode"),
        "statuscode": normalize_int(raw.get("statuscode")),
        "statuscode_text": _fv(raw, "statuscode"),
        "pricelevelid": _lookup_id(raw, "pricelevelid"),
        "pricelevel_name": _lookup_name(raw, "pricelevelid"),
        "transactioncurrencyid": _lookup_id(raw, "transactioncurrencyid"),
        "transactioncurrency_text": _lookup_name(raw, "transactioncurrencyid"),
        "createdon": normalize_timestamp_millis(raw.get("createdon")),
        "modifiedon": normalize_timestamp_millis(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_salesorderdetail(raw: Dict[str, Any], collection_time: int) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_salesorderdetail",
        "salesorderdetailid": normalize_string(raw.get("salesorderdetailid")),
        "salesorderid": _lookup_id(raw, "salesorderid"),
        "productid": _lookup_id(raw, "productid"),
        "product_name": _lookup_name(raw, "productid"),
        "productdescription": normalize_string(raw.get("productdescription")),
        "uomid": _lookup_id(raw, "uomid"),
        "uomid_name": _fv(raw, "_uomid_value"),
        "quantity": normalize_float(raw.get("quantity")),
        "priceperunit": normalize_float(raw.get("priceperunit")),
        "baseamount": normalize_float(raw.get("baseamount")),
        "extendedamount": normalize_float(raw.get("extendedamount")),
        "manualdiscountamount": normalize_float(raw.get("manualdiscountamount")),
        "transactioncurrencyid": _lookup_id(raw, "transactioncurrencyid"),
        "transactioncurrency_text": _lookup_name(raw, "transactioncurrencyid"),
        "modifiedon": normalize_timestamp_millis(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


# OData: realized orders only (Fulfilled=3, Invoiced=4 per Microsoft Learn salesorder_statecode).
REALIZED_SALESORDER_STATE_FILTER = "(statecode eq 3 or statecode eq 4)"

# Active master data only (Microsoft Learn: statecode 0 = Active for account/product).
ACTIVE_ACCOUNT_FILTER = "statecode eq 0"
ACTIVE_PRODUCT_FILTER = "statecode eq 0"

# Navigation property from salesorder to salesorderdetail (Learn: order_details).
SALESORDER_EXPAND_ORDER_DETAILS = (
    "order_details("
    "$select=salesorderdetailid,_salesorderid_value,_productid_value,productdescription,"
    "_uomid_value,quantity,priceperunit,baseamount,extendedamount,manualdiscountamount,"
    "_transactioncurrencyid_value,modifiedon"
    ")"
)


def build_realized_salesorder_odata_filter(since_filter: Optional[str]) -> str:
    """Combine optional modifiedon lookback with Fulfilled/Invoiced state filter."""
    if since_filter:
        return f"({since_filter}) and {REALIZED_SALESORDER_STATE_FILTER}"
    return REALIZED_SALESORDER_STATE_FILTER


def build_salesorder_odata_filter(
    since_filter: Optional[str], include_active_orders: bool
) -> Optional[str]:
    """
    OData $filter for salesorders.

    Production: Fulfilled (3) or Invoiced (4) only, optionally combined with modifiedon lookback.

    Test / sandbox: ``include_active_orders`` skips the state filter so Active (0) orders are
    included; if ``since_filter`` is set, only that window is applied; if both are unset
    (full snapshot + active), returns None so no $filter is sent (all states).
    """
    if include_active_orders:
        return since_filter
    return build_realized_salesorder_odata_filter(since_filter)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Dynamics 365 CRM discovery collector (stdout JSON array). "
            "Scope: active accounts, active catalog, realized salesorders + lines only."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--tenant-id", required=True, help="Azure AD / Entra ID tenant ID.")
    parser.add_argument("--client-id", required=True, help="App registration client ID.")
    parser.add_argument("--client-secret", required=True, help="App registration client secret.")
    parser.add_argument("--crm-url", required=True, help="CRM base URL, e.g. https://org.crm4.dynamics.com")
    parser.add_argument("--api-version", default="v9.2", help="Dynamics 365 Web API version.")
    parser.add_argument(
        "--lookback-hours", type=int, default=24,
        help="Rolling window for OData modifiedon filter on transactional entities (hours, UTC)."
    )
    parser.add_argument("--page-size", type=int, default=5000, help="OData maxpagesize preference.")
    parser.add_argument("--http-timeout-sec", type=int, default=60, help="HTTP request timeout seconds.")
    parser.add_argument("--http-retries", type=int, default=3, help="urllib3 retry count for 429/5xx.")
    parser.add_argument("--skip-accounts", action="store_true", help="Skip accounts (master data).")
    parser.add_argument("--skip-catalog", action="store_true", help="Skip product catalog entities.")
    parser.add_argument("--skip-sales", action="store_true", help="Skip realized sales (salesorders + lines).")
    parser.add_argument(
        "--full-snapshot", action="store_true",
        help="Ignore lookback-hours; fetch all records (initial backfill mode)."
    )
    parser.add_argument(
        "--include-active-orders", action="store_true",
        help=(
            "Do not restrict salesorders to Fulfilled/Invoiced (statecode 3/4). "
            "Use for CRM test orgs where orders stay Active (0). "
            "Still honors --lookback-hours unless --full-snapshot."
        ),
    )
    parser.add_argument(
        "--debug-token", action="store_true",
        help="Print decoded JWT claims and request details to stderr (diagnostic only)."
    )
    parser.add_argument(
        "--verbose-fetch", action="store_true",
        help=(
            "After each OData entity fetch, log odata_rows vs emitted JSON objects to stderr; "
            "also log full Counter keys if any unexpected data_type appears. "
            "Use when crm_inventory_productpricelevel is missing from stdout but analyze_scripts succeeds."
        ),
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    crm_url = args.crm_url.rstrip("/")
    api_base = f"{crm_url}/api/data/{args.api_version}/"
    timeout = args.http_timeout_sec

    # Build incremental filter cutoff
    since_filter: Optional[str] = None
    if not args.full_snapshot:
        since = datetime.now(timezone.utc) - timedelta(hours=args.lookback_hours)
        since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        since_filter = f"modifiedon ge {since_str}"

    # OAuth2
    token = get_access_token(
        args.tenant_id, args.client_id, args.client_secret, crm_url, timeout,
        debug=args.debug_token,
    )
    session = build_session(token, args.page_size, args.http_retries)
    collection_time = int(datetime.now(timezone.utc).timestamp() * 1000)

    records: List[Dict[str, Any]] = []

    verbose_fetch = args.verbose_fetch

    # --- Master: Accounts (no incremental filter — always full snapshot) ---
    if not args.skip_accounts:
        account_items = fetch_paginated(session, f"{api_base}accounts", ACTIVE_ACCOUNT_FILTER, timeout)
        acc_emitted = 0
        for item in account_items:
            if not isinstance(item, dict):
                continue
            rec = normalize_account(item, collection_time)
            if rec.get("accountid"):
                records.append(sparse_record(rec))
                acc_emitted += 1
        if verbose_fetch:
            _stderr_fetch_summary("accounts", len(account_items), acc_emitted)

    # --- Catalog (no incremental filter) ---
    if not args.skip_catalog:
        product_items = fetch_paginated(session, f"{api_base}products", ACTIVE_PRODUCT_FILTER, timeout)
        prod_emitted = 0
        for item in product_items:
            if not isinstance(item, dict):
                continue
            rec = normalize_product(item, collection_time)
            if rec.get("productid"):
                records.append(sparse_record(rec))
                prod_emitted += 1
        if verbose_fetch:
            _stderr_fetch_summary("products", len(product_items), prod_emitted)

        pl_items = fetch_paginated(session, f"{api_base}pricelevels", None, timeout)
        pl_emitted = 0
        for item in pl_items:
            if not isinstance(item, dict):
                continue
            rec = normalize_pricelevel(item, collection_time)
            if rec.get("pricelevelid"):
                records.append(sparse_record(rec))
                pl_emitted += 1
        if verbose_fetch:
            _stderr_fetch_summary("pricelevels", len(pl_items), pl_emitted)

        ppl_items = fetch_paginated(session, f"{api_base}productpricelevels", None, timeout)
        ppl_emitted = 0
        for item in ppl_items:
            if not isinstance(item, dict):
                continue
            rec = normalize_productpricelevel(item, collection_time)
            if rec.get("productpricelevelid"):
                records.append(sparse_record(rec))
                ppl_emitted += 1
        if verbose_fetch:
            _stderr_fetch_summary("productpricelevels", len(ppl_items), ppl_emitted)

    # --- Realized sales: Fulfilled/Invoiced salesorders + expanded line items ---
    if not args.skip_sales:
        so_filter = build_salesorder_odata_filter(since_filter, args.include_active_orders)
        expand_params = {"$expand": SALESORDER_EXPAND_ORDER_DETAILS}
        sales_items = fetch_paginated(
            session, f"{api_base}salesorders", so_filter, timeout, extra_params=expand_params
        )
        sales_emitted = 0
        for item in sales_items:
            if not isinstance(item, dict):
                continue
            order_lines = item.get("order_details")
            # Emit header (normalize ignores unknown keys such as order_details)
            so_rec = normalize_salesorder(item, collection_time)
            if so_rec.get("salesorderid"):
                records.append(sparse_record(so_rec))
                sales_emitted += 1
            so_id = normalize_string(item.get("salesorderid"))
            if isinstance(order_lines, list):
                for line in order_lines:
                    if not isinstance(line, dict):
                        continue
                    detail_raw = dict(line)
                    if so_id and not detail_raw.get("_salesorderid_value"):
                        detail_raw["_salesorderid_value"] = so_id
                    det_rec = normalize_salesorderdetail(detail_raw, collection_time)
                    if det_rec.get("salesorderdetailid"):
                        records.append(sparse_record(det_rec))
                        sales_emitted += 1
        if verbose_fetch:
            _stderr_fetch_summary("salesorders+expanded_lines", len(sales_items), sales_emitted)

    _stderr_emit_histogram(records, verbose=verbose_fetch)

    sys.stdout.write(json.dumps(records, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
