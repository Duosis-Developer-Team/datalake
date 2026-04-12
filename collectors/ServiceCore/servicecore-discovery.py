# -*- coding: utf-8 -*-
"""
ServiceCore ITSM discovery collector.

Fetches Incident and ServiceRequest records via OData API, normalizes to flat JSON
for NiFi PutDatabaseRecord (UPSERT into discovery_* tables).

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


def load_config(config_path: str) -> Dict[str, Any]:
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            root = json.load(fh)
    except OSError:
        sys.stderr.write(f"Configuration file not readable: {config_path}\n")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"Invalid JSON in configuration file: {exc}\n")
        sys.exit(1)

    cfg = root.get("ServiceCore")
    if not isinstance(cfg, dict):
        sys.stderr.write("Missing or invalid 'ServiceCore' block in configuration.\n")
        sys.exit(1)

    required = {"api_url", "api_key", "lookback_hours", "page_size"}
    missing = required - cfg.keys()
    if missing:
        sys.stderr.write(f"ServiceCore config missing keys: {sorted(missing)}\n")
        sys.exit(1)

    return cfg


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


def normalize_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return bool(value)


def normalize_datetime_iso(value: Any) -> Optional[str]:
    """Return ISO-8601 string in UTC for JSON / DB, or None."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    s = str(value).strip()
    if not s:
        return None
    # API returns e.g. "2022-09-13T03:37:21.11" without Z
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        elif "+" in s[10:] or s.count("-") > 2:
            dt = datetime.fromisoformat(s)
        else:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return s


def build_session(api_key: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "accept": "application/json",
            "ApiKey": api_key,
        }
    )
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_paginated(
    session: requests.Session,
    base_url: str,
    relative_path: str,
    odata_filter: str,
    page_size: int,
    timeout: int = 30,
) -> List[Dict[str, Any]]:
    """Fetch all pages from an OData GetAll endpoint."""
    base = base_url.rstrip("/")
    path = relative_path.lstrip("/")
    url = f"{base}/{path}"
    results: List[Dict[str, Any]] = []
    skip = 0

    while True:
        params: Dict[str, Any] = {
            "$filter": odata_filter,
            "$top": page_size,
            "$skip": skip,
        }
        try:
            resp = session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as exc:
            sys.stderr.write(f"HTTP request failed: {exc}\n")
            sys.exit(1)
        except ValueError as exc:
            sys.stderr.write(f"Invalid JSON response: {exc}\n")
            sys.exit(1)

        batch = payload.get("value")
        if not isinstance(batch, list):
            sys.stderr.write("Unexpected API response: missing 'value' array.\n")
            sys.exit(1)

        results.extend(batch)

        if len(batch) < page_size:
            break
        skip += page_size

    return results


def _nested_origin_from_name(raw: Dict[str, Any], key: str = "Ticket_OriginFrom") -> Optional[str]:
    nested = raw.get(key)
    if isinstance(nested, dict):
        return normalize_string(nested.get("OriginFromName"))
    return None


