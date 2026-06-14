from django.contrib.auth import get_user_model
from datetime import timedelta
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import RoleCode, UserRole
from orders.models import OrderRequest
from products.models import (
    DeliveryLocation,
    Offer,
    PricingBasis,
    PricingTier,
    Product,
    ProductCategory,
    ProductSpecification,
    Seller,
)

from .models import (
    StoreDeliveryAssignment,
    StoreDeliveryAssignmentStatus,
    StoreDeliveryDocument,
    StoreDeliveryEvent,
    StoreDeliveryOffer,
    StoreDeliveryOfferStatus,
    StoreDeliveryRequest,
    StoreDeliveryRequestStatus,
    StoreDriverOperationalProfile,
    StoreNotificationStatus,
    StoreOrder,
    StoreOrderLoadingVehicle,
    StoreOrderNotification,
    StoreOrderStatus,
    StoreOrderWeighbridgeSlip,
    StoreQuoteConfirmationStatus,
    StoreRiskStatus,
)

User = get_user_model()


class StoreOrderCheckoutTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username="buyer", password="pass1234")
        self.admin = User.objects.create_user(username="admin", password="pass1234", is_staff=True)
        self.seller_user = User.objects.create_user(username="kaveh_seller", password="pass1234")
        self.seller = Seller.objects.create(
            user=self.seller_user,
            company_name="Kaveh Metal",
            business_type="Platform",
            location="Isfahan",
            is_verified=True,
        )
        self.category = ProductCategory.objects.create(
            name="Checkout Sheet",
            code="checkout-sheet",
            product_kind="sheet",
        )

    def make_product(
        self,
        *,
        price=43000,
        price_basis=PricingBasis.TON,
        condition_label="",
        dimension_width_mm=None,
        dimension_length_mm=None,
        manufacturing_process="sheet",
        thickness_mm="2",
        length_mm="6000",
        is_active=True,
        availability_status=Product.AVAILABILITY_IN_STOCK,
    ):
        product = Product.objects.create(
            category=self.category,
            name="2mm checkout sheet",
            short_description="2mm checkout sheet",
            description="2mm checkout sheet",
            is_active=is_active,
            availability_status=availability_status,
        )
        ProductSpecification.objects.create(
            product=product,
            material_type="sheet",
            steel_grade="ST37",
            surface_finish="black",
            manufacturing_process=manufacturing_process,
            factory="mobarakeh",
            cut_type="cut",
            thickness_mm=thickness_mm,
            width_mm="1250",
            length_mm=length_mm,
        )
        offer = Offer.objects.create(product=product, seller=self.seller, is_active=True)
        tier = None
        if price is not None:
            tier = PricingTier.objects.create(
                offer=offer,
                tier_name="Daily price",
                unit_price=price,
                price_basis=price_basis,
                minimum_quantity=1,
                condition_label=condition_label,
                dimension_width_mm=dimension_width_mm,
                dimension_length_mm=dimension_length_mm,
            )
        DeliveryLocation.objects.create(
            offer=offer,
            incoterm="EXW",
            country="Iran",
            province="Isfahan",
            city="Mobarakeh",
            address="warehouse",
        )
        return product, offer, tier

    def create_order(self, product, quantity="2", buyer=None, quantity_unit="ton", settlement_term_days=None, selection_details=None, items=None, payment_method=None):
        self.client.force_authenticate(buyer or self.buyer)
        payload = {
            "contact_name": "Buyer Co",
            "contact_phone": "09120000000",
            "destination_province": "Tehran",
            "destination_city": "Tehran",
            "destination_address": "Buyer warehouse",
            "items": items
            or [
                {
                    "product_id": product.id,
                    "quantity": quantity,
                    "quantity_unit": quantity_unit,
                    **({"selection_details": selection_details} if selection_details is not None else {}),
                }
            ],
        }
        if settlement_term_days is not None:
            payload["settlement_term_days"] = settlement_term_days
        if payment_method is not None:
            payload["payment_method"] = payment_method
        return self.client.post("/api/v1/store/orders/", payload, format="json")

    def test_priced_product_creates_direct_store_order_not_marketplace_request(self):
        product, _offer, _tier = self.make_product(price=43000)

        res = self.create_order(product, quantity="2")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["status"], StoreOrderStatus.PAYMENT_PENDING)
        self.assertEqual(res.data["payment_status"], "PENDING")
        self.assertEqual(res.data["total_amount"], 86000)
        self.assertEqual(res.data["settlement_term_days"], 1)
        self.assertEqual(res.data["settlement_term_fee_amount"], 0)
        self.assertEqual(res.data["remaining_amount"], 86000)
        self.assertEqual(res.data["risk_status"], StoreRiskStatus.PENDING)
        self.assertFalse(res.data["is_price_expired"])
        self.assertTrue(res.data["price_valid_until"])
        self.assertTrue(res.data["payment_due_at"])
        self.assertIn("/account/payments?", res.data["payment_link_url"])
        self.assertEqual(len(res.data["items"]), 1)
        self.assertEqual(res.data["items"][0]["unit_price_amount"], 43000)
        self.assertEqual(res.data["items"][0]["estimated_weight_kg"], "2000.000")
        self.assertEqual(OrderRequest.all_objects.count(), 0)

    @override_settings(
        OFFLINE_PAYMENT_BANK_ACCOUNTS_JSON=json.dumps(
            [{"id": "IBAN_01", "bank_name": "Test Bank", "iban": "IR000000000000000000000000", "account_holder": "Test"}]
        )
    )
    def test_satna_checkout_creates_offline_payment_without_payment_link(self):
        from offline_payments.models import OfflinePayment

        product, _offer, _tier = self.make_product(price=500_000_000)

        res = self.create_order(product, quantity="3", payment_method="satna_offline")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["payment_method"], "satna_offline")
        self.assertEqual(res.data["payment_link_url"], "")
        payment = OfflinePayment.objects.get(store_order_id=res.data["id"])
        self.assertEqual(payment.amount, 1_500_000_000)

    def test_kilogram_quantity_converts_to_ton_pricing(self):
        product, _offer, _tier = self.make_product(price=43000)

        res = self.create_order(product, quantity="1500", quantity_unit="kg")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["items"][0]["quantity_unit"], "kg")
        self.assertEqual(res.data["items"][0]["estimated_weight_kg"], "1500.000")
        self.assertEqual(res.data["total_amount"], 64500)

    def test_sheet_count_quantity_estimates_weight_from_dimensions(self):
        product, _offer, _tier = self.make_product(price=43000)

        res = self.create_order(product, quantity="10", quantity_unit="sheet")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["items"][0]["quantity_unit"], "sheet")
        self.assertEqual(res.data["items"][0]["estimated_weight_kg"], "1200.000")
        self.assertEqual(res.data["total_amount"], 51600)

    def test_sheet_count_must_be_whole_number(self):
        product, _offer, _tier = self.make_product(price=43000)

        res = self.create_order(product, quantity="1.5", quantity_unit="sheet")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(StoreOrder.objects.count(), 0)

    def test_kilogram_price_basis_uses_weight_without_ton_division(self):
        product, _offer, _tier = self.make_product(price=1400, price_basis=PricingBasis.KG)

        res = self.create_order(product, quantity="1", quantity_unit="ton")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["items"][0]["price_basis"], PricingBasis.KG)
        self.assertEqual(res.data["items"][0]["estimated_weight_kg"], "1000.000")
        self.assertEqual(res.data["total_amount"], 1400000)

    def test_kilogram_price_basis_calculates_high_tonnage_as_kilograms(self):
        product, _offer, _tier = self.make_product(price=140000, price_basis=PricingBasis.KG)

        res = self.create_order(product, quantity="50", quantity_unit="ton")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["items"][0]["estimated_weight_kg"], "50000.000")
        self.assertEqual(res.data["subtotal_amount"], 7000000000)
        self.assertEqual(res.data["total_amount"], 7000000000)

    def test_two_millimeter_coil_uses_standard_twenty_ton_weight(self):
        product, _offer, _tier = self.make_product(
            price=140000,
            price_basis=PricingBasis.KG,
            manufacturing_process="coil",
            thickness_mm="2",
            length_mm=None,
        )

        res = self.create_order(product, quantity="1", quantity_unit="kg")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        item = res.data["items"][0]
        self.assertEqual(item["quantity"], "20.000")
        self.assertEqual(item["quantity_unit"], "ton")
        self.assertEqual(item["estimated_weight_kg"], "20000.000")
        self.assertEqual(item["selection_details"]["roll_weight_ton"], "20")
        self.assertEqual(res.data["subtotal_amount"], 2800000000)

    def test_three_millimeter_and_above_coil_uses_heavier_standard_weight(self):
        product, _offer, _tier = self.make_product(
            price=140000,
            price_basis=PricingBasis.KG,
            manufacturing_process="coil",
            thickness_mm="3",
            length_mm=None,
        )

        res = self.create_order(product, quantity="1", quantity_unit="ton")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        item = res.data["items"][0]
        self.assertEqual(item["quantity"], "22.500")
        self.assertEqual(item["estimated_weight_kg"], "22500.000")
        self.assertEqual(item["selection_details"]["roll_weight_rule"], "gte_3mm")

    def test_coil_uses_configured_weight_kg_per_unit_when_set(self):
        product, _offer, _tier = self.make_product(
            price=140000,
            price_basis=PricingBasis.KG,
            manufacturing_process="coil",
            thickness_mm="3",
            length_mm=None,
        )
        # وزنِ ثابتِ قابل‌تنظیم: «وزن واحد» = ۱۸ تن (۱۸۰۰۰ kg) به‌جای پیش‌فرض ۲۲٫۵ تن
        spec = product.specifications
        spec.weight_kg_per_unit = "18000"
        spec.save(update_fields=["weight_kg_per_unit"])

        res = self.create_order(product, quantity="1", quantity_unit="ton")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        item = res.data["items"][0]
        self.assertEqual(item["quantity"], "18.000")
        self.assertEqual(item["estimated_weight_kg"], "18000.000")
        self.assertEqual(item["selection_details"]["roll_weight_ton"], "18.000")
        self.assertEqual(item["selection_details"]["roll_weight_rule"], "configured")

    def test_cut_sheet_lines_store_each_estimated_weight(self):
        product, _offer, _tier = self.make_product(price=1000, price_basis=PricingBasis.KG)

        res = self.create_order(
            product,
            quantity="1",
            quantity_unit="sheet",
            selection_details={
                "cut_lines": [
                    {"count": 3, "width_m": "1.5", "length_m": "7"},
                    {"count": 10, "width_m": "1.5", "length_m": "4"},
                ]
            },
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        item = res.data["items"][0]
        self.assertEqual(item["quantity"], "13.000")
        self.assertEqual(item["quantity_unit"], "sheet")
        self.assertEqual(item["estimated_weight_kg"], "1464.000")
        self.assertEqual(item["selection_details"]["total_sheet_count"], 13)
        self.assertEqual(item["selection_details"]["cut_lines"][0]["estimated_weight_kg"], "504.000")
        self.assertEqual(item["selection_details"]["cut_lines"][1]["estimated_weight_kg"], "960.000")
        self.assertEqual(res.data["subtotal_amount"], 1464000)

    def test_sheet_price_basis_uses_selected_dimension_and_sheet_count(self):
        product, _offer, tier = self.make_product(
            price=100000,
            price_basis=PricingBasis.SHEET,
            condition_label="1500x3000",
            dimension_width_mm="1500",
            dimension_length_mm="3000",
        )

        self.client.force_authenticate(self.buyer)
        res = self.client.post(
            "/api/v1/store/orders/",
            {
                "contact_name": "Buyer Co",
                "contact_phone": "09120000000",
                "destination_province": "Tehran",
                "destination_city": "Tehran",
                "destination_address": "Buyer warehouse",
                "items": [
                    {
                        "product_id": product.id,
                        "pricing_tier_id": tier.id,
                        "quantity": "10",
                        "quantity_unit": "sheet",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["items"][0]["price_basis"], PricingBasis.SHEET)
        self.assertEqual(res.data["items"][0]["selected_condition_label"], "1500x3000")
        self.assertEqual(res.data["items"][0]["estimated_weight_kg"], "720.000")
        self.assertEqual(res.data["total_amount"], 1000000)

    def test_multi_day_settlement_adds_fee_and_due_date(self):
        product, _offer, _tier = self.make_product(price=43000)

        res = self.create_order(product, quantity="2", settlement_term_days=3)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["settlement_term_days"], 3)
        self.assertEqual(res.data["settlement_term_fee_amount"], 860)
        self.assertEqual(res.data["total_amount"], 86860)

    def test_product_without_price_creates_quote_order(self):
        product, _offer, _tier = self.make_product(price=None)

        res = self.create_order(product, quantity="1")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["status"], StoreOrderStatus.QUOTE_REQUESTED)
        self.assertEqual(res.data["payment_status"], "UNPAID")
        self.assertEqual(res.data["quote_confirmation_status"], StoreQuoteConfirmationStatus.AWAITING_ADMIN_QUOTE)
        self.assertIsNone(res.data["items"][0]["unit_price_amount"])
        self.assertEqual(res.data["total_amount"], 0)

    def test_mixed_quote_order_requires_admin_quote_and_buyer_confirmation_before_payment_link(self):
        priced_product, _offer, _tier = self.make_product(price=1000, price_basis=PricingBasis.KG)
        quote_product, _quote_offer, _quote_tier = self.make_product(price=None)

        res = self.create_order(
            priced_product,
            settlement_term_days=3,
            items=[
                {"product_id": priced_product.id, "quantity": "1", "quantity_unit": "ton"},
                {"product_id": quote_product.id, "quantity": "1", "quantity_unit": "ton"},
            ],
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["status"], StoreOrderStatus.QUOTE_REQUESTED)
        self.assertEqual(res.data["quote_confirmation_status"], StoreQuoteConfirmationStatus.AWAITING_ADMIN_QUOTE)
        self.assertEqual(res.data["subtotal_amount"], 1000000)
        self.assertEqual(res.data["settlement_term_fee_amount"], 0)
        self.assertEqual(res.data["payment_link_url"], "")
        quote_item = next(item for item in res.data["items"] if item["unit_price_amount"] is None)

        self.client.force_authenticate(self.admin)
        quote_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/quote/",
            {
                "items": [
                    {
                        "item_id": quote_item["id"],
                        "unit_price_amount": 2000,
                        "price_basis": PricingBasis.KG,
                    }
                ]
            },
            format="json",
        )

        self.assertEqual(quote_res.status_code, status.HTTP_200_OK, quote_res.data)
        self.assertEqual(quote_res.data["status"], StoreOrderStatus.PRICE_CONFIRMED)
        self.assertEqual(quote_res.data["quote_confirmation_status"], StoreQuoteConfirmationStatus.AWAITING_BUYER)
        self.assertEqual(quote_res.data["subtotal_amount"], 3000000)
        self.assertEqual(quote_res.data["settlement_term_fee_amount"], 30000)
        self.assertEqual(quote_res.data["total_amount"], 3030000)
        self.assertEqual(quote_res.data["payment_link_url"], "")

        link_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/payment-link/",
            {},
            format="json",
        )
        self.assertEqual(link_res.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(self.buyer)
        confirm_res = self.client.post(f"/api/v1/store/orders/{res.data['id']}/confirm-quote/", {}, format="json")

        self.assertEqual(confirm_res.status_code, status.HTTP_200_OK, confirm_res.data)
        self.assertEqual(confirm_res.data["status"], StoreOrderStatus.PAYMENT_PENDING)
        self.assertEqual(confirm_res.data["payment_status"], "PENDING")
        self.assertEqual(confirm_res.data["quote_confirmation_status"], StoreQuoteConfirmationStatus.CONFIRMED)
        self.assertIn("/account/payments?", confirm_res.data["payment_link_url"])

    def test_admin_quote_refreshes_deadlines_and_includes_loading_freight(self):
        quote_product, _quote_offer, _quote_tier = self.make_product(price=None)
        res = self.create_order(quote_product, quantity="2", quantity_unit="ton", settlement_term_days=2)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        order = StoreOrder.objects.get(pk=res.data["id"])
        StoreOrder.objects.filter(pk=order.pk).update(
            price_valid_until=timezone.now() - timedelta(hours=1),
            payment_due_at=timezone.now() - timedelta(hours=1),
        )
        quote_item = res.data["items"][0]

        self.client.force_authenticate(self.admin)
        quote_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{order.pk}/quote/",
            {
                "items": [
                    {
                        "item_id": quote_item["id"],
                        "unit_price_amount": 1000,
                        "price_basis": PricingBasis.KG,
                    }
                ],
                "multi_loading": True,
                "freight_amount": 500000,
                "freight_note": "Two loading points.",
                "loading_points": [
                    {
                        "item_id": quote_item["id"],
                        "province": "Tehran",
                        "city": "Rey",
                        "place_type": "warehouse",
                        "address": "Main warehouse",
                        "freight_amount": 500000,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(quote_res.status_code, status.HTTP_200_OK, quote_res.data)
        self.assertEqual(quote_res.data["subtotal_amount"], 2000000)
        self.assertEqual(quote_res.data["settlement_term_fee_amount"], 10000)
        self.assertEqual(quote_res.data["total_amount"], 2510000)
        self.assertEqual(quote_res.data["metadata"]["quote"]["freight_amount"], 500000)
        self.assertTrue(quote_res.data["metadata"]["quote"]["multi_loading"])
        self.assertEqual(quote_res.data["items"][0]["delivery_snapshot"]["city"], "Rey")
        self.assertEqual(quote_res.data["items"][0]["delivery_snapshot"]["place_type"], "warehouse")
        order.refresh_from_db()
        self.assertGreater(order.price_valid_until, timezone.now())
        self.assertGreater(order.payment_due_at, timezone.now())

        StoreOrder.objects.filter(pk=order.pk).update(price_valid_until=timezone.now() - timedelta(minutes=1))
        self.client.force_authenticate(self.buyer)
        confirm_res = self.client.post(f"/api/v1/store/orders/{order.pk}/confirm-quote/", {}, format="json")

        self.assertEqual(confirm_res.status_code, status.HTTP_200_OK, confirm_res.data)
        self.assertEqual(confirm_res.data["quote_confirmation_status"], StoreQuoteConfirmationStatus.CONFIRMED)
        self.assertIn("/account/payments?", confirm_res.data["payment_link_url"])
        order.refresh_from_db()
        self.assertGreater(order.price_valid_until, timezone.now())

    def test_buyer_must_provide_reason_when_rejecting_quote(self):
        quote_product, _quote_offer, _quote_tier = self.make_product(price=None)
        res = self.create_order(quote_product, quantity="1")
        quote_item = res.data["items"][0]
        self.client.force_authenticate(self.admin)
        quote_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/quote/",
            {"items": [{"item_id": quote_item["id"], "unit_price_amount": 2000, "price_basis": PricingBasis.KG}]},
            format="json",
        )
        self.assertEqual(quote_res.status_code, status.HTTP_200_OK, quote_res.data)

        self.client.force_authenticate(self.buyer)
        empty_reject = self.client.post(f"/api/v1/store/orders/{res.data['id']}/reject-quote/", {}, format="json")
        reject_res = self.client.post(
            f"/api/v1/store/orders/{res.data['id']}/reject-quote/",
            {"reason": "price_too_high", "note": "Need a lower price."},
            format="json",
        )

        self.assertEqual(empty_reject.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(reject_res.status_code, status.HTTP_200_OK, reject_res.data)
        self.assertEqual(reject_res.data["quote_confirmation_status"], StoreQuoteConfirmationStatus.REJECTED)
        self.assertEqual(reject_res.data["quote_rejection_reason"], "price_too_high")
        self.assertEqual(reject_res.data["status"], StoreOrderStatus.QUOTE_REQUESTED)

    def test_out_of_stock_product_creates_quote_order(self):
        product, _offer, _tier = self.make_product(
            price=43000,
            availability_status=Product.AVAILABILITY_OUT_OF_STOCK,
        )

        res = self.create_order(product, quantity="1")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["status"], StoreOrderStatus.QUOTE_REQUESTED)
        self.assertIsNone(res.data["items"][0]["unit_price_amount"])

    def test_inactive_product_is_rejected(self):
        product, _offer, _tier = self.make_product(price=43000, is_active=False)

        res = self.create_order(product, quantity="1")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(StoreOrder.objects.count(), 0)

    def test_order_item_snapshot_does_not_change_after_catalog_edit(self):
        product, _offer, tier = self.make_product(price=43000)

        res = self.create_order(product, quantity="1")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        order = StoreOrder.objects.get(pk=res.data["id"])
        item = order.items.get()
        product.name = "changed title"
        product.save(update_fields=["name"])
        tier.unit_price = 50000
        tier.save(update_fields=["unit_price"])
        item.refresh_from_db()

        self.assertEqual(item.product_name, "2mm checkout sheet")
        self.assertEqual(item.product_snapshot["name"], "2mm checkout sheet")
        self.assertEqual(item.unit_price_amount, 43000)
        self.assertEqual(item.delivery_snapshot["city"], "Mobarakeh")

    def test_admin_can_list_direct_store_orders(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="1")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        self.client.force_authenticate(self.admin)
        admin_res = self.client.get("/api/v1/admin/dashboard/store-orders/")

        self.assertEqual(admin_res.status_code, status.HTTP_200_OK)
        rows = admin_res.data.get("results", admin_res.data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], res.data["id"])

    def test_admin_can_confirm_manual_payment(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="1")
        self.client.force_authenticate(self.admin)

        payment_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/confirm-payment/",
            {"provider": "manual", "provider_reference": "receipt-1"},
            format="json",
        )

        self.assertEqual(payment_res.status_code, status.HTTP_201_CREATED, payment_res.data)
        order = StoreOrder.objects.get(pk=res.data["id"])
        self.assertEqual(order.payment_status, "PAID")
        self.assertEqual(order.status, StoreOrderStatus.PAID)
        self.assertTrue(order.status_history.filter(event="STORE_ORDER_PAYMENT_CONFIRMED").exists())

    def test_admin_final_weight_reopens_paid_order_for_remaining_settlement(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="1")
        item_id = res.data["items"][0]["id"]
        self.client.force_authenticate(self.admin)
        payment_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/confirm-payment/",
            {"provider": "manual", "provider_reference": "receipt-final-weight"},
            format="json",
        )
        self.assertEqual(payment_res.status_code, status.HTTP_201_CREATED, payment_res.data)

        final_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/final-weight/",
            {"items": [{"item_id": item_id, "final_weight_kg": "1200"}]},
            format="json",
        )

        self.assertEqual(final_res.status_code, status.HTTP_200_OK, final_res.data)
        self.assertEqual(final_res.data["weight_adjustment_amount"], 8600)
        self.assertEqual(final_res.data["total_amount"], 51600)
        self.assertEqual(final_res.data["paid_amount"], 43000)
        self.assertEqual(final_res.data["remaining_amount"], 8600)
        self.assertEqual(final_res.data["payment_status"], "PENDING")
        self.assertEqual(final_res.data["items"][0]["final_weight_kg"], "1200.000")
        self.assertTrue(StoreOrder.objects.get(pk=res.data["id"]).status_history.filter(event="STORE_ORDER_FINAL_WEIGHT_RECORDED").exists())

    def test_user_dashboard_summary_and_pending_payments_are_scoped_to_buyer(self):
        product, _offer, _tier = self.make_product(price=43000)
        other_buyer = User.objects.create_user(username="other-buyer", password="pass1234")
        own_res = self.create_order(product, quantity="1", buyer=self.buyer)
        other_res = self.create_order(product, quantity="1", buyer=other_buyer)
        self.assertEqual(own_res.status_code, status.HTTP_201_CREATED, own_res.data)
        self.assertEqual(other_res.status_code, status.HTTP_201_CREATED, other_res.data)

        self.client.force_authenticate(self.buyer)
        summary_res = self.client.get("/api/v1/store/dashboard/summary/")
        pending_res = self.client.get("/api/v1/store/pending-payments/")

        self.assertEqual(summary_res.status_code, status.HTTP_200_OK)
        self.assertEqual(summary_res.data["total_orders"], 1)
        self.assertEqual(summary_res.data["pending_payment_orders"], 1)
        self.assertEqual(pending_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(pending_res.data), 1)
        self.assertEqual(pending_res.data[0]["id"], own_res.data["id"])

    def test_pending_payment_marks_overdue_orders(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="1", buyer=self.buyer)
        StoreOrder.objects.filter(pk=res.data["id"]).update(payment_due_at=timezone.now() - timedelta(hours=1))

        self.client.force_authenticate(self.buyer)
        summary_res = self.client.get("/api/v1/store/dashboard/summary/")
        pending_res = self.client.get("/api/v1/store/pending-payments/")

        self.assertEqual(summary_res.status_code, status.HTTP_200_OK)
        self.assertEqual(summary_res.data["overdue_payment_orders"], 1)
        self.assertEqual(summary_res.data["notification_count"], 1)
        self.assertEqual(summary_res.data["notifications"][0]["type"], "payment_overdue")
        self.assertEqual(pending_res.status_code, status.HTTP_200_OK)
        self.assertTrue(pending_res.data[0]["is_payment_overdue"])

    def test_user_payment_list_returns_confirmed_payments_for_own_orders(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="1")
        self.client.force_authenticate(self.admin)
        payment_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/confirm-payment/",
            {"provider": "manual", "provider_reference": "receipt-payment-list"},
            format="json",
        )
        self.assertEqual(payment_res.status_code, status.HTTP_201_CREATED, payment_res.data)

        self.client.force_authenticate(self.buyer)
        list_res = self.client.get("/api/v1/store/payments/")

        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.data), 1)
        self.assertEqual(list_res.data[0]["order"], res.data["id"])
        self.assertEqual(list_res.data[0]["status"], "PAID")

    def test_admin_can_update_store_order_payment_deadline_and_destination(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="1")
        due_at = (timezone.now() + timedelta(hours=6)).isoformat()
        price_valid_until = (timezone.now() + timedelta(hours=2)).isoformat()
        self.client.force_authenticate(self.admin)

        update_res = self.client.patch(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/",
            {
                "destination_province": "Tehran",
                "destination_city": "Tehran",
                "payment_due_at": due_at,
                "price_valid_until": price_valid_until,
                "risk_status": StoreRiskStatus.APPROVED,
                "source_price_checked": True,
                "market_price_checked": True,
                "stock_verified": True,
                "proforma_confirmed": True,
                "admin_notes": "Call before shipping",
            },
            format="json",
        )

        self.assertEqual(update_res.status_code, status.HTTP_200_OK, update_res.data)
        self.assertEqual(update_res.data["destination_province"], "Tehran")
        self.assertEqual(update_res.data["destination_city"], "Tehran")
        self.assertEqual(update_res.data["risk_status"], StoreRiskStatus.APPROVED)
        self.assertTrue(update_res.data["source_price_checked_at"])
        self.assertTrue(update_res.data["market_price_checked_at"])
        self.assertTrue(update_res.data["stock_verified_at"])
        self.assertTrue(update_res.data["proforma_confirmed_at"])
        self.assertEqual(update_res.data["admin_notes"], "Call before shipping")
        self.assertTrue(StoreOrder.objects.get(pk=res.data["id"]).status_history.filter(event="STORE_ORDER_ADMIN_UPDATED").exists())

    def test_expired_price_blocks_manual_payment_confirmation(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="1")
        StoreOrder.objects.filter(pk=res.data["id"]).update(price_valid_until=timezone.now() - timedelta(minutes=1))
        self.client.force_authenticate(self.admin)

        payment_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/confirm-payment/",
            {"provider": "manual", "provider_reference": "late-receipt"},
            format="json",
        )

        self.assertEqual(payment_res.status_code, status.HTTP_400_BAD_REQUEST)
        order = StoreOrder.objects.get(pk=res.data["id"])
        self.assertEqual(order.payment_status, "PENDING")

    def test_release_transition_requires_payment_and_risk_checks(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="1")
        self.client.force_authenticate(self.admin)

        blocked_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/transition/",
            {"status": StoreOrderStatus.READY_FOR_PICKUP},
            format="json",
        )

        self.assertEqual(blocked_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("payment_not_confirmed", str(blocked_res.data))

    def test_paid_and_checked_order_can_enter_fulfillment(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="1")
        self.client.force_authenticate(self.admin)
        payment_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/confirm-payment/",
            {"provider": "manual", "provider_reference": "receipt-risk-clear"},
            format="json",
        )
        self.assertEqual(payment_res.status_code, status.HTTP_201_CREATED, payment_res.data)
        update_res = self.client.patch(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/",
            {
                "risk_status": StoreRiskStatus.APPROVED,
                "stock_verified": True,
                "proforma_confirmed": True,
                "loading_permission": True,
            },
            format="json",
        )
        self.assertEqual(update_res.status_code, status.HTTP_200_OK, update_res.data)

        transition_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/transition/",
            {"status": StoreOrderStatus.FULFILLMENT_PENDING},
            format="json",
        )

        self.assertEqual(transition_res.status_code, status.HTTP_200_OK, transition_res.data)
        self.assertEqual(transition_res.data["status"], StoreOrderStatus.FULFILLMENT_PENDING)

    def test_admin_can_generate_payment_link_and_send_attempt_is_logged(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="1")
        self.client.force_authenticate(self.admin)

        link_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/payment-link/",
            {},
            format="json",
        )
        send_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/send-payment-link/",
            {"recipient": "09121111111"},
            format="json",
        )

        self.assertEqual(link_res.status_code, status.HTTP_200_OK, link_res.data)
        self.assertIn("/account/payments?", link_res.data["payment_link_url"])
        self.assertEqual(send_res.status_code, status.HTTP_201_CREATED, send_res.data)
        self.assertEqual(send_res.data["status"], StoreNotificationStatus.SKIPPED)
        notification = StoreOrderNotification.objects.get(pk=send_res.data["id"])
        self.assertEqual(notification.recipient, "09121111111")
        self.assertEqual(notification.error_message, "sms_provider_not_configured")

    def create_driver(self, username):
        driver = User.objects.create_user(username=username, password="pass1234")
        UserRole.objects.create(user=driver, role=RoleCode.DRIVER, is_active=True, activated_at=timezone.now())
        return driver

    def create_carrier(self, username):
        carrier = User.objects.create_user(username=username, password="pass1234")
        UserRole.objects.create(user=carrier, role=RoleCode.CARRIER, is_active=True, activated_at=timezone.now())
        return carrier

    def create_driver_profile(
        self,
        driver,
        *,
        is_verified=True,
        is_available=True,
        province="Isfahan",
        city="Isfahan",
        latitude="32.654600",
        longitude="51.668000",
        service_radius_km=200,
        capacity_kg="25000.000",
        vehicle_type="trailer",
        vehicle_plate="IR-TEST",
    ):
        return StoreDriverOperationalProfile.objects.create(
            user=driver,
            is_verified=is_verified,
            is_available=is_available,
            current_province=province,
            current_city=city,
            current_latitude=latitude,
            current_longitude=longitude,
            service_radius_km=service_radius_km,
            capacity_kg=capacity_kg,
            vehicle_type=vehicle_type,
            vehicle_plate=vehicle_plate,
        )

    def prepare_fulfillment_order(self, quantity="50", provider_reference="driver-load-payment"):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity=quantity)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.client.force_authenticate(self.admin)
        payment_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/confirm-payment/",
            {"provider": "manual", "provider_reference": provider_reference},
            format="json",
        )
        self.assertEqual(payment_res.status_code, status.HTTP_201_CREATED, payment_res.data)
        update_res = self.client.patch(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/",
            {
                "risk_status": StoreRiskStatus.APPROVED,
                "stock_verified": True,
                "proforma_confirmed": True,
                "loading_permission": True,
            },
            format="json",
        )
        self.assertEqual(update_res.status_code, status.HTTP_200_OK, update_res.data)
        return StoreOrder.objects.prefetch_related("items").get(pk=res.data["id"])

    def test_admin_delivery_request_allows_priced_unpaid_order_before_release(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="50")
        drivers = [self.create_driver("driver-unpaid-1"), self.create_driver("driver-unpaid-2")]
        self.client.force_authenticate(self.admin)

        create_res = self.client.post(
            "/api/v1/admin/dashboard/delivery-requests/",
            {"order_id": res.data["id"], "driver_ids": [driver.id for driver in drivers], "vehicle_type": "trailer"},
            format="json",
        )

        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED, create_res.data)
        self.assertEqual(create_res.data["required_driver_count"], 2)
        self.assertEqual(StoreDeliveryRequest.objects.count(), 1)
        order = StoreOrder.objects.get(pk=res.data["id"])
        self.assertEqual(order.status, StoreOrderStatus.FULFILLMENT_PENDING)

        transition_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{order.id}/transition/",
            {"status": StoreOrderStatus.READY_FOR_PICKUP},
            format="json",
        )
        self.assertEqual(transition_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("order_transition_blockers", str(transition_res.data["detail"]))
        self.assertIn("payment_not_confirmed", transition_res.data["blockers"])
        self.assertIn("final_weight_not_recorded", transition_res.data["blockers"])

    def test_admin_delivery_request_stores_pickup_and_destination_coordinates(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="25")
        driver = self.create_driver("geo-driver")
        self.client.force_authenticate(self.admin)

        create_res = self.client.post(
            "/api/v1/admin/dashboard/delivery-requests/",
            {
                "order_id": res.data["id"],
                "driver_ids": [driver.id],
                "pickup_province": "Isfahan",
                "pickup_city": "Mobarakeh",
                "pickup_address": "Loading gate 2",
                "pickup_latitude": "32.340000",
                "pickup_longitude": "51.500000",
                "destination_province": "Tehran",
                "destination_city": "Tehran",
                "destination_address": "Buyer warehouse",
                "destination_latitude": "35.700000",
                "destination_longitude": "51.400000",
            },
            format="json",
        )

        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED, create_res.data)
        self.assertEqual(create_res.data["pickup_address"], "Loading gate 2")
        self.assertEqual(create_res.data["destination_address"], "Buyer warehouse")
        self.assertEqual(create_res.data["destination_latitude"], "35.700000")
        order = StoreOrder.objects.get(pk=res.data["id"])
        self.assertEqual(str(order.destination_latitude), "35.700000")
        self.assertEqual(str(order.destination_longitude), "51.400000")

    def test_admin_can_publish_offer_to_driver_and_carrier_recipients(self):
        order = self.prepare_fulfillment_order(quantity="50", provider_reference="driver-carrier-load-payment")
        driver = self.create_driver("mixed-driver")
        carrier = self.create_carrier("mixed-carrier")
        self.client.force_authenticate(self.admin)

        create_res = self.client.post(
            "/api/v1/admin/dashboard/delivery-requests/",
            {
                "order_id": str(order.id),
                "recipient_type": "ALL",
                "recipient_ids": [driver.id, carrier.id],
                "vehicle_type": "trailer",
            },
            format="json",
        )

        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED, create_res.data)
        self.assertEqual(create_res.data["required_driver_count"], 2)
        self.assertEqual(set(StoreDeliveryOffer.objects.values_list("recipient_type", flat=True)), {"DRIVER", "CARRIER"})

        offer = StoreDeliveryOffer.objects.get(driver=carrier)
        self.client.force_authenticate(carrier)
        accept_res = self.client.post(
            f"/api/v1/store/driver/load-offers/{offer.id}/respond/",
            {"action": "accept"},
            format="json",
        )
        self.assertEqual(accept_res.status_code, status.HTTP_201_CREATED, accept_res.data)
        self.assertEqual(accept_res.data["recipient_type"], "CARRIER")

    def test_admin_publishes_high_tonnage_offer_to_multiple_active_drivers(self):
        order = self.prepare_fulfillment_order(quantity="50", provider_reference="driver-load-payment-50")
        drivers = [self.create_driver(f"driver-{index}") for index in range(1, 4)]
        self.client.force_authenticate(self.admin)

        create_res = self.client.post(
            "/api/v1/admin/dashboard/delivery-requests/",
            {
                "order_id": str(order.id),
                "driver_ids": [driver.id for driver in drivers],
                "vehicle_type": "flatbed trailer",
                "pickup_notes": "loading from isfahan warehouse",
                "dispatcher_notes": "call before arrival",
            },
            format="json",
        )

        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED, create_res.data)
        self.assertEqual(create_res.data["total_weight_kg"], "50000.000")
        self.assertEqual(create_res.data["required_driver_count"], 2)
        self.assertEqual(create_res.data["accepted_driver_count"], 0)
        self.assertEqual(len(create_res.data["offers"]), 3)
        self.assertEqual(create_res.data["shipment_snapshot"]["required_driver_count"], 2)
        self.assertEqual(create_res.data["shipment_snapshot"]["items"][0]["planned_weight_kg"], "50000.000")

        self.client.force_authenticate(drivers[0])
        offer_res = self.client.get("/api/v1/store/driver/load-offers/")
        self.assertEqual(offer_res.status_code, status.HTTP_200_OK, offer_res.data)
        self.assertEqual(len(offer_res.data), 1)
        self.assertEqual(offer_res.data[0]["total_weight_kg"], "50000.000")
        self.assertEqual(offer_res.data[0]["required_driver_count"], 2)
        self.assertEqual(offer_res.data[0]["pickup_notes"], "loading from isfahan warehouse")

    def test_driver_acceptance_caps_each_assignment_at_twenty_five_tons(self):
        order = self.prepare_fulfillment_order(quantity="50", provider_reference="driver-load-payment-cap")
        drivers = [self.create_driver(f"cap-driver-{index}") for index in range(1, 4)]
        self.client.force_authenticate(self.admin)
        create_res = self.client.post(
            "/api/v1/admin/dashboard/delivery-requests/",
            {"order_id": str(order.id), "driver_ids": [driver.id for driver in drivers]},
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED, create_res.data)
        offers = list(StoreDeliveryOffer.objects.order_by("created_at"))

        self.client.force_authenticate(drivers[0])
        accept_one = self.client.post(
            f"/api/v1/store/driver/load-offers/{offers[0].id}/respond/",
            {"action": "accept"},
            format="json",
        )
        self.assertEqual(accept_one.status_code, status.HTTP_201_CREATED, accept_one.data)
        self.assertEqual(accept_one.data["planned_weight_kg"], "25000.000")

        self.client.force_authenticate(drivers[1])
        accept_two = self.client.post(
            f"/api/v1/store/driver/load-offers/{offers[1].id}/respond/",
            {"action": "accept"},
            format="json",
        )
        self.assertEqual(accept_two.status_code, status.HTTP_201_CREATED, accept_two.data)
        self.assertEqual(accept_two.data["planned_weight_kg"], "25000.000")

        request_obj = StoreDeliveryRequest.objects.get(order=order)
        self.assertEqual(request_obj.status, StoreDeliveryRequestStatus.ASSIGNED)
        self.assertEqual(request_obj.accepted_driver_count, 2)
        self.assertEqual(StoreDeliveryAssignment.objects.count(), 2)
        self.assertTrue(all(row.planned_weight_kg <= 25000 for row in StoreDeliveryAssignment.objects.all()))

        self.client.force_authenticate(drivers[2])
        accept_three = self.client.post(
            f"/api/v1/store/driver/load-offers/{offers[2].id}/respond/",
            {"action": "accept"},
            format="json",
        )
        self.assertEqual(accept_three.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery_capacity_full", str(accept_three.data))

    def test_driver_cannot_respond_to_other_driver_offer(self):
        order = self.prepare_fulfillment_order(quantity="25", provider_reference="driver-load-access")
        owner = self.create_driver("offer-owner")
        other = self.create_driver("offer-other")
        self.client.force_authenticate(self.admin)
        create_res = self.client.post(
            "/api/v1/admin/dashboard/delivery-requests/",
            {"order_id": str(order.id), "driver_ids": [owner.id]},
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED, create_res.data)
        offer = StoreDeliveryOffer.objects.get()

        self.client.force_authenticate(other)
        response = self.client.post(
            f"/api/v1/store/driver/load-offers/{offer.id}/respond/",
            {"action": "accept"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(StoreDeliveryAssignment.objects.count(), 0)

    @override_settings(DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage")
    def test_driver_assignment_transition_and_document_upload(self):
        order = self.prepare_fulfillment_order(quantity="25", provider_reference="driver-load-doc")
        driver = self.create_driver("doc-driver")
        self.client.force_authenticate(self.admin)
        create_res = self.client.post(
            "/api/v1/admin/dashboard/delivery-requests/",
            {"order_id": str(order.id), "driver_ids": [driver.id]},
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED, create_res.data)
        offer = StoreDeliveryOffer.objects.get(driver=driver)

        self.client.force_authenticate(driver)
        accept_res = self.client.post(
            f"/api/v1/store/driver/load-offers/{offer.id}/respond/",
            {"action": "accept"},
            format="json",
        )
        self.assertEqual(accept_res.status_code, status.HTTP_201_CREATED, accept_res.data)
        assignment_id = accept_res.data["id"]
        transition_res = self.client.post(
            f"/api/v1/store/driver/assignments/{assignment_id}/transition/",
            {"status": StoreDeliveryAssignmentStatus.ARRIVED_FOR_LOADING, "note": "arrived"},
            format="json",
        )
        self.assertEqual(transition_res.status_code, status.HTTP_200_OK, transition_res.data)
        self.assertEqual(transition_res.data["status"], StoreDeliveryAssignmentStatus.ARRIVED_FOR_LOADING)

        upload = SimpleUploadedFile("proof.pdf", b"%PDF-1.4\nproof\n", content_type="application/pdf")
        upload_res = self.client.post(
            f"/api/v1/store/driver/assignments/{assignment_id}/documents/",
            {"document_type": "delivery_receipt", "file": upload, "note": "signed"},
            format="multipart",
        )

        self.assertEqual(upload_res.status_code, status.HTTP_201_CREATED, upload_res.data)
        self.assertEqual(upload_res.data["document_type"], "delivery_receipt")
        self.assertEqual(StoreDeliveryDocument.objects.count(), 1)
        self.assertTrue(StoreDeliveryEvent.objects.filter(event="DELIVERY_DOCUMENT_UPLOADED").exists())

    def test_driver_can_update_profile_and_admin_can_verify_it(self):
        driver = self.create_driver("profile-driver")

        self.client.force_authenticate(driver)
        update_res = self.client.patch(
            "/api/v1/store/driver/profile/",
            {
                "is_available": True,
                "is_verified": True,
                "current_province": "Isfahan",
                "current_city": "Mobarakeh",
                "current_latitude": "32.340000",
                "current_longitude": "51.500000",
                "vehicle_type": "trailer",
                "vehicle_plate": "11-A-222",
                "service_radius_km": 120,
            },
            format="json",
        )
        self.assertEqual(update_res.status_code, status.HTTP_200_OK, update_res.data)
        self.assertTrue(update_res.data["is_available"])
        self.assertFalse(update_res.data["is_verified"])
        self.assertTrue(update_res.data["last_location_at"])

        self.client.force_authenticate(self.admin)
        verify_res = self.client.patch(
            f"/api/v1/admin/dashboard/driver-profiles/{driver.id}/",
            {"is_verified": True},
            format="json",
        )
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK, verify_res.data)
        self.assertTrue(verify_res.data["is_verified"])
        self.assertTrue(verify_res.data["verified_at"])

    def test_geo_match_preview_returns_nearest_verified_available_drivers(self):
        order = self.prepare_fulfillment_order(quantity="25", provider_reference="driver-geo-preview")
        near = self.create_driver("geo-near")
        far = self.create_driver("geo-far")
        unverified = self.create_driver("geo-unverified")
        self.create_driver_profile(near, latitude="32.330000", longitude="51.500000", city="Mobarakeh")
        self.create_driver_profile(far, latitude="32.800000", longitude="51.900000", city="Isfahan")
        self.create_driver_profile(unverified, is_verified=False, latitude="32.331000", longitude="51.501000", city="Mobarakeh")

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/v1/admin/dashboard/delivery-requests/match-drivers/",
            {
                "order_id": str(order.id),
                "pickup_latitude": "32.340000",
                "pickup_longitude": "51.510000",
                "search_radius_km": 200,
                "limit": 5,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual([row["username"] for row in response.data], ["geo-near", "geo-far"])
        self.assertLess(float(response.data[0]["distance_km"]), float(response.data[1]["distance_km"]))

    def test_auto_publish_uses_nearest_verified_drivers_and_notifies_with_expiry(self):
        order = self.prepare_fulfillment_order(quantity="50", provider_reference="driver-geo-publish")
        near = self.create_driver("publish-near")
        second = self.create_driver("publish-second")
        far = self.create_driver("publish-far")
        self.create_driver_profile(near, latitude="32.330000", longitude="51.500000", city="Mobarakeh")
        self.create_driver_profile(second, latitude="32.360000", longitude="51.540000", city="Mobarakeh")
        self.create_driver_profile(far, latitude="35.700000", longitude="51.400000", city="Tehran", service_radius_km=50)

        self.client.force_authenticate(self.admin)
        create_res = self.client.post(
            "/api/v1/admin/dashboard/delivery-requests/",
            {
                "order_id": str(order.id),
                "pickup_province": "Isfahan",
                "pickup_city": "Mobarakeh",
                "pickup_latitude": "32.340000",
                "pickup_longitude": "51.510000",
                "search_radius_km": 120,
                "offer_ttl_minutes": 15,
                "max_candidate_count": 2,
            },
            format="json",
        )

        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED, create_res.data)
        self.assertEqual(create_res.data["required_driver_count"], 2)
        self.assertEqual(create_res.data["pickup_city"], "Mobarakeh")
        self.assertEqual(len(create_res.data["offers"]), 2)
        ranked_offers = sorted(create_res.data["offers"], key=lambda row: row["match_rank"])
        self.assertEqual([offer["driver_username"] for offer in ranked_offers], ["publish-near", "publish-second"])
        self.assertTrue(all(offer["expires_at"] for offer in create_res.data["offers"]))
        self.assertEqual(
            StoreOrderNotification.objects.filter(order=order, event="DELIVERY_LOAD_OFFERED", status=StoreNotificationStatus.SENT).count(),
            2,
        )

    def test_expired_offer_reassigns_to_next_nearby_driver(self):
        from .tasks import expire_delivery_offers

        order = self.prepare_fulfillment_order(quantity="25", provider_reference="driver-geo-expire")
        first = self.create_driver("expire-first")
        second = self.create_driver("expire-second")
        self.create_driver_profile(first, latitude="32.330000", longitude="51.500000", city="Mobarakeh")
        self.create_driver_profile(second, latitude="32.350000", longitude="51.530000", city="Mobarakeh")
        self.client.force_authenticate(self.admin)
        create_res = self.client.post(
            "/api/v1/admin/dashboard/delivery-requests/",
            {
                "order_id": str(order.id),
                "pickup_latitude": "32.340000",
                "pickup_longitude": "51.510000",
                "search_radius_km": 120,
                "offer_ttl_minutes": 1,
                "max_candidate_count": 1,
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED, create_res.data)
        offer = StoreDeliveryOffer.objects.get(driver=first)
        offer.expires_at = timezone.now() - timedelta(minutes=1)
        offer.save(update_fields=["expires_at"])

        result = expire_delivery_offers()

        self.assertEqual(result, {"expired": 1})
        offer.refresh_from_db()
        self.assertEqual(offer.status, StoreDeliveryOfferStatus.EXPIRED)
        self.assertTrue(StoreDeliveryOffer.objects.filter(driver=second, status=StoreDeliveryOfferStatus.OFFERED).exists())
        self.assertTrue(StoreDeliveryEvent.objects.filter(event="DELIVERY_REQUEST_REASSIGNED").exists())

    def test_driver_cannot_accept_expired_offer(self):
        order = self.prepare_fulfillment_order(quantity="25", provider_reference="driver-geo-expired-accept")
        driver = self.create_driver("expired-accept-driver")
        self.create_driver_profile(driver, latitude="32.330000", longitude="51.500000", city="Mobarakeh")
        self.client.force_authenticate(self.admin)
        create_res = self.client.post(
            "/api/v1/admin/dashboard/delivery-requests/",
            {
                "order_id": str(order.id),
                "pickup_latitude": "32.340000",
                "pickup_longitude": "51.510000",
                "search_radius_km": 120,
                "max_candidate_count": 1,
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED, create_res.data)
        offer = StoreDeliveryOffer.objects.get(driver=driver)
        offer.expires_at = timezone.now() - timedelta(minutes=1)
        offer.save(update_fields=["expires_at"])

        self.client.force_authenticate(driver)
        accept_res = self.client.post(
            f"/api/v1/store/driver/load-offers/{offer.id}/respond/",
            {"action": "accept"},
            format="json",
        )

        self.assertEqual(accept_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("offer_expired", str(accept_res.data))
        offer.refresh_from_db()
        self.assertEqual(offer.status, StoreDeliveryOfferStatus.EXPIRED)


@override_settings(MEDIA_ROOT="/tmp/test_media_loading_vehicles")
class LoadingVehicleWeighbridgeTests(APITestCase):
    """Tests for multi-vehicle loading and weighbridge slip endpoints."""

    def setUp(self):
        self.admin = User.objects.create_user(username="lv_admin", password="pass", is_staff=True)
        self.buyer = User.objects.create_user(username="lv_buyer", password="pass")
        # Create minimal order
        self.order = StoreOrder.objects.create(
            buyer=self.buyer,
            status=StoreOrderStatus.READY_FOR_PICKUP,
            payment_status="PAID",
            contact_name="Test",
            contact_phone="09000000000",
            destination_province="Isfahan",
            destination_city="Isfahan",
            destination_address="Test",
            total_amount=1000000,
        )
        self.base_url = f"/api/v1/admin/dashboard/store-orders/{self.order.id}"

    # ── Loading vehicles ─────────────────────────────────────────────────

    def test_create_vehicle_and_mirrors_legacy(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(
            f"{self.base_url}/loading-vehicles/",
            {"driver_name": "Ali", "driver_phone": "09111111111", "vehicle_type": "truck", "vehicle_plate": "12A345"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.driver_name, "Ali")
        self.assertEqual(self.order.vehicle_plate, "12A345")

    def test_list_vehicles(self):
        StoreOrderLoadingVehicle.objects.create(order=self.order, sequence=1, driver_name="Ali", vehicle_plate="12A345")
        self.client.force_authenticate(self.admin)
        res = self.client.get(f"{self.base_url}/loading-vehicles/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_update_vehicle_mirrors_legacy(self):
        v = StoreOrderLoadingVehicle.objects.create(order=self.order, sequence=1, driver_name="Ali", vehicle_plate="12A345")
        self.client.force_authenticate(self.admin)
        res = self.client.patch(
            f"{self.base_url}/loading-vehicles/{v.id}/",
            {"driver_name": "Reza", "vehicle_plate": "99B123"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.driver_name, "Reza")

    def test_delete_vehicle_clears_legacy(self):
        v = StoreOrderLoadingVehicle.objects.create(order=self.order, sequence=1, driver_name="Ali", vehicle_plate="12A345")
        self.order.driver_name = "Ali"
        self.order.vehicle_plate = "12A345"
        self.order.save(update_fields=["driver_name", "vehicle_plate"])
        self.client.force_authenticate(self.admin)
        res = self.client.delete(f"{self.base_url}/loading-vehicles/{v.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.order.refresh_from_db()
        self.assertEqual(self.order.driver_name, "")

    # ── Transition validation ─────────────────────────────────────────────

    def _make_heavy_order(self):
        from products.models import ProductCategory, Product, ProductSpecification, Offer, PricingTier, PricingBasis
        from .models import StoreOrderItem
        category = ProductCategory.objects.create(name="LV Cat", code="lv-cat", product_kind="sheet")
        product = Product.objects.create(category=category, name="Heavy", short_description="", description="", is_active=True)
        ProductSpecification.objects.create(product=product, material_type="sheet", steel_grade="ST37", surface_finish="black",
                                            manufacturing_process="sheet", factory="mobarakeh", cut_type="cut",
                                            thickness_mm="5", width_mm="1250", length_mm="6000")
        seller_user = User.objects.create_user(username="lv_seller_u", password="pass")
        from products.models import Seller
        seller = Seller.objects.create(user=seller_user, company_name="S", business_type="P", location="I", is_verified=True)
        offer = Offer.objects.create(product=product, seller=seller, is_active=True)
        tier = PricingTier.objects.create(offer=offer, tier_name="T", unit_price=1000, price_basis=PricingBasis.TON, minimum_quantity=1)
        order = StoreOrder.objects.create(
            buyer=self.buyer, status=StoreOrderStatus.FULFILLMENT_PENDING,
            payment_status="PAID", contact_name="T", contact_phone="09000000000",
            destination_province="I", destination_city="I", destination_address="A",
            total_amount=50000000,
            stock_verified_at=timezone.now(), proforma_confirmed_at=timezone.now(), loading_permission_at=timezone.now(),
        )
        StoreOrderItem.objects.create(
            order=order, product=product, offer=offer, pricing_tier=tier,
            product_name="Heavy", seller_name="S",
            quantity=50, quantity_unit="TON",
            unit_price=1000000, total_price=50000000,
            estimated_weight_kg="50000.000", final_weight_kg="50000.000",
        )
        return order

    def test_transition_blocked_when_insufficient_vehicles(self):
        order = self._make_heavy_order()
        self.client.force_authenticate(self.admin)
        res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{order.id}/transition/",
            {"status": StoreOrderStatus.READY_FOR_PICKUP, "event": "loading_ready"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("loading_vehicles_insufficient", str(res.data))

    def test_transition_allowed_when_enough_vehicles(self):
        order = self._make_heavy_order()
        # 50 tons needs ceil(50000/25000) = 2 vehicles
        StoreOrderLoadingVehicle.objects.create(order=order, sequence=1, driver_name="Ali", vehicle_plate="AA111")
        StoreOrderLoadingVehicle.objects.create(order=order, sequence=2, driver_name="Reza", vehicle_plate="BB222")
        self.client.force_authenticate(self.admin)
        res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{order.id}/transition/",
            {"status": StoreOrderStatus.READY_FOR_PICKUP, "event": "loading_ready"},
            format="json",
        )
        self.assertNotIn("loading_vehicles_insufficient", str(res.data))

    # ── Weighbridge slips ─────────────────────────────────────────────────

    def test_upload_slip_and_list(self):
        self.client.force_authenticate(self.admin)
        file_content = b"PDF fake content"
        upload_file = SimpleUploadedFile("slip.pdf", file_content, content_type="application/pdf")
        res = self.client.post(
            f"{self.base_url}/weighbridge-slips/",
            {"file": upload_file, "slip_number": "WB-001", "weight_kg": "24500.000"},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertTrue(StoreOrderWeighbridgeSlip.objects.filter(order=self.order).exists())

        list_res = self.client.get(f"{self.base_url}/weighbridge-slips/")
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.data), 1)
        self.assertEqual(list_res.data[0]["slip_number"], "WB-001")

    def test_delete_slip(self):
        slip = StoreOrderWeighbridgeSlip.objects.create(
            order=self.order,
            file=SimpleUploadedFile("s.pdf", b"x"),
            slip_number="WB-DEL",
        )
        self.client.force_authenticate(self.admin)
        res = self.client.delete(f"{self.base_url}/weighbridge-slips/{slip.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(StoreOrderWeighbridgeSlip.objects.filter(pk=slip.id).exists())

    def test_buyer_sees_slips_in_order_detail(self):
        StoreOrderWeighbridgeSlip.objects.create(
            order=self.order,
            file=SimpleUploadedFile("wb.pdf", b"x"),
            slip_number="BUYER-VISIBLE",
        )
        self.client.force_authenticate(self.buyer)
        res = self.client.get(f"/api/v1/store/orders/{self.order.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        slips = res.data.get("weighbridge_slips", [])
        self.assertEqual(len(slips), 1)
        self.assertEqual(slips[0]["slip_number"], "BUYER-VISIBLE")

    def test_invalid_file_extension_rejected(self):
        self.client.force_authenticate(self.admin)
        bad_file = SimpleUploadedFile("bad.exe", b"x", content_type="application/octet-stream")
        res = self.client.post(
            f"{self.base_url}/weighbridge-slips/",
            {"file": bad_file},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
