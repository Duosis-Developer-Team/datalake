# -*- coding: utf-8 -*-
"""Unit tests for ServiceCore discovery normalization helpers."""
import importlib.util
import os
import sys
import unittest
from unittest import mock

_DIR = os.path.dirname(os.path.abspath(__file__))
_SPEC = importlib.util.spec_from_file_location(
    "servicecore_discovery",
    os.path.join(_DIR, "servicecore-discovery.py"),
)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MOD)

normalize_incident = _MOD.normalize_incident
normalize_service_request = _MOD.normalize_service_request
as_unified_incident = _MOD.as_unified_incident
as_unified_service_request = _MOD.as_unified_service_request
parse_args = _MOD.parse_args


class TestNormalizeIncident(unittest.TestCase):
    def test_maps_flat_fields(self):
        raw = {
            "TicketId": 153344,
            "TicketSubject": "Test subject",
            "State": 4,
            "StateText": "Close",
            "StatusId": 2,
            "StatusName": "Closed",
            "PriorityId": 3,
            "PriorityName": "P3",
            "CategoryId": 67,
            "CategoryName": "Other",
            "OrgUserId": 4359,
            "OrgUsersName": "Jane Doe",
            "AgentId": 1,
            "AgentGroupId": 10,
            "AgentGroupName": "NOC",
            "CreatedDate": "2024-01-15T10:00:00",
            "LastUpdatedDate": "2024-01-16T12:00:00",
            "TargetResolutionDate": "2024-01-20T18:00:00",
            "ClosedAndDoneDate": "2024-01-17T08:00:00",
            "CodePrefix": "#INC153344",
            "Guid": "abc-123",
            "TicketDescriptionTextFormat": "plain text",
            "CustomFieldsJson": "{}",
            "AttachmentFiles": ["a.eml"],
            "Ticket_OriginFrom": {"OriginFromName": "Email"},
        }
        ts = "2026-04-12T12:00:00+00:00"
        rec = normalize_incident(raw, ts)
        self.assertEqual(rec["data_type"], "servicecore_inventory_incident")
        self.assertEqual(rec["ticket_id"], 153344)
        self.assertEqual(rec["subject"], "Test subject")
        self.assertEqual(rec["origin_from_name"], "Email")
        self.assertIn("a.eml", rec["attachment_files"] or "")
        self.assertEqual(rec["collection_time"], ts)

    def test_nested_origin_missing(self):
        raw = {"TicketId": 1, "TicketSubject": "x"}
        rec = normalize_incident(raw, "2026-01-01T00:00:00+00:00")
        self.assertIsNone(rec["origin_from_name"])


class TestNormalizeServiceRequest(unittest.TestCase):
    def test_maps_fields(self):
        raw = {
            "ServiceRequestId": 102246,
            "ServiceRequestName": "REQ name",
            "RequesterId": 4359,
            "RequesterUserFullName": "John",
            "OrgUsersName": "John",
            "State": 4,
            "StateText": "Done",
            "StatusId": 1,
            "StatusName": "Open",
            "PriorityId": 2,
            "PriorityName": "P2",
            "CategoryName": "Cat",
            "ServiceCategoryName": "SvcCat",
            "ServiceItemNames": "Item",
            "AgentGroupId": 5,
            "AgentGroupName": "Desk",
            "OriginFromName": "Portal",
            "Tags": "tag1",
            "RequestDate": "2024-02-01T09:00:00",
            "TargetResolutionDate": "2024-02-10T09:00:00",
            "TargetResponseDate": "2024-02-02T09:00:00",
            "DeletedDate": None,
            "IsActive": True,
            "CodePrefix": "#SR102246",
            "Guid": "g-1",
            "RequestDescriptionTextFormat": "desc",
            "CustomFieldsJson": "{}",
        }
        ts = "2026-04-12T12:00:00+00:00"
        rec = normalize_service_request(raw, ts)
        self.assertEqual(rec["data_type"], "servicecore_inventory_servicerequest")
        self.assertEqual(rec["service_request_id"], 102246)
        self.assertTrue(rec["is_active"])
        self.assertEqual(rec["collection_time"], ts)


class TestParseArgs(unittest.TestCase):
    def test_required_api_flags(self):
        argv = [
            "servicecore-discovery.py",
            "--api-url",
            "https://example.com/api/v1",
            "--api-key",
            "secret",
        ]
        with mock.patch.object(sys, "argv", argv):
            args = parse_args()
        self.assertEqual(args.api_url, "https://example.com/api/v1")
        self.assertEqual(args.api_key, "secret")
        self.assertEqual(args.lookback_hours, 24)
        self.assertEqual(args.page_size, 100)

    def test_optional_overrides(self):
        argv = [
            "prog",
            "--api-url",
            "https://x/v1",
            "--api-key",
            "k",
            "--lookback-hours",
            "48",
            "--page-size",
            "50",
        ]
        with mock.patch.object(sys, "argv", argv):
            args = parse_args()
        self.assertEqual(args.lookback_hours, 48)
        self.assertEqual(args.page_size, 50)


class TestUnifiedShape(unittest.TestCase):
    def test_incident_includes_null_service_request_fields(self):
        raw = {"TicketId": 1, "TicketSubject": "x"}
        rec = normalize_incident(raw, "2026-01-01T00:00:00+00:00")
        unified = as_unified_incident(rec)
        self.assertIsNone(unified.get("service_request_id"))
        self.assertIsNone(unified.get("request_date"))
        self.assertEqual(unified.get("ticket_id"), 1)

    def test_service_request_includes_null_incident_fields(self):
        raw = {"ServiceRequestId": 99, "ServiceRequestName": "n"}
        rec = normalize_service_request(raw, "2026-01-01T00:00:00+00:00")
        unified = as_unified_service_request(rec)
        self.assertIsNone(unified.get("ticket_id"))
        self.assertIsNone(unified.get("created_date"))
        self.assertEqual(unified.get("service_request_id"), 99)


if __name__ == "__main__":
    unittest.main()
