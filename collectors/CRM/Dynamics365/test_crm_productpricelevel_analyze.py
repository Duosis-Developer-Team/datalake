#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for analyze_scripts/crm_productpricelevel_analyze.py helpers."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import MagicMock

SCRIPT_DIR = Path(__file__).resolve().parent
ANALYZE_PATH = SCRIPT_DIR / "analyze_scripts" / "crm_productpricelevel_analyze.py"

spec = importlib.util.spec_from_file_location("crm_productpricelevel_analyze", ANALYZE_PATH)
mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
assert spec.loader is not None
spec.loader.exec_module(mod)


class TestCollectAllKeys(unittest.TestCase):
    def test_union_and_limit(self):
        rows = [
            {"a": 1, "b": 2},
            {"b": 3, "c": 4},
        ]
        keys = mod.collect_all_keys(rows, sample_limit=10)
        self.assertEqual(keys, {"a", "b", "c"})

    def test_respects_sample_limit(self):
        rows = [{"k": i} for i in range(100)]
        keys = mod.collect_all_keys(rows, sample_limit=3)
        self.assertEqual(keys, {"k"})


class TestFieldCoverageReport(unittest.TestCase):
    def test_typical_d365_keys_ok(self):
        crm_keys = {
            "productpricelevelid",
            "_pricelevelid_value",
            "_pricelevelid_value@OData.Community.Display.V1.FormattedValue",
            "_productid_value",
            "_productid_value@OData.Community.Display.V1.FormattedValue",
            "_uomid_value",
            "_uomid_value@OData.Community.Display.V1.FormattedValue",
            "amount",
            "_discounttypeid_value",
            "pricingmethodcode",
            "pricingmethodcode@OData.Community.Display.V1.FormattedValue",
            "_transactioncurrencyid_value",
            "_transactioncurrencyid_value@OData.Community.Display.V1.FormattedValue",
            "modifiedon",
        }
        rows = mod.field_coverage_report(crm_keys)
        statuses = [r[2] for r in rows]
        self.assertTrue(all(s == "OK" for s in statuses))


class TestPricelevelCrossCheck(unittest.TestCase):
    def test_balanced(self):
        ppl = [
            {"_pricelevelid_value": "pl-1"},
            {"_pricelevelid_value": "pl-1"},
        ]
        pl = [{"pricelevelid": "pl-1"}, {"pricelevelid": "pl-2"}]
        dist_ppl, dist_pl, warns = mod.pricelevel_cross_check(ppl, pl)
        self.assertEqual(dist_ppl, 1)
        self.assertEqual(dist_pl, 2)
        self.assertTrue(any("no productpricelevel" in w for w in warns))

    def test_orphan_pricelevel_in_ppl(self):
        ppl = [{"_pricelevelid_value": "orphan"}]
        pl = [{"pricelevelid": "pl-1"}]
        _, _, warns = mod.pricelevel_cross_check(ppl, pl)
        self.assertTrue(any("not in fetched pricelevels" in w for w in warns))


class TestFetchAllPages(unittest.TestCase):
    def test_follows_next_link(self):
        session = MagicMock()
        first = MagicMock()
        first.status_code = 200
        first.json.return_value = {
            "value": [{"id": "1"}],
            "@odata.nextLink": "https://x/page2",
        }
        second = MagicMock()
        second.status_code = 200
        second.json.return_value = {
            "value": [{"id": "2"}],
        }
        session.get.side_effect = [first, second]

        rows, pages, ok_pages, status = mod.fetch_all_pages(
            session, "https://x/page1", timeout=30,
        )
        self.assertEqual([r["id"] for r in rows], ["1", "2"])
        self.assertEqual(pages, 2)
        self.assertEqual(status, 200)
        self.assertEqual(session.get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
