#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynamics 365 CRM discovery collector.

Fetches Accounts, Product Catalog, Sales funnel (Opportunity → Quote → SalesOrder → Invoice)
and Contracts via the Dynamics 365 Web API (OData v4), normalizes records to sparse flat JSON
for NiFi PutDatabaseRecord (UPSERT into discovery_crm_* tables).

Each array element is sparse: only keys relevant to that record's data_type are emitted;
omitted keys correspond to null in the unified Avro schema (crm-dynamics-discovery.json).

Output: UTF-8 JSON array on stdout.
"""
from __future__ import annotations

import argparse
import json
import sys
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


def normalize_datetime_iso(value: Any) -> Optional[str]:
    """Return ISO-8601 string in UTC or None."""
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
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return s


def normalize_date(value: Any) -> Optional[str]:
    """Return date as ISO-8601 date string (YYYY-MM-DD) or None."""
    dt = normalize_datetime_iso(value)
    if dt is None:
        return None
    return dt[:10]


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


def get_access_token(tenant_id: str, client_id: str, client_secret: str, crm_url: str, timeout: int) -> str:
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": f"{crm_url.rstrip('/')}/.default",
    }
    resp = requests.post(token_url, data=payload, timeout=timeout)
    if resp.status_code != 200:
        sys.stderr.write(f"Token request failed ({resp.status_code}): {resp.text[:200]}\n")
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
        "Prefer": (
            f'odata.include-annotations="OData.Community.Display.V1.FormattedValue",'
            f"odata.maxpagesize={page_size}"
        ),
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
) -> List[Dict[str, Any]]:
    """
    Fetch all pages from an OData endpoint, following @odata.nextLink.

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


# ---------------------------------------------------------------------------
# Normalizers — one per entity (14 data_types)
# ---------------------------------------------------------------------------

