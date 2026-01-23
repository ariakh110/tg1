from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import RoleCode, UserRole
from products.models import ProductCategory

from .models import OrderStatus, OrderType

User = get_user_model()


class OrderFlowTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username="buyer", password="pass1234")
        self.seller = User.objects.create_user(username="seller", password="pass1234")

        UserRole.objects.update_or_create(
            user=self.buyer,
            role=RoleCode.BUYER,
            defaults={"is_active": True, "activated_at": timezone.now()},
        )
        UserRole.objects.create(
            user=self.seller,
            role=RoleCode.SELLER,
            is_active=True,
            activated_at=timezone.now(),
        )
        self.category = ProductCategory.objects.create(name="Steel")

    def test_create_buy_order(self):
        self.client.force_authenticate(self.buyer)
        resp = self.client.post(
            "/api/v1/orders/",
            {
                "type": OrderType.BUY,
                "title": "Buy steel",
                "product_type": self.category.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["type"], OrderType.BUY)

    def test_create_sell_order_requires_active_seller(self):
        unverified = User.objects.create_user(username="seller2", password="pass1234")
        UserRole.objects.create(user=unverified, role=RoleCode.SELLER, is_active=False)
        self.client.force_authenticate(unverified)
        resp = self.client.post(
            "/api/v1/orders/",
            {
                "type": OrderType.SELL,
                "title": "Sell steel",
                "product_type": self.category.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_offer_and_accept_buy_order(self):
        self.client.force_authenticate(self.buyer)
        order_resp = self.client.post(
            "/api/v1/orders/",
            {
                "type": OrderType.BUY,
                "title": "Buy steel",
                "product_type": self.category.id,
            },
            format="json",
        )
        order_id = order_resp.data["id"]

        self.client.force_authenticate(self.seller)
        offer_resp = self.client.post(
            f"/api/v1/orders/{order_id}/offers/",
            {"price_total": {"amount": 1000, "currency": "IRR"}},
            format="json",
        )
        self.assertEqual(offer_resp.status_code, status.HTTP_201_CREATED)
        offer_id = offer_resp.data["id"]

        self.client.force_authenticate(self.buyer)
        accept_resp = self.client.post(f"/api/v1/offers/{offer_id}/accept/")
        self.assertEqual(accept_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(accept_resp.data["status"], OrderStatus.OFFER_SELECTED)

    def test_offer_and_accept_sell_order(self):
        self.client.force_authenticate(self.seller)
        order_resp = self.client.post(
            "/api/v1/orders/",
            {
                "type": OrderType.SELL,
                "title": "Sell steel",
                "product_type": self.category.id,
            },
            format="json",
        )
        self.assertEqual(order_resp.status_code, status.HTTP_201_CREATED)
        order_id = order_resp.data["id"]

        self.client.force_authenticate(self.buyer)
        offer_resp = self.client.post(
            f"/api/v1/orders/{order_id}/offers/",
            {"price_total": {"amount": 2000, "currency": "IRR"}},
            format="json",
        )
        self.assertEqual(offer_resp.status_code, status.HTTP_201_CREATED)
        offer_id = offer_resp.data["id"]

        self.client.force_authenticate(self.seller)
        accept_resp = self.client.post(f"/api/v1/offers/{offer_id}/accept/")
        self.assertEqual(accept_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(accept_resp.data["status"], OrderStatus.OFFER_SELECTED)

# Create your tests here.
