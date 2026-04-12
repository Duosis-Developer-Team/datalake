# -*- coding: utf-8 -*-
"""Unit tests for ServiceCore discovery normalization helpers."""
import importlib.util
import json
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
normalize_user = _MOD.normalize_user
sparse_record = _MOD.sparse_record
parse_args = _MOD.parse_args
_http_retry_policy = _MOD._http_retry_policy
_origin_from_name = _MOD._origin_from_name


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
            "AgentFullName": "Agent Smith",
            "OrgUserSupportAccountName": "acme.com",
            "OrgUserSupportAccountId": 2605,
            "SlaPolicyName": "P3 SLA",
            "CompanyName": "Acme",
            "TimesReopen": 2,
            "IsActive": True,
            "IsDeleted": False,
            "IsMerged": False,
            "CreatedDate": "2024-01-15T10:00:00",
            "LastUpdatedDate": "2024-01-16T12:00:00",
            "TargetResolutionDate": "2024-01-20T18:00:00",
            "ClosedAndDoneDate": "2024-01-17T08:00:00",
            "CodePrefix": "#INC153344",
            "Guid": "abc-123",
            "TicketDescriptionTextFormat": "plain text",
            "CustomFieldsJson": "{}",
            "AttachmentFiles": ["a.eml"],
            "OriginFromName": "Email",
        }
        ts = "2026-04-12T12:00:00+00:00"
        rec = normalize_incident(raw, ts)
        self.assertEqual(rec["data_type"], "servicecore_inventory_incident")
        self.assertEqual(rec["ticket_id"], 153344)
        self.assertEqual(rec["subject"], "Test subject")
        self.assertEqual(rec["origin_from_name"], "Email")
        self.assertEqual(rec["agent_full_name"], "Agent Smith")
        self.assertEqual(rec["org_user_support_account_name"], "acme.com")
        self.assertEqual(rec["org_user_support_account_id"], 2605)
        self.assertEqual(rec["sla_policy_name"], "P3 SLA")
        self.assertEqual(rec["company_name"], "Acme")
        self.assertEqual(rec["times_reopen"], 2)
        self.assertTrue(rec["is_active"])
        self.assertFalse(rec["is_deleted"])
        self.assertFalse(rec["is_merged"])
        self.assertIn("a.eml", rec["attachment_files"] or "")
        self.assertEqual(rec["collection_time"], ts)
        self.assertNotIn("user_id", rec)
        self.assertNotIn("service_request_id", rec)

    def test_nested_origin_ticket_origin_from_name(self):
        raw = {
            "TicketId": 1,
            "TicketSubject": "x",
            "Ticket_OriginFrom": {"TicketOriginFromName": "Portal"},
        }
        self.assertEqual(_origin_from_name(raw), "Portal")

    def test_nested_origin_missing(self):
        raw = {"TicketId": 1, "TicketSubject": "x"}
        rec = normalize_incident(raw, "2026-01-01T00:00:00+00:00")
        self.assertIsNone(rec["origin_from_name"])


class TestSparseRecord(unittest.TestCase):
    def test_drops_none_keeps_false_and_zero(self):
        inp = {"a": 1, "b": None, "c": False, "d": 0, "e": ""}
        # empty string is kept as value (not None)
        out = sparse_record(inp)
        self.assertEqual(out, {"a": 1, "c": False, "d": 0, "e": ""})