def normalize_account(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
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
        "createdon": normalize_datetime_iso(raw.get("createdon")),
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_product(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
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
        "createdon": normalize_datetime_iso(raw.get("createdon")),
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_pricelevel(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
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
        "createdon": normalize_datetime_iso(raw.get("createdon")),
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_productpricelevel(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
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
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_opportunity(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_opportunity",
        "opportunityid": normalize_string(raw.get("opportunityid")),
        "name": normalize_string(raw.get("name")),
        "customerid": _lookup_id(raw, "customerid"),
        "customerid_name": _lookup_name(raw, "customerid"),
        "ownerid": _lookup_id(raw, "ownerid"),
        "owner_name": _lookup_name(raw, "ownerid"),
        "estimatedvalue": normalize_float(raw.get("estimatedvalue")),
        "actualvalue": normalize_float(raw.get("actualvalue")),
        "closeprobability": normalize_int(raw.get("closeprobability")),
        "estimatedclosedate": normalize_date(raw.get("estimatedclosedate")),
        "actualclosedate": normalize_date(raw.get("actualclosedate")),
        "statecode": normalize_int(raw.get("statecode")),
        "statecode_text": _fv(raw, "statecode"),
        "statuscode": normalize_int(raw.get("statuscode")),
        "statuscode_text": _fv(raw, "statuscode"),
        "salesstagecode": normalize_int(raw.get("salesstagecode")),
        "salesstagecode_text": _fv(raw, "salesstagecode"),
        "pricelevelid": _lookup_id(raw, "pricelevelid"),
        "pricelevel_name": _lookup_name(raw, "pricelevelid"),
        "transactioncurrencyid": _lookup_id(raw, "transactioncurrencyid"),
        "transactioncurrency_text": _lookup_name(raw, "transactioncurrencyid"),
        "totalamount": normalize_float(raw.get("totalamount")),
        "totaltax": normalize_float(raw.get("totaltax")),
        "createdon": normalize_datetime_iso(raw.get("createdon")),
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_opportunityproduct(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_opportunityproduct",
        "opportunityproductid": normalize_string(raw.get("opportunityproductid")),
        "opportunityid": _lookup_id(raw, "opportunityid"),
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
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_quote(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_quote",
        "quoteid": normalize_string(raw.get("quoteid")),
        "name": normalize_string(raw.get("name")),
        "quotenumber": normalize_string(raw.get("quotenumber")),
        "customerid": _lookup_id(raw, "customerid"),
        "customerid_name": _lookup_name(raw, "customerid"),
        "opportunityid": _lookup_id(raw, "opportunityid"),
        "ownerid": _lookup_id(raw, "ownerid"),
        "owner_name": _lookup_name(raw, "ownerid"),
        "totalamount": normalize_float(raw.get("totalamount")),
        "totaltax": normalize_float(raw.get("totaltax")),
        "totallineitemamount": normalize_float(raw.get("totallineitemamount")),
        "effectivefrom": normalize_date(raw.get("effectivefrom")),
        "effectiveto": normalize_date(raw.get("effectiveto")),
        "statecode": normalize_int(raw.get("statecode")),
        "statecode_text": _fv(raw, "statecode"),
        "statuscode": normalize_int(raw.get("statuscode")),
        "statuscode_text": _fv(raw, "statuscode"),
        "pricelevelid": _lookup_id(raw, "pricelevelid"),
        "pricelevel_name": _lookup_name(raw, "pricelevelid"),
        "transactioncurrencyid": _lookup_id(raw, "transactioncurrencyid"),
        "transactioncurrency_text": _lookup_name(raw, "transactioncurrencyid"),
        "createdon": normalize_datetime_iso(raw.get("createdon")),
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_quotedetail(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_quotedetail",
        "quotedetailid": normalize_string(raw.get("quotedetailid")),
        "quoteid": _lookup_id(raw, "quoteid"),
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
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_salesorder(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
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
        "createdon": normalize_datetime_iso(raw.get("createdon")),
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_salesorderdetail(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
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
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_invoice(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_invoice",
        "invoiceid": normalize_string(raw.get("invoiceid")),
        "name": normalize_string(raw.get("name")),
        "invoicenumber": normalize_string(raw.get("invoicenumber")),
        "customerid": _lookup_id(raw, "customerid"),
        "customerid_name": _lookup_name(raw, "customerid"),
        "salesorderid": _lookup_id(raw, "salesorderid"),
        "opportunityid": _lookup_id(raw, "opportunityid"),
        "ownerid": _lookup_id(raw, "ownerid"),
        "owner_name": _lookup_name(raw, "ownerid"),
        "totalamount": normalize_float(raw.get("totalamount")),
        "totaltax": normalize_float(raw.get("totaltax")),
        "totallineitemamount": normalize_float(raw.get("totallineitemamount")),
        "invoicedate": normalize_date(raw.get("invoicedate")),
        "duedate": normalize_date(raw.get("duedate")),
        "statecode": normalize_int(raw.get("statecode")),
        "statecode_text": _fv(raw, "statecode"),
        "statuscode": normalize_int(raw.get("statuscode")),
        "statuscode_text": _fv(raw, "statuscode"),
        "pricelevelid": _lookup_id(raw, "pricelevelid"),
        "pricelevel_name": _lookup_name(raw, "pricelevelid"),
        "transactioncurrencyid": _lookup_id(raw, "transactioncurrencyid"),
        "transactioncurrency_text": _lookup_name(raw, "transactioncurrencyid"),
        "createdon": normalize_datetime_iso(raw.get("createdon")),
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_invoicedetail(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_invoicedetail",
        "invoicedetailid": normalize_string(raw.get("invoicedetailid")),
        "invoiceid": _lookup_id(raw, "invoiceid"),
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
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_contract(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_contract",
        "contractid": normalize_string(raw.get("contractid")),
        "title": normalize_string(raw.get("title")),
        "contractnumber": normalize_string(raw.get("contractnumber")),
        "customerid": _lookup_id(raw, "customerid"),
        "customerid_name": _lookup_name(raw, "customerid"),
        "ownerid": _lookup_id(raw, "ownerid"),
        "owner_name": _lookup_name(raw, "ownerid"),
        "activeon": normalize_date(raw.get("activeon")),
        "expireson": normalize_date(raw.get("expireson")),
        "billingfrequencycode": normalize_int(raw.get("billingfrequencycode")),
        "billingfrequencycode_text": _fv(raw, "billingfrequencycode"),
        "totalprice": normalize_float(raw.get("totalprice")),
        "totallineitemdiscount": normalize_float(raw.get("totallineitemdiscount")),
        "statecode": normalize_int(raw.get("statecode")),
        "statecode_text": _fv(raw, "statecode"),
        "statuscode": normalize_int(raw.get("statuscode")),
        "statuscode_text": _fv(raw, "statuscode"),
        "transactioncurrencyid": _lookup_id(raw, "transactioncurrencyid"),
        "transactioncurrency_text": _lookup_name(raw, "transactioncurrencyid"),
        "createdon": normalize_datetime_iso(raw.get("createdon")),
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


def normalize_contractdetail(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    return {
        "data_type": "crm_inventory_contractdetail",
        "contractdetailid": normalize_string(raw.get("contractdetailid")),
        "contractid": _lookup_id(raw, "contractid"),
        "productid": _lookup_id(raw, "productid"),
        "product_name": _lookup_name(raw, "productid"),
        "productdescription": normalize_string(raw.get("productdescription")),
        "uomid": _lookup_id(raw, "uomid"),
        "uomid_name": _fv(raw, "_uomid_value"),
        "quantity": normalize_float(raw.get("quantity")),
        "price": normalize_float(raw.get("price")),
        "totalprice": normalize_float(raw.get("totalprice")),
        "discount": normalize_float(raw.get("discount")),
        "activeon": normalize_date(raw.get("activeon")),
        "expireson": normalize_date(raw.get("expireson")),
        "transactioncurrencyid": _lookup_id(raw, "transactioncurrencyid"),
        "transactioncurrency_text": _lookup_name(raw, "transactioncurrencyid"),
        "modifiedon": normalize_datetime_iso(raw.get("modifiedon")),
        "collection_time": collection_time,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dynamics 365 CRM discovery collector (stdout JSON array).",
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
    parser.add_argument("--skip-sales", action="store_true", help="Skip sales funnel entities.")
    parser.add_argument("--skip-contracts", action="store_true", help="Skip contract entities.")
    parser.add_argument(
        "--full-snapshot", action="store_true",
        help="Ignore lookback-hours; fetch all records (initial backfill mode)."
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
    token = get_access_token(args.tenant_id, args.client_id, args.client_secret, crm_url, timeout)
    session = build_session(token, args.page_size, args.http_retries)
    collection_time = datetime.now(timezone.utc).isoformat()

    records: List[Dict[str, Any]] = []

    # --- Master: Accounts (no incremental filter — always full snapshot) ---
    if not args.skip_accounts:
        for item in fetch_paginated(session, f"{api_base}accounts", None, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_account(item, collection_time)
            if rec.get("accountid"):
                records.append(sparse_record(rec))

    # --- Catalog (no incremental filter) ---
    if not args.skip_catalog:
        for item in fetch_paginated(session, f"{api_base}products", None, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_product(item, collection_time)
            if rec.get("productid"):
                records.append(sparse_record(rec))

        for item in fetch_paginated(session, f"{api_base}pricelevels", None, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_pricelevel(item, collection_time)
            if rec.get("pricelevelid"):
                records.append(sparse_record(rec))

        for item in fetch_paginated(session, f"{api_base}productpricelevels", None, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_productpricelevel(item, collection_time)
            if rec.get("productpricelevelid"):
                records.append(sparse_record(rec))

    # --- Sales funnel (incremental filter applies) ---
    if not args.skip_sales:
        for item in fetch_paginated(session, f"{api_base}opportunities", since_filter, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_opportunity(item, collection_time)
            if rec.get("opportunityid"):
                records.append(sparse_record(rec))

        for item in fetch_paginated(session, f"{api_base}opportunityproducts", since_filter, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_opportunityproduct(item, collection_time)
            if rec.get("opportunityproductid"):
                records.append(sparse_record(rec))

        for item in fetch_paginated(session, f"{api_base}quotes", since_filter, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_quote(item, collection_time)
            if rec.get("quoteid"):
                records.append(sparse_record(rec))

        for item in fetch_paginated(session, f"{api_base}quotedetails", since_filter, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_quotedetail(item, collection_time)
            if rec.get("quotedetailid"):
                records.append(sparse_record(rec))

        for item in fetch_paginated(session, f"{api_base}salesorders", since_filter, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_salesorder(item, collection_time)
            if rec.get("salesorderid"):
                records.append(sparse_record(rec))

        for item in fetch_paginated(session, f"{api_base}salesorderdetails", since_filter, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_salesorderdetail(item, collection_time)
            if rec.get("salesorderdetailid"):
                records.append(sparse_record(rec))

        for item in fetch_paginated(session, f"{api_base}invoices", since_filter, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_invoice(item, collection_time)
            if rec.get("invoiceid"):
                records.append(sparse_record(rec))

        for item in fetch_paginated(session, f"{api_base}invoicedetails", since_filter, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_invoicedetail(item, collection_time)
            if rec.get("invoicedetailid"):
                records.append(sparse_record(rec))

    # --- Contracts (incremental filter applies) ---
    if not args.skip_contracts:
        for item in fetch_paginated(session, f"{api_base}contracts", since_filter, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_contract(item, collection_time)
            if rec.get("contractid"):
                records.append(sparse_record(rec))

        for item in fetch_paginated(session, f"{api_base}contractdetails", since_filter, timeout):
            if not isinstance(item, dict):
                continue
            rec = normalize_contractdetail(item, collection_time)
            if rec.get("contractdetailid"):
                records.append(sparse_record(rec))

    sys.stdout.write(json.dumps(records, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
