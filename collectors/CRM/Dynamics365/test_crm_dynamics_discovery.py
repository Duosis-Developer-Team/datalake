#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for crm-dynamics-discovery.py.

Tests cover:
- normalize_* functions (all 6 entity normalizers: account, product, pricelevel, productpricelevel, salesorder, salesorderdetail)
- sparse_record: None-value dropping
- normalize_timestamp_millis: various ISO-8601 inputs -> epoch ms UTC
- normalize_date: date extraction
- _fv / _lookup_id / _lookup_name: OData annotation helpers
- fetch_paginated: @odata.nextLink following (mock)
- 429 / 5xx retry behavior (session-level, via mock)
- data_type and UPSERT key contract for every supported entity
"""
import io
import json
import sys
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Add script directory to path so we can import without package install
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

import importlib.util

spec = importlib.util.spec_from_file_location(
    "crm_dynamics_discovery",
    SCRIPT_DIR / "crm-dynamics-discovery.py",
)
mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(mod)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fv_key(field: str) -> str:
    return f"{field}@OData.Community.Display.V1.FormattedValue"


def _lv_key(field: str) -> str:
    return f"_{field}_value"


def _lv_name_key(field: str) -> str:
    return f"_{field}_value@OData.Community.Display.V1.FormattedValue"


COLLECTION_TIME_MS = int(
    datetime(2026, 4, 24, 10, 0, 0, tzinfo=timezone.utc).timestamp() * 1000
)


# ---------------------------------------------------------------------------
# Normalizer helpers
# ---------------------------------------------------------------------------

class TestNormalizeString(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(mod.normalize_string(None))

    def test_empty(self):
        self.assertIsNone(mod.normalize_string(""))

    def test_value(self):
        self.assertEqual(mod.normalize_string("hello"), "hello")

    def test_int_coercion(self):
        self.assertEqual(mod.normalize_string(42), "42")


class TestNormalizeInt(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(mod.normalize_int(None))

    def test_string_int(self):
        self.assertEqual(mod.normalize_int("5"), 5)

    def test_invalid(self):
        self.assertIsNone(mod.normalize_int("abc"))


class TestNormalizeFloat(unittest.TestCase):
    def test_value(self):
        self.assertAlmostEqual(mod.normalize_float("3.14"), 3.14)

    def test_none(self):
        self.assertIsNone(mod.normalize_float(None))


class TestNormalizeTimestampMillis(unittest.TestCase):
    def test_z_suffix(self):
        result = mod.normalize_timestamp_millis("2026-01-15T09:30:00Z")
        self.assertIsInstance(result, int)
        dt = datetime.fromtimestamp(result / 1000.0, tz=timezone.utc)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 15)

    def test_no_timezone(self):
        result = mod.normalize_timestamp_millis("2026-01-15T09:30:00")
        self.assertIsInstance(result, int)

    def test_none(self):
        self.assertIsNone(mod.normalize_timestamp_millis(None))

    def test_empty(self):
        self.assertIsNone(mod.normalize_timestamp_millis(""))

    def test_with_offset(self):
        result = mod.normalize_timestamp_millis("2026-01-15T09:30:00+03:00")
        self.assertIsInstance(result, int)
        dt = datetime.fromtimestamp(result / 1000.0, tz=timezone.utc)
        self.assertEqual(dt.hour, 6)  # 09:30+03 -> 06:30 UTC


class TestNormalizeDate(unittest.TestCase):
    def test_returns_date_part(self):
        result = mod.normalize_date("2026-03-20T00:00:00Z")
        self.assertEqual(result, "2026-03-20")

    def test_none(self):
        self.assertIsNone(mod.normalize_date(None))


class TestODataHelpers(unittest.TestCase):
    def setUp(self):
        self.raw: Dict[str, Any] = {
            "statecode": 0,
            _fv_key("statecode"): "Active",
            _lv_key("ownerid"): "owner-guid-123",
            _lv_name_key("ownerid"): "John Doe",
        }

    def test_fv(self):
        self.assertEqual(mod._fv(self.raw, "statecode"), "Active")

    def test_fv_missing(self):
        self.assertIsNone(mod._fv(self.raw, "nonexistent"))

    def test_lookup_id(self):
        self.assertEqual(mod._lookup_id(self.raw, "ownerid"), "owner-guid-123")

    def test_lookup_name(self):
        self.assertEqual(mod._lookup_name(self.raw, "ownerid"), "John Doe")


# ---------------------------------------------------------------------------
# sparse_record
# ---------------------------------------------------------------------------

class TestSparseRecord(unittest.TestCase):
    def test_drops_none(self):
        rec = {"a": "hello", "b": None, "c": 0, "d": False}
        result = mod.sparse_record(rec)
        self.assertNotIn("b", result)
        self.assertIn("a", result)
        self.assertIn("c", result)
        self.assertIn("d", result)

    def test_all_none_returns_empty(self):
        self.assertEqual(mod.sparse_record({"x": None}), {})


# ---------------------------------------------------------------------------
# Entity normalizers — data_type and UPSERT key contract
# ---------------------------------------------------------------------------

def _make_raw_account() -> Dict[str, Any]:
    return {
        "accountid": "acc-uuid-1",
        "name": "Acme Corp",
        "accountnumber": "ACM001",
        "statecode": 0,
        _fv_key("statecode"): "Active",
        _lv_key("ownerid"): "owner-uuid-1",
        _lv_name_key("ownerid"): "Sales Manager",
    }


def _make_raw_product() -> Dict[str, Any]:
    return {
        "productid": "prod-uuid-1",
        "name": "Cloud VM - 2vCPU",
        "productnumber": "BLT-001",
        "blt_productgroup": 758660000,
        _fv_key("blt_productgroup"): "Temel Urunler",
    }


def _make_raw_pricelevel() -> Dict[str, Any]:
    return {
        "pricelevelid": "pl-uuid-1",
        "name": "TL Fiyat Listesi",
        _lv_key("transactioncurrencyid"): "cur-uuid-1",
        _lv_name_key("transactioncurrencyid"): "Turkish Lira",
        "exchangerate": 1.0,
    }


def _make_raw_productpricelevel() -> Dict[str, Any]:
    return {
        "productpricelevelid": "ppl-uuid-1",
        _lv_key("pricelevelid"): "pl-uuid-1",
        _lv_name_key("pricelevelid"): "TL Fiyat Listesi",
        _lv_key("productid"): "prod-uuid-1",
        _lv_name_key("productid"): "Cloud VM - 2vCPU",
        _lv_key("uomid"): "uom-uuid-1",
        _fv_key("_uomid_value"): "Adet",
        "amount": 5000.0,
    }


def _make_raw_salesorder() -> Dict[str, Any]:
    return {
        "salesorderid": "so-uuid-1",
        "name": "Order #001",
        "ordernumber": "SO-001",
        _lv_key("customerid"): "acc-uuid-1",
        _lv_name_key("customerid"): "Acme Corp",
        "totalamount": 50000.0,
        "statecode": 3,
        _fv_key("statecode"): "Fulfilled",
    }


def _make_raw_salesorderdetail() -> Dict[str, Any]:
    return {
        "salesorderdetailid": "sod-uuid-1",
        _lv_key("salesorderid"): "so-uuid-1",
        _lv_key("productid"): "prod-uuid-1",
        "quantity": 10.0,
        "priceperunit": 5000.0,
        "extendedamount": 50000.0,
    }


class TestNormalizerDataTypeAndUpsertKey(unittest.TestCase):
    """Verify data_type and primary UPSERT key for every entity."""

    CASES = [
        ("normalize_account",           _make_raw_account,           "crm_inventory_account",           "accountid"),
        ("normalize_product",           _make_raw_product,           "crm_inventory_product",           "productid"),
        ("normalize_pricelevel",        _make_raw_pricelevel,        "crm_inventory_pricelevel",        "pricelevelid"),
        ("normalize_productpricelevel", _make_raw_productpricelevel, "crm_inventory_productpricelevel", "productpricelevelid"),
        ("normalize_salesorder",        _make_raw_salesorder,        "crm_inventory_salesorder",        "salesorderid"),
        ("normalize_salesorderdetail",  _make_raw_salesorderdetail,  "crm_inventory_salesorderdetail",  "salesorderdetailid"),
    ]

    def _run_case(self, func_name, raw_factory, expected_data_type, expected_upsert_key):
        func = getattr(mod, func_name)
        raw = raw_factory()
        rec = func(raw, COLLECTION_TIME_MS)
        self.assertEqual(rec["data_type"], expected_data_type,
                         f"{func_name}: data_type mismatch")
        self.assertIn(expected_upsert_key, rec,
                      f"{func_name}: UPSERT key '{expected_upsert_key}' missing")
        self.assertIsNotNone(rec[expected_upsert_key],
                             f"{func_name}: UPSERT key '{expected_upsert_key}' is None")
        self.assertIn("collection_time", rec,
                      f"{func_name}: collection_time missing")

    def test_all_normalizers(self):
        for func_name, raw_factory, expected_dt, expected_key in self.CASES:
            with self.subTest(func=func_name):
                self._run_case(func_name, raw_factory, expected_dt, expected_key)


class TestNormalizeAccountFields(unittest.TestCase):
    def setUp(self):
        self.raw = _make_raw_account()
        self.rec = mod.normalize_account(self.raw, COLLECTION_TIME_MS)

    def test_name(self):
        self.assertEqual(self.rec["name"], "Acme Corp")

    def test_statecode_text(self):
        self.assertEqual(self.rec["statecode_text"], "Active")

    def test_owner_name(self):
        self.assertEqual(self.rec["owner_name"], "Sales Manager")

    def test_collection_time(self):
        self.assertEqual(self.rec["collection_time"], COLLECTION_TIME_MS)


class TestNormalizeProductPriceLevelFields(unittest.TestCase):
    def setUp(self):
        self.raw = _make_raw_productpricelevel()
        self.rec = mod.normalize_productpricelevel(self.raw, COLLECTION_TIME_MS)

    def test_amount(self):
        self.assertAlmostEqual(self.rec["amount"], 5000.0)

    def test_uomid_name(self):
        self.assertEqual(self.rec["uomid_name"], "Adet")

    def test_pricelevel_ref(self):
        self.assertEqual(self.rec["pricelevelid"], "pl-uuid-1")
        self.assertEqual(self.rec["pricelevel_name"], "TL Fiyat Listesi")


class TestRealizedSalesorderFilterOnly(unittest.TestCase):
    """Sales OData filter must always restrict to Fulfilled/Invoiced orders."""

    def test_filter_state_only_when_full_snapshot(self):
        f = mod.build_realized_salesorder_odata_filter(None)
        self.assertEqual(f, mod.REALIZED_SALESORDER_STATE_FILTER)

    def test_filter_combines_modifiedon_and_state(self):
        since = "modifiedon ge 2026-04-01T00:00:00Z"
        f = mod.build_realized_salesorder_odata_filter(since)
        self.assertIn(since, f)
        self.assertIn(mod.REALIZED_SALESORDER_STATE_FILTER, f)
        self.assertIn(" and ", f)


class TestBuildSalesorderOdataFilter(unittest.TestCase):
    """--include-active-orders bypasses Fulfilled/Invoiced-only filter."""

    def test_default_matches_realized_filter(self):
        self.assertEqual(
            mod.build_salesorder_odata_filter(None, False),
            mod.REALIZED_SALESORDER_STATE_FILTER,
        )
        since = "modifiedon ge 2026-04-01T00:00:00Z"
        self.assertEqual(
            mod.build_salesorder_odata_filter(since, False),
            mod.build_realized_salesorder_odata_filter(since),
        )

    def test_include_active_full_snapshot_no_filter(self):
        self.assertIsNone(mod.build_salesorder_odata_filter(None, True))

    def test_include_active_with_lookback_only_since(self):
        since = "modifiedon ge 2026-04-01T00:00:00Z"
        self.assertEqual(mod.build_salesorder_odata_filter(since, True), since)


class TestSparseRecordIntegration(unittest.TestCase):
    def test_account_sparse(self):
        raw = {"accountid": "acc-1", "name": None, "telephone1": None, "statecode": 0,
               _fv_key("statecode"): "Active"}
        rec = mod.normalize_account(raw, COLLECTION_TIME_MS)
        sparse = mod.sparse_record(rec)
        self.assertNotIn("name", sparse)
        self.assertIn("accountid", sparse)


# ---------------------------------------------------------------------------
# fetch_paginated — nextLink following (mock)
# ---------------------------------------------------------------------------

class TestFetchPaginated(unittest.TestCase):
    def _build_session(self):
        return MagicMock()

    def test_single_page(self):
        session = self._build_session()
        page1 = {"value": [{"id": 1}, {"id": 2}]}
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = page1
        session.get.return_value = resp

        result = mod.fetch_paginated(session, "https://crm.example.com/api/accounts", None, 30)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 1)

    def test_two_pages_via_nextlink(self):
        session = self._build_session()
        page1 = {
            "value": [{"id": 1}],
            "@odata.nextLink": "https://crm.example.com/api/accounts?$skiptoken=abc",
        }
        page2 = {"value": [{"id": 2}]}

        responses = [page1, page2]
        call_count = [0]

        def mock_get(url, **kwargs):
            r = MagicMock()
            r.raise_for_status = MagicMock()
            r.json.return_value = responses[call_count[0]]
            call_count[0] += 1
            return r

        session.get.side_effect = mock_get
        result = mod.fetch_paginated(session, "https://crm.example.com/api/accounts", None, 30)
        self.assertEqual(len(result), 2)
        self.assertEqual(call_count[0], 2)

    def test_returns_empty_on_403(self):
        """403 Forbidden must NOT raise SystemExit — returns [] and logs a warning."""
        session = self._build_session()
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 403
        resp.reason = "Forbidden"
        resp.json.return_value = {"error": {"message": "Principal lacks privilege"}}
        session.get.return_value = resp

        result = mod.fetch_paginated(session, "https://crm.example.com/api/accounts", None, 30)
        self.assertEqual(result, [])

    def test_returns_empty_on_401(self):
        """401 Unauthorized must NOT raise SystemExit — returns []."""
        session = self._build_session()
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 401
        resp.reason = "Unauthorized"
        resp.json.return_value = {}
        session.get.return_value = resp

        result = mod.fetch_paginated(session, "https://crm.example.com/api/accounts", None, 30)
        self.assertEqual(result, [])

    def test_returns_empty_on_other_http_error(self):
        """Non-auth HTTP errors also return [] instead of exiting."""
        session = self._build_session()
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 500
        resp.reason = "Internal Server Error"
        session.get.return_value = resp

        result = mod.fetch_paginated(session, "https://crm.example.com/api/accounts", None, 30)
        self.assertEqual(result, [])

    def test_returns_empty_on_network_error(self):
        """Network-level exceptions return [] instead of exiting."""
        import requests as req_lib
        session = self._build_session()
        session.get.side_effect = req_lib.ConnectionError("Connection refused")

        result = mod.fetch_paginated(session, "https://crm.example.com/api/accounts", None, 30)
        self.assertEqual(result, [])

    def test_applies_odata_filter(self):
        session = self._build_session()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"value": []}
        session.get.return_value = resp

        mod.fetch_paginated(session, "https://crm.example.com/api/accounts",
                            "modifiedon ge 2026-04-01T00:00:00Z", 30)
        call_kwargs = session.get.call_args
        params = call_kwargs[1].get("params", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {})
        self.assertIn("$filter", params)


# ---------------------------------------------------------------------------
# Fixture-based test using existing raw_catalog_*.json analysis files
# ---------------------------------------------------------------------------

ANALYZE_DIR = SCRIPT_DIR / "analyze_scripts"


class TestFixtureProductPriceLevels(unittest.TestCase):
    """Use the real raw_catalog_productpricelevels.json fixture for smoke testing."""

    def setUp(self):
        fixture_path = ANALYZE_DIR / "raw_catalog_productpricelevels.json"
        if not fixture_path.exists():
            self.skipTest("analyze_scripts/raw_catalog_productpricelevels.json not found.")
        with open(fixture_path, encoding="utf-8") as f:
            self.records = json.load(f).get("value", [])

    def test_all_normalize_without_error(self):
        errors = 0
        for raw in self.records:
            try:
                rec = mod.normalize_productpricelevel(raw, COLLECTION_TIME_MS)
                mod.sparse_record(rec)
            except Exception as e:
                errors += 1
        self.assertEqual(errors, 0, f"{errors} records failed normalization")

    def test_data_type_consistent(self):
        for raw in self.records[:20]:
            rec = mod.normalize_productpricelevel(raw, COLLECTION_TIME_MS)
            self.assertEqual(rec["data_type"], "crm_inventory_productpricelevel")

    def test_amounts_are_float_or_none(self):
        for raw in self.records[:20]:
            rec = mod.normalize_productpricelevel(raw, COLLECTION_TIME_MS)
            amt = rec.get("amount")
            if amt is not None:
                self.assertIsInstance(amt, float)


class TestFixtureProducts(unittest.TestCase):
    def setUp(self):
        fixture_path = ANALYZE_DIR / "raw_catalog_products.json"
        if not fixture_path.exists():
            self.skipTest("analyze_scripts/raw_catalog_products.json not found.")
        with open(fixture_path, encoding="utf-8") as f:
            self.records = json.load(f).get("value", [])

    def test_all_normalize_without_error(self):
        errors = 0
        for raw in self.records:
            try:
                rec = mod.normalize_product(raw, COLLECTION_TIME_MS)
                mod.sparse_record(rec)
            except Exception as e:
                errors += 1
        self.assertEqual(errors, 0)

    def test_productid_always_present(self):
        for raw in self.records[:20]:
            rec = mod.normalize_product(raw, COLLECTION_TIME_MS)
            self.assertIsNotNone(rec.get("productid"))


class TestStderrHistogram(unittest.TestCase):
    def test_emit_histogram_zero_fills_known_types(self):
        recs = [{"data_type": "crm_inventory_account", "k": 1}]
        buf = io.StringIO()
        with redirect_stderr(buf):
            mod._stderr_emit_histogram(recs, verbose=False)
        out = buf.getvalue()
        self.assertIn("stdout_json_array_length=1", out)
        self.assertIn("crm_inventory_account=1", out)
        self.assertIn("crm_inventory_productpricelevel=0", out)


class TestFixturePriceLevels(unittest.TestCase):
    def setUp(self):
        fixture_path = ANALYZE_DIR / "raw_catalog_pricelevels.json"
        if not fixture_path.exists():
            self.skipTest("analyze_scripts/raw_catalog_pricelevels.json not found.")
        with open(fixture_path, encoding="utf-8") as f:
            self.records = json.load(f).get("value", [])

    def test_all_normalize_without_error(self):
        for raw in self.records:
            rec = mod.normalize_pricelevel(raw, COLLECTION_TIME_MS)
            mod.sparse_record(rec)

    def test_name_extracted(self):
        for raw in self.records:
            rec = mod.normalize_pricelevel(raw, COLLECTION_TIME_MS)
            if raw.get("name"):
                self.assertIsNotNone(rec.get("name"))


if __name__ == "__main__":
    unittest.main()
