from decimal import Decimal
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Seller
from .models import Product, ProductCategory, ProductSpecification, ProductAttributeOption, Offer, PricingTier
from .market_hierarchy import build_market_hierarchy


class DomesticHierarchyTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="map-seller", password="pass")
        self.seller = Seller.objects.create(user=user, company_name="Map", business_type="Trading", location="Tehran")
        self.sheet = ProductCategory.objects.create(name="ورق نقشه", code="map-sheet", product_kind="sheet")
        self.black = ProductCategory.objects.create(name="ورق سیاه نقشه", code="map-black", parent=self.sheet, spec_defaults={"surface_finish": "black"})
        self.rebar = ProductCategory.objects.create(name="میلگرد نقشه", code="map-rebar", product_kind="rebar")
        ProductAttributeOption.objects.create(group="factory", value="map-a", label="کارخانه الف", product_kind="sheet")
        ProductAttributeOption.objects.create(group="factory", value="map-b", label="کارخانه ب", product_kind="sheet")
        self.a = self.make_product("ورق تست الف", self.black, factory="map-a")
        self.b = self.make_product("ورق تست ب", self.black, factory="map-b")
        self.oiled = self.make_product("ورق تست روغنی", self.sheet, factory="map-a", surface_finish="oiled")
        self.bar = self.make_product("میلگرد تست", self.rebar, factory="map-a", surface_finish="ribbed")
        self.make_product("غیرفعال", self.black, active=False, factory="map-a")

    def make_product(self, name, category, active=True, **spec):
        product = Product.objects.create(name=name, category=category, is_active=active)
        ProductSpecification.objects.create(product=product, **spec)
        offer = Offer.objects.create(product=product, seller=self.seller, is_active=True)
        PricingTier.objects.create(offer=offer, tier_name="روز", price_basis="kg", unit_price=1000, minimum_quantity=1)
        return product

    def test_tree_follows_kind_finish_factory_and_preserves_all_products(self):
        data = self.client.get("/api/market/summary/").data
        self.assertEqual(data["total"], 4)
        sheet = next(node for node in data["hierarchy"] if node["scope"]["kind"] == "sheet")
        self.assertEqual(sheet["count"], 3)
        black = next(node for node in sheet["children"] if node["scope"]["subtype"] == "black")
        self.assertEqual(black["name"], "ورق سیاه")
        self.assertEqual(black["count"], 2)
        factory = next(node for node in black["children"] if node["scope"]["factory"] == "map-a")
        self.assertEqual(factory["name"], "کارخانه الف")
        self.assertEqual(factory["children"][0]["product_id"], self.a.id)
        self.assertEqual(factory["children"][0]["scope"]["product_id"], str(self.a.id))
        self.assertIsNone(factory["average_change"])

    def test_each_scope_filters_table_before_pagination_and_intersects_search(self):
        cases = [({"kind": "sheet"}, {self.a.id, self.b.id, self.oiled.id}),
                 ({"kind": "sheet", "subtype": "black"}, {self.a.id, self.b.id}),
                 ({"kind": "sheet", "subtype": "black", "factory": "map-a"}, {self.a.id}),
                 ({"product_id": str(self.b.id)}, {self.b.id})]
        for scope, expected in cases:
            data = self.client.get("/api/market/products/", scope).data
            self.assertEqual({row["product_id"] for row in data["results"]}, expected)
        data = self.client.get("/api/market/products/", {"kind": "sheet", "subtype": "black", "page_size": 1, "page": 2}).data
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["results"]), 1)
        scoped = self.client.get("/api/market/products/", {"kind": "sheet", "search": "کارخانه ب"}).data
        self.assertEqual([row["product_id"] for row in scoped["results"]], [self.b.id])
        self.assertEqual(self.client.get("/api/market/products/", {"kind": "sheet", "subtype": "not-real"}).data["count"], 0)
        self.assertEqual(self.client.get("/api/market/products/").data["count"], 4)

    def test_missing_taxonomy_is_visible_and_filterable(self):
        product = self.make_product("بدون کارخانه", self.sheet)
        row = next(row for row in self.client.get("/api/market/products/").data["results"] if row["product_id"] == product.id)
        self.assertEqual(row["subtype"], "__unspecified__")
        self.assertEqual(row["factory_label"], "کارخانه ثبت نشده")
        data = self.client.get("/api/market/products/", {"kind": "sheet", "subtype": "__unspecified__", "factory": "__unspecified__"}).data
        self.assertEqual([item["product_id"] for item in data["results"]], [product.id])

    def test_hierarchy_does_not_truncate_after_thirty_or_one_hundred(self):
        rows = [{"product_id": i, "name": str(i), "product_kind": "sheet", "product_kind_label": "ورق",
                 "subtype": "black", "subtype_label": "ورق سیاه", "factory": "a", "factory_label": "الف",
                 "percent_change": Decimal("2.5") if i % 2 else None, "direction": "up" if i % 2 else "new"} for i in range(135)]
        root = build_market_hierarchy(rows)[0]
        self.assertEqual(root["count"], 135)
        self.assertEqual(len(root["children"][0]["children"][0]["children"]), 135)
        self.assertEqual(root["average_change"], "2.50")

    def test_factory_identifiers_remain_distinct_when_labels_match(self):
        option = ProductAttributeOption.objects.get(group="factory", value="map-b")
        option.label = "کارخانه الف"
        option.save()
        sheet = next(node for node in self.client.get("/api/market/summary/").data["hierarchy"] if node["scope"]["kind"] == "sheet")
        black = next(node for node in sheet["children"] if node["scope"]["subtype"] == "black")
        self.assertEqual({node["scope"]["factory"] for node in black["children"]}, {"map-a", "map-b"})
        self.assertEqual({node["name"] for node in black["children"]}, {"کارخانه الف"})
