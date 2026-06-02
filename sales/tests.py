from django.contrib.auth import get_user_model
from datetime import timedelta
import json

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

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
    StoreNotificationStatus,
    StoreOrder,
    StoreOrderNotification,
    StoreOrderStatus,
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

    def test_loading_transition_requires_payment_and_risk_checks(self):
        product, _offer, _tier = self.make_product(price=43000)
        res = self.create_order(product, quantity="1")
        self.client.force_authenticate(self.admin)

        blocked_res = self.client.post(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/transition/",
            {"status": StoreOrderStatus.FULFILLMENT_PENDING},
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
