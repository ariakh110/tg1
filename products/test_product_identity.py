"""Regression coverage for same-name products with different physical specs."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Product, ProductSpecification, Seller, Offer, PricingTier


class AdminProductIdentityTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("identity-admin", is_staff=True)
        self.client.force_authenticate(user)
        seller_user = get_user_model().objects.create_user("identity-seller")
        self.seller = Seller.objects.create(user=seller_user, company_name="Identity", business_type="Trading", location="Test")
        self.payload = {
            "name": "ÙˆØ±Ù‚ Ø³ÛŒØ§Ù‡ Ú©Ø§ÙˆÛŒØ§Ù† Û³Û° Ù…ÛŒÙ„", "category_code": "sheet",
            "seller_id": self.seller.pk, "price": "50000", "price_basis": "kg",
            "manufacturing_process": "sheet", "surface_finish": "black",
            "factory": "kavian", "steel_grade": "ST37", "cut_type": "cut",
            "thickness_mm": "30", "width_mm": "1500", "length_mm": "6000",
        }

    def save(self, **changes):
        response = self.client.post("/api/products/admin-upsert/", {**self.payload, **changes}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_same_name_different_lengths_keep_both_specs_and_prices(self):
        short = self.save()
        long = self.save(length_mm="7500", price="55000")
        self.assertNotEqual(short["product_id"], long["product_id"])
        self.assertTrue(long["created_product"])
        for result, length, price in [(short, "6000", "50000"), (long, "7500", "55000")]:
            product = Product.objects.get(pk=result["product_id"])
            self.assertEqual(product.specifications.length_mm, Decimal(length))
            self.assertEqual(PricingTier.objects.get(offer__product=product).unit_price, Decimal(price))
        self.assertNotEqual(Product.objects.get(pk=short["product_id"]).slug, Product.objects.get(pk=long["product_id"]).slug)

    def test_matching_dimensions_updates_only_the_matching_variant(self):
        short = self.save()
        long = self.save(length_mm="7500", price="55000")
        updated = self.save(length_mm="7500.00", price="57000")
        self.assertEqual(updated["product_id"], long["product_id"])
        self.assertFalse(updated["created_product"])
        self.assertEqual(Product.objects.filter(name=self.payload["name"]).count(), 2)
        self.assertEqual(PricingTier.objects.get(offer__product_id=short["product_id"]).unit_price, Decimal("50000"))

    def test_name_only_update_is_rejected_when_multiple_products_match(self):
        short = self.save()
        product = Product.objects.create(name=self.payload["name"], category_id=Product.objects.get(pk=short["product_id"]).category_id)
        ProductSpecification.objects.create(product=product, length_mm=7500)
        response = self.client.post("/api/products/admin-upsert/", {
            "name": self.payload["name"], "category_code": "sheet",
            "seller_id": self.seller.pk, "price": "99000",
        }, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(PricingTier.objects.get(offer__product_id=short["product_id"]).unit_price, Decimal("50000"))
        self.assertFalse(Offer.objects.filter(product=product).exists())

    def test_explicit_id_remains_the_edit_target_when_length_changes(self):
        short = self.save()
        updated = self.save(product_id=short["product_id"], length_mm="6500")
        self.assertEqual(updated["product_id"], short["product_id"])
        self.assertEqual(Product.objects.filter(name=self.payload["name"]).count(), 1)
        self.assertEqual(ProductSpecification.objects.get(product_id=short["product_id"]).length_mm, Decimal("6500"))

    def test_variable_and_fixed_lengths_are_distinct_and_variable_is_preserved(self):
        fixed = self.save(length_mm="7000", length_type="fixed")
        variable = self.save(length_mm="7000", length_type="over", price="53000")
        self.assertNotEqual(fixed["product_id"], variable["product_id"])
        product = Product.objects.get(pk=variable["product_id"])
        self.assertEqual(getattr(product.specifications, "length_type", None), "over")
        from sales.services import estimate_sheet_unit_weight_kg
        self.assertIsNone(estimate_sheet_unit_weight_kg(product))

    def test_variable_length_requires_a_positive_threshold(self):
        response = self.client.post("/api/products/admin-upsert/", {**self.payload, "length_type": "over", "length_mm": "0"}, format="json")
        self.assertEqual(response.status_code, 400, response.data)

    def test_bulk_price_import_targets_length_variant_and_rejects_ambiguous_name(self):
        from .admin_import import bulk_upsert_products
        short = self.save()
        variable = self.save(length_mm="7000", length_type="over", price="53000")
        result = bulk_upsert_products([{
            "name": self.payload["name"], "category_code": "sheet", "seller_id": self.seller.pk,
            "length_mm": "7000", "length_type": "over", "price": "56000",
        }], create_missing=False)
        self.assertEqual(result["failed_rows"], 0, result)
        self.assertEqual(result["results"][0]["product_id"], variable["product_id"])
        self.assertEqual(PricingTier.objects.get(offer__product_id=short["product_id"]).unit_price, Decimal("50000"))
        ambiguous = bulk_upsert_products([{"name": self.payload["name"], "price": "99999", "seller_id": self.seller.pk}], create_missing=False)
        self.assertEqual(ambiguous["failed_rows"], 1)
        self.assertEqual(PricingTier.objects.get(offer__product_id=variable["product_id"]).unit_price, Decimal("56000"))

    def test_public_api_retains_variable_length_semantics(self):
        result = self.save(length_mm="7000", length_type="over")
        response = self.client.get(f"/api/products/{result['product_id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["specification"]["length_type"], "over")

    def test_fixed_length_is_default_and_other_dimensions_are_identity(self):
        original = self.save()
        for changes in [{"width_mm": "2000"}, {"thickness_mm": "35"}, {"factory": "mobarakeh"}]:
            with self.subTest(changes=changes):
                variant = self.save(**changes)
                self.assertNotEqual(variant["product_id"], original["product_id"])
        self.assertEqual(ProductSpecification.objects.get(product_id=original["product_id"]).length_type, "fixed")

    def test_variable_length_respects_inherited_category_defaults(self):
        from .models import ProductCategory
        ProductCategory.objects.create(name="Default sheet", code="default-variable-sheet", product_kind="sheet", spec_defaults={"manufacturing_process": "sheet"})
        self.save(category_code="default-variable-sheet", manufacturing_process="", length_type="over", length_mm="7000")
