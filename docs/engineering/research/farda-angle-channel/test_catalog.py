"""Offline validation of the proposed data package; no Django database required."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from prepare_seed import prepare
from collect_catalog import CatalogParser, collect

ROOT = Path(__file__).resolve().parent


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads((ROOT / "source-catalog.json").read_text(encoding="utf-8"))
        cls.result = prepare(cls.snapshot)

    def test_all_source_rows_accounted_for(self):
        observed = sum(len(t["rows"]) for p in self.snapshot["pages"] for t in p["tables"])
        retained = sum(len(p["source_observations"]) for p in self.result["products"])
        rejected = sum(len(p["source_observations"]) for p in self.result["quarantine"])
        self.assertEqual(observed, retained + rejected)

    def test_unique_keys_slugs_and_scope(self):
        products = self.result["products"]
        self.assertEqual(len(products), len({p["key"] for p in products}))
        self.assertEqual(len(products), len({p["product"]["slug"] for p in products}))
        self.assertEqual({p["specifications"]["material_type"] for p in products}, {"angle", "channel"})

    def test_grade_header_is_not_silently_dropped(self):
        parser = CatalogParser()
        parser.feed('<h3>نبشی ST52</h3><table><tr><th>سایز</th><th>ضخامت</th><th>استاندارد</th><th>حالت</th><th>واحد</th></tr><tr><td>90*90</td><td>6</td><td>ST52</td><td>12 متری</td><td>کیلوگرم</td></tr></table>')
        with patch("collect_catalog.fetch", return_value=(parser,"test-hash")):
            data = collect("https://fardafoolad.com/angel-bar/st52-angel-bar")
        self.assertEqual(len(data["tables"]), 1)
        self.assertEqual(data["tables"][0]["rows"][0]["استاندارد"], "ST52")

    def test_safe_publication_and_no_foreign_price_or_offer(self):
        self.assertTrue(all(not c["is_active"] for c in self.result["categories"]))
        for p in self.result["products"]:
            self.assertFalse(p["product"]["is_active"])
            self.assertEqual(p["product"]["availability_status"], "inquiry")
            self.assertEqual(p["product"]["seo_index_mode"], "noindex")
            self.assertNotIn("price", p)
            self.assertNotIn("offers", p)
            self.assertNotIn("انبار تهران", p["specifications"]["factory"])
            self.assertIn(p["specifications"]["steel_grade"], ("", "ST52", "5SP"))
            for field in ("manufacturing_process", "surface_finish"):
                self.assertEqual(p["specifications"][field], "")

    def test_decimal_notation_and_no_cartesian_invention(self):
        self.assertTrue(any(p["specifications"]["thickness_mm"] == "2.5" for p in self.result["products"]))
        self.assertTrue(any(any(s["value"] == "6.5" for s in p["dynamic_specs"]) for p in self.result["products"]))
        self.assertTrue(all(p["source_observations"] for p in self.result["products"]))
        self.assertEqual(len(self.result["empty_source_pages"]), 1)
        self.assertEqual(sum(p["specifications"]["steel_grade"] == "ST52" for p in self.result["products"]), 5)
        self.assertEqual(sum(p["specifications"]["steel_grade"] == "5SP" for p in self.result["products"]), 9)

    def test_invalid_unit_and_length_quarantined(self):
        self.assertEqual(len(self.result["quarantine"]), 3)
        self.assertTrue(all(p["issues"] for p in self.result["quarantine"]))
        for p in self.result["products"]:
            self.assertIn(p["specifications"]["length_mm"], ("6000", "12000"))
            if p["specifications"]["material_type"] == "channel":
                self.assertIsNone(p["specifications"]["height_mm"])
                self.assertIsNone(p["specifications"]["thickness_mm"])

    def test_seo_bounds_and_owned_canonical(self):
        for p in self.result["products"]:
            product = p["product"]
            for field, limit in (("name",255),("seo_title",255),("page_h1",255),("slug",500),("meta_description",320),("short_description",500)):
                self.assertLessEqual(len(product[field]), limit)
                self.assertTrue(product[field])
            self.assertEqual(p["canonical_path"], "/products/" + product["slug"])
            self.assertNotIn("fardafoolad", product["description"])
            self.assertNotIn("امروز", product["seo_title"])

    def test_saved_candidate_is_reproducible(self):
        saved = json.loads((ROOT / "seed-candidate.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, self.result)


if __name__ == "__main__":
    unittest.main()