def normalize_incident(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    attachments = raw.get("AttachmentFiles")
    if attachments is None:
        attachment_str: Optional[str] = None
    elif isinstance(attachments, (list, dict)):
        attachment_str = json.dumps(attachments, ensure_ascii=False)
    else:
        attachment_str = normalize_string(attachments)

    origin = _nested_origin_from_name(raw, "Ticket_OriginFrom")

    return {
        "data_type": "servicecore_inventory_incident",
        "ticket_id": normalize_int(raw.get("TicketId")),
        "subject": normalize_string(raw.get("TicketSubject")),
        "state": normalize_int(raw.get("State")),
        "state_text": normalize_string(raw.get("StateText")),
        "status_id": normalize_int(raw.get("StatusId")),
        "status_name": normalize_string(raw.get("StatusName")),
        "priority_id": normalize_int(raw.get("PriorityId")),
        "priority_name": normalize_string(raw.get("PriorityName")),
        "category_id": normalize_int(raw.get("CategoryId")),
        "category_name": normalize_string(raw.get("CategoryName")),
        "org_user_id": normalize_int(raw.get("OrgUserId")),
        "org_users_name": normalize_string(raw.get("OrgUsersName")),
        "agent_id": normalize_int(raw.get("AgentId")),
        "agent_group_id": normalize_int(raw.get("AgentGroupId")),
        "agent_group_name": normalize_string(raw.get("AgentGroupName")),
        "created_date": normalize_datetime_iso(raw.get("CreatedDate")),
        "last_updated_date": normalize_datetime_iso(raw.get("LastUpdatedDate")),
        "target_resolution_date": normalize_datetime_iso(raw.get("TargetResolutionDate")),
        "closed_and_done_date": normalize_datetime_iso(raw.get("ClosedAndDoneDate")),
        "code_prefix": normalize_string(raw.get("CodePrefix")),
        "guid": normalize_string(raw.get("Guid")),
        "description_text_format": normalize_string(raw.get("TicketDescriptionTextFormat")),
        "custom_fields_json": normalize_string(raw.get("CustomFieldsJson")),
        "attachment_files": attachment_str,
        "origin_from_name": origin,
        "collection_time": collection_time,
    }


def normalize_service_request(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    return {
        "data_type": "servicecore_inventory_servicerequest",
        "service_request_id": normalize_int(raw.get("ServiceRequestId")),
        "service_request_name": normalize_string(raw.get("ServiceRequestName")),
        "requester_id": normalize_int(raw.get("RequesterId")),
        "requester_full_name": normalize_string(raw.get("RequesterUserFullName")),
        "org_users_name": normalize_string(raw.get("OrgUsersName")),
        "state": normalize_int(raw.get("State")),
        "state_text": normalize_string(raw.get("StateText")),
        "status_id": normalize_int(raw.get("StatusId")),
        "status_name": normalize_string(raw.get("StatusName")),
        "priority_id": normalize_int(raw.get("PriorityId")),
        "priority_name": normalize_string(raw.get("PriorityName")),
        "category_name": normalize_string(raw.get("CategoryName")),
        "service_category_name": normalize_string(raw.get("ServiceCategoryName")),
        "service_item_names": normalize_string(raw.get("ServiceItemNames")),
        "agent_group_id": normalize_int(raw.get("AgentGroupId")),
        "agent_group_name": normalize_string(raw.get("AgentGroupName")),
        "origin_from_name": normalize_string(raw.get("OriginFromName")),
        "tags": normalize_string(raw.get("Tags")),
        "request_date": normalize_datetime_iso(raw.get("RequestDate")),
        "target_resolution_date": normalize_datetime_iso(raw.get("TargetResolutionDate")),
        "target_response_date": normalize_datetime_iso(raw.get("TargetResponseDate")),
        "deleted_date": normalize_datetime_iso(raw.get("DeletedDate")),
        "is_active": normalize_bool(raw.get("IsActive")),
        "code_prefix": normalize_string(raw.get("CodePrefix")),
        "guid": normalize_string(raw.get("Guid")),
        "request_description_text_format": normalize_string(raw.get("RequestDescriptionTextFormat")),
        "custom_fields_json": normalize_string(raw.get("CustomFieldsJson")),
        "collection_time": collection_time,
    }


# Keys only present on service-request rows; null on incident rows (unified Avro schema).
_SERVICE_REQUEST_EMPTY: Dict[str, Any] = {
    "service_request_id": None,
    "service_request_name": None,
    "requester_id": None,
    "requester_full_name": None,
    "service_category_name": None,
    "service_item_names": None,
    "tags": None,
    "request_date": None,
    "target_response_date": None,
    "deleted_date": None,
    "is_active": None,
    "request_description_text_format": None,
}

# Keys only present on incident rows; null on service-request rows.
_INCIDENT_EMPTY: Dict[str, Any] = {
    "ticket_id": None,
    "subject": None,
    "category_id": None,
    "org_user_id": None,
    "agent_id": None,
    "created_date": None,
    "last_updated_date": None,
    "closed_and_done_date": None,
    "description_text_format": None,
    "attachment_files": None,
}


def as_unified_incident(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {**_SERVICE_REQUEST_EMPTY, **rec}


def as_unified_service_request(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {**_INCIDENT_EMPTY, **rec}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ServiceCore ITSM discovery collector (stdout JSON array)."
    )
    parser.add_argument(
        "-c",
        "--config",
        required=True,
        metavar="PATH",
        help="Path to JSON configuration file containing a ServiceCore block.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    api_url = str(config["api_url"]).rstrip("/")
    api_key = str(config["api_key"])
    lookback_hours = int(config["lookback_hours"])
    page_size = int(config["page_size"])

    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    filter_incident = f"LastUpdatedDate ge {since_str}"
    filter_sr = f"RequestDate ge {since_str}"

    session = build_session(api_key)
    collection_time = datetime.now(timezone.utc).isoformat()

    incidents_raw = fetch_paginated(
        session, api_url, "Incident/GetAll", filter_incident, page_size
    )
    sr_raw = fetch_paginated(
        session, api_url, "ServiceRequest/GetAll", filter_sr, page_size
    )

    records: List[Dict[str, Any]] = []

    for item in incidents_raw:
        if not isinstance(item, dict):
            continue
        rec = normalize_incident(item, collection_time)
        if rec.get("ticket_id") is not None:
            records.append(as_unified_incident(rec))

    for item in sr_raw:
        if not isinstance(item, dict):
            continue
        rec = normalize_service_request(item, collection_time)
        if rec.get("service_request_id") is not None:
            records.append(as_unified_service_request(rec))

    sys.stdout.write(json.dumps(records, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