class TestNormalizeServiceRequest(unittest.TestCase):
    def test_maps_fields(self):
        raw = {
            "ServiceRequestId": 102246,
            "ServiceRequestName": "REQ name",
            "Subject": "SR subject line",
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
            "AgentId": 99,
            "AgentGroupId": 5,
            "AgentGroupName": "Desk",
            "AgentFullName": "Support Agent",
            "OrgUserSupportAccountName": "tenant.org",
            "OrgUserSupportAccountId": 42,
            "SlaPolicyName": "",
            "CompanyName": "Co",
            "OriginFromName": "Portal",
            "Tags": "tag1",
            "RequestDate": "2024-02-01T09:00:00",
            "TargetResolutionDate": "2024-02-10T09:00:00",
            "TargetResponseDate": "2024-02-02T09:00:00",
            "DeletedDate": None,
            "IsActive": True,
            "IsDeleted": False,
            "CodePrefix": "#SR102246",
            "Guid": "g-1",
            "RequestDescriptionTextFormat": "desc",
            "CustomFieldsJson": "{}",
            "AttachmentFiles": ["b.eml"],
        }
        ts = "2026-04-12T12:00:00+00:00"
        rec = normalize_service_request(raw, ts)
        self.assertEqual(rec["data_type"], "servicecore_inventory_servicerequest")
        self.assertEqual(rec["service_request_id"], 102246)
        self.assertEqual(rec["subject"], "SR subject line")
        self.assertEqual(rec["agent_id"], 99)
        self.assertEqual(rec["agent_full_name"], "Support Agent")
        self.assertEqual(rec["org_user_support_account_id"], 42)
        self.assertEqual(rec["company_name"], "Co")
        self.assertFalse(rec["is_deleted"])
        self.assertIn("b.eml", rec["attachment_files"] or "")
        self.assertTrue(rec["is_active"])
        self.assertEqual(rec["collection_time"], ts)
        self.assertNotIn("ticket_id", rec)
        self.assertNotIn("user_id", rec)

    def test_subject_fallback_to_service_request_name(self):
        raw = {
            "ServiceRequestId": 1,
            "ServiceRequestName": "Fallback title",
            "RequesterId": 1,
        }
        rec = normalize_service_request(raw, "2026-01-01T00:00:00+00:00")
        self.assertEqual(rec["subject"], "Fallback title")


class TestNormalizeUser(unittest.TestCase):
    def test_maps_fields(self):
        raw = {
            "UserId": 4359,
            "Email": "user@example.com",
            "FullName": "Jane Doe",
            "JobTitle": "Engineer",
            "IsEnabled": True,
            "SoftDeleted": False,
        }
        ts = "2026-04-12T12:00:00+00:00"
        rec = normalize_user(raw, ts)
        self.assertEqual(rec["data_type"], "servicecore_inventory_user")
        self.assertEqual(rec["user_id"], 4359)
        self.assertEqual(rec["email"], "user@example.com")
        self.assertEqual(rec["full_name"], "Jane Doe")
        self.assertEqual(rec["job_title"], "Engineer")
        self.assertTrue(rec["is_enabled"])
        self.assertFalse(rec["soft_deleted"])
        self.assertEqual(rec["collection_time"], ts)
        self.assertNotIn("ticket_id", rec)


class TestHttpRetryPolicy(unittest.TestCase):
    def test_returns_retry_without_error(self):
        r = _http_retry_policy()
        self.assertIsNotNone(r)


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
        self.assertFalse(args.skip_users)

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
            "--skip-users",
        ]
        with mock.patch.object(sys, "argv", argv):
            args = parse_args()
        self.assertEqual(args.lookback_hours, 48)
        self.assertEqual(args.page_size, 50)
        self.assertTrue(args.skip_users)


class TestMainIntegration(unittest.TestCase):
    def test_main_skips_users_and_writes_sparse_json(self):
        argv = [
            "servicecore-discovery.py",
            "--api-url",
            "https://example.com/api/v1",
            "--api-key",
            "k",
            "--skip-users",
        ]
        fake_inc = [{"TicketId": 1, "TicketSubject": "t"}]
        fake_sr = []

        def fake_fetch(_session, _base, path, _filt, _ps):
            if path == "Incident/GetAll":
                return fake_inc
            if path == "ServiceRequest/GetAll":
                return fake_sr
            raise AssertionError(f"unexpected path {path}")

        captured = []

        def fake_write(s):
            captured.append(s)
            return len(s)

        with mock.patch.object(sys, "argv", argv):
            with mock.patch.object(_MOD, "fetch_paginated", side_effect=fake_fetch):
                with mock.patch.object(sys.stdout, "write", fake_write):
                    with mock.patch.object(sys.stdout, "flush", lambda: None):
                        _MOD.main()

        parsed = json.loads("".join(captured))
        self.assertEqual(len(parsed), 1)
        row = parsed[0]
        self.assertEqual(row.get("data_type"), "servicecore_inventory_incident")
        self.assertEqual(row.get("ticket_id"), 1)
        self.assertNotIn("user_id", row)
        self.assertNotIn("service_request_id", row)


if __name__ == "__main__":
    unittest.main()
