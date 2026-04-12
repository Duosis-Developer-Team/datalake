# -*- coding: utf-8 -*-
"""
ServiceCore ITSM discovery collector.

Fetches Incident, ServiceRequest, and User records via OData API, normalizes to flat JSON
for NiFi PutDatabaseRecord (UPSERT into discovery_* tables).

Each array element is sparse: only keys relevant to that record's data_type are emitted;
omitted keys correspond to null in the unified Avro schema (servicecore-discovery.json).

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


def _http_retry_policy() -> Retry:
    """Build urllib3 Retry compatible with both legacy and current urllib3."""
    base = dict(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
    )
    get_only = frozenset({"GET"})
    try:
        return Retry(allowed_methods=get_only, **base)
    except TypeError:
        # urllib3 < 1.26 uses method_whitelist
        try:
            return Retry(method_whitelist=get_only, **base)
        except TypeError:
            return Retry(**base)


def build_session(api_key: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "accept": "application/json",
            "ApiKey": api_key,
        }
    )
    retries = _http_retry_policy()
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


def _serialize_attachments(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    if isinstance(raw, (list, dict)):
        return json.dumps(raw, ensure_ascii=False)
    return normalize_string(raw)


def _origin_from_name(raw: Dict[str, Any]) -> Optional[str]:
    """Resolve origin channel: flat field first, then nested Ticket_OriginFrom."""
    flat = normalize_string(raw.get("OriginFromName"))
    if flat is not None:
        return flat
    nested = raw.get("Ticket_OriginFrom")
    if isinstance(nested, dict):
        return normalize_string(
            nested.get("TicketOriginFromName") or nested.get("OriginFromName")
        )
    return None


def normalize_incident(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    attachment_str = _serialize_attachments(raw.get("AttachmentFiles"))

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
        "agent_full_name": normalize_string(raw.get("AgentFullName")),
        "org_user_support_account_name": normalize_string(
            raw.get("OrgUserSupportAccountName")
        ),
        "org_user_support_account_id": normalize_int(raw.get("OrgUserSupportAccountId")),
        "sla_policy_name": normalize_string(raw.get("SlaPolicyName")),
        "company_name": normalize_string(raw.get("CompanyName")),
        "times_reopen": normalize_int(raw.get("TimesReopen")),
        "is_active": normalize_bool(raw.get("IsActive")),
        "is_deleted": normalize_bool(raw.get("IsDeleted")),
        "is_merged": normalize_bool(raw.get("IsMerged")),
        "created_date": normalize_datetime_iso(raw.get("CreatedDate")),
        "last_updated_date": normalize_datetime_iso(raw.get("LastUpdatedDate")),
        "target_resolution_date": normalize_datetime_iso(raw.get("TargetResolutionDate")),
        "closed_and_done_date": normalize_datetime_iso(raw.get("ClosedAndDoneDate")),
        "code_prefix": normalize_string(raw.get("CodePrefix")),
        "guid": normalize_string(raw.get("Guid")),
        "description_text_format": normalize_string(raw.get("TicketDescriptionTextFormat")),
        "custom_fields_json": normalize_string(raw.get("CustomFieldsJson")),
        "attachment_files": attachment_str,
        "origin_from_name": _origin_from_name(raw),
        "collection_time": collection_time,
    }


def normalize_service_request(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    attachment_str = _serialize_attachments(raw.get("AttachmentFiles"))
    subject = normalize_string(raw.get("Subject"))
    if subject is None:
        subject = normalize_string(raw.get("ServiceRequestName"))

    return {
        "data_type": "servicecore_inventory_servicerequest",
        "service_request_id": normalize_int(raw.get("ServiceRequestId")),
        "service_request_name": normalize_string(raw.get("ServiceRequestName")),
        "subject": subject,
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
        "agent_id": normalize_int(raw.get("AgentId")),
        "agent_group_id": normalize_int(raw.get("AgentGroupId")),
        "agent_group_name": normalize_string(raw.get("AgentGroupName")),
        "agent_full_name": normalize_string(raw.get("AgentFullName")),
        "org_user_support_account_name": normalize_string(
            raw.get("OrgUserSupportAccountName")
        ),
        "org_user_support_account_id": normalize_int(raw.get("OrgUserSupportAccountId")),
        "sla_policy_name": normalize_string(raw.get("SlaPolicyName")),
        "company_name": normalize_string(raw.get("CompanyName")),
        "origin_from_name": normalize_string(raw.get("OriginFromName")),
        "tags": normalize_string(raw.get("Tags")),
        "request_date": normalize_datetime_iso(raw.get("RequestDate")),
        "target_resolution_date": normalize_datetime_iso(raw.get("TargetResolutionDate")),
        "target_response_date": normalize_datetime_iso(raw.get("TargetResponseDate")),
        "deleted_date": normalize_datetime_iso(raw.get("DeletedDate")),
        "is_active": normalize_bool(raw.get("IsActive")),
        "is_deleted": normalize_bool(raw.get("IsDeleted")),
        "code_prefix": normalize_string(raw.get("CodePrefix")),
        "guid": normalize_string(raw.get("Guid")),
        "request_description_text_format": normalize_string(
            raw.get("RequestDescriptionTextFormat")
        ),
        "custom_fields_json": normalize_string(raw.get("CustomFieldsJson")),
        "attachment_files": attachment_str,
        "collection_time": collection_time,
    }


def normalize_user(raw: Dict[str, Any], collection_time: str) -> Dict[str, Any]:
    return {
        "data_type": "servicecore_inventory_user",
        "user_id": normalize_int(raw.get("UserId")),
        "email": normalize_string(raw.get("Email")),
        "full_name": normalize_string(raw.get("FullName")),
        "job_title": normalize_string(raw.get("JobTitle")),
        "is_enabled": normalize_bool(raw.get("IsEnabled")),
        "soft_deleted": normalize_bool(raw.get("SoftDeleted")),
        "collection_time": collection_time,
    }


def sparse_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Drop keys whose value is None so stdout JSON stays compact (NiFi/Avro: missing = null)."""
    return {k: v for k, v in rec.items() if v is not None}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ServiceCore ITSM discovery collector (stdout JSON array).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--api-url",
        required=True,
        help="Base API URL (e.g. https://operationsupportapi.example.com/api/v1).",
    )
    parser.add_argument(
        "--api-key",
        required=True,
        help="API key sent as ApiKey header.",
    )
    parser.add_argument(
        "--lookback-hours",
        type=int,
        default=24,
        help="Rolling window for OData $filter (hours, UTC).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="OData $top page size.",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="Optional; reserved for future auth flows (not used for GET endpoints).",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Optional; reserved for future auth flows (not used for GET endpoints).",
    )
    parser.add_argument(
        "--skip-users",
        action="store_true",
        help="Do not call User/GetAllUsers (faster smoke tests).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_url = str(args.api_url).rstrip("/")
    api_key = str(args.api_key)
    lookback_hours = int(args.lookback_hours)
    page_size = int(args.page_size)
    skip_users = bool(args.skip_users)

    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    filter_incident = f"LastUpdatedDate ge {since_str}"
    filter_sr = f"RequestDate ge {since_str}"
    # OData: always-true filter for full user catalog pagination.
    filter_users = "1 eq 1"

    session = build_session(api_key)
    collection_time = datetime.now(timezone.utc).isoformat()

    incidents_raw = fetch_paginated(
        session, api_url, "Incident/GetAll", filter_incident, page_size
    )
    sr_raw = fetch_paginated(
        session, api_url, "ServiceRequest/GetAll", filter_sr, page_size
    )
    users_raw: List[Dict[str, Any]] = []
    if not skip_users:
        users_raw = fetch_paginated(
            session, api_url, "User/GetAllUsers", filter_users, page_size
        )

    records: List[Dict[str, Any]] = []

    for item in incidents_raw:
        if not isinstance(item, dict):
            continue
        rec = normalize_incident(item, collection_time)
        if rec.get("ticket_id") is not None:
            records.append(sparse_record(rec))

    for item in sr_raw:
        if not isinstance(item, dict):
            continue
        rec = normalize_service_request(item, collection_time)
        if rec.get("service_request_id") is not None:
            records.append(sparse_record(rec))

    for item in users_raw:
        if not isinstance(item, dict):
            continue
        rec = normalize_user(item, collection_time)
        if rec.get("user_id") is not None:
            records.append(sparse_record(rec))

    sys.stdout.write(json.dumps(records, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
