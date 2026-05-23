from django.contrib.auth import get_user_model
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import OrderRequest
from products.models import (
    DeliveryLocation,
    Offer,
    PricingTier,
    Product,
    ProductCategory,
    ProductSpecification,
    Seller,
)

from .models import StoreNotificationStatus, StoreOrder, StoreOrderNotification, StoreOrderStatus

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

    def make_product(self, *, price=43000, is_active=True, availability_status=Product.AVAILABILITY_IN_STOCK):
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
            manufacturing_process="sheet",
            factory="mobarakeh",
            cut_type="cut",
            thickness_mm="2",
            width_mm="1250",
            length_mm="6000",
        )
        offer = Offer.objects.create(product=product, seller=self.seller, is_active=True)
        tier = None
        if price is not None:
            tier = PricingTier.objects.create(
                offer=offer,
                tier_name="Daily price",
                unit_price=price,
                minimum_quantity=1,
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

    def create_order(self, product, quantity="2", buyer=None, quantity_unit="ton", settlement_term_days=None):
        self.client.force_authenticate(buyer or self.buyer)
        payload = {
            "contact_name": "Buyer Co",
            "contact_phone": "09120000000",
            "destination_province": "Tehran",
            "destination_city": "Tehran",
            "destination_address": "Buyer warehouse",
            "items": [
                {
                    "product_id": product.id,
                    "quantity": quantity,
                    "quantity_unit": quantity_unit,
                }
            ],
        }
        if settlement_term_days is not None:
            payload["settlement_term_days"] = settlement_term_days
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
        self.assertTrue(res.data["payment_due_at"])
        self.assertIn("/account/payments?", res.data["payment_link_url"])
        self.assertEqual(len(res.data["items"]), 1)
        self.assertEqual(res.data["items"][0]["unit_price_amount"], 43000)
        self.assertEqual(res.data["items"][0]["estimated_weight_kg"], "2000.000")
        self.assertEqual(OrderRequest.all_objects.count(), 0)

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
        self.assertEqual(res.data["items"][0]["estimated_weight_kg"], "1177.500")
        self.assertEqual(res.data["total_amount"], 50633)

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
        self.assertIsNone(res.data["items"][0]["unit_price_amount"])
        self.assertEqual(res.data["total_amount"], 0)

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
        self.client.force_authenticate(self.admin)

        update_res = self.client.patch(
            f"/api/v1/admin/dashboard/store-orders/{res.data['id']}/",
            {
                "destination_province": "Tehran",
                "destination_city": "Tehran",
                "payment_due_at": due_at,
                "admin_notes": "Call before shipping",
            },
            format="json",
        )

        self.assertEqual(update_res.status_code, status.HTTP_200_OK, update_res.data)
        self.assertEqual(update_res.data["destination_province"], "Tehran")
        self.assertEqual(update_res.data["destination_city"], "Tehran")
        self.assertEqual(update_res.data["admin_notes"], "Call before shipping")
        self.assertTrue(StoreOrder.objects.get(pk=res.data["id"]).status_history.filter(event="STORE_ORDER_ADMIN_UPDATED").exists())

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
