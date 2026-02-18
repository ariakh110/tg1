from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import RoleCode, UserRole
from products.models import ProductCategory

from .models import (
    OrderRequest,
    OrderRequestStatus,
    OrderRequestType,
    OrderStatus,
    OrderType,
)

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


class OrderRequestFlowTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username="request_buyer", password="pass1234")
        self.buyer_viewer = User.objects.create_user(username="request_viewer", password="pass1234")
        self.seller = User.objects.create_user(username="request_seller", password="pass1234")
        self.warehouse = User.objects.create_user(username="warehouse", password="pass1234")

        UserRole.objects.update_or_create(
            user=self.buyer,
            role=RoleCode.BUYER,
            defaults={"is_active": True, "activated_at": timezone.now()},
        )
        UserRole.objects.update_or_create(
            user=self.buyer_viewer,
            role=RoleCode.BUYER,
            defaults={"is_active": True, "activated_at": timezone.now()},
        )
        UserRole.objects.update_or_create(
            user=self.seller,
            role=RoleCode.SELLER,
            defaults={"is_active": True, "activated_at": timezone.now()},
        )
        UserRole.objects.update_or_create(
            user=self.warehouse,
            role=RoleCode.WAREHOUSE_MANAGER,
            defaults={"is_active": True, "activated_at": timezone.now()},
        )
        self.category = ProductCategory.objects.create(name="Marketplace Steel")

    def _results(self, response):
        if isinstance(response.data, list):
            return response.data
        return response.data.get("results", [])

    def test_buy_request_visible_in_feed(self):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            "/api/v1/my/requests/",
            {
                "type": OrderRequestType.BUY,
                "category": self.category.id,
                "product_title": "Buy sheets",
                "quantity": "10",
                "quantity_unit": "ton",
            },
            format="json",
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_resp.data["status"], OrderRequestStatus.ACTIVE)

        self.client.force_authenticate(self.buyer_viewer)
        feed_resp = self.client.get("/api/v1/marketplace/feed/")
        self.assertEqual(feed_resp.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in self._results(feed_resp)]
        self.assertIn(create_resp.data["id"], ids)

    def test_sell_request_requires_warehouse_approval_before_feed(self):
        self.client.force_authenticate(self.seller)
        create_resp = self.client.post(
            "/api/v1/my/requests/",
            {
                "type": OrderRequestType.SELL,
                "category": self.category.id,
                "product_title": "Sell rebar",
                "quantity": "20",
                "quantity_unit": "ton",
            },
            format="json",
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_resp.data["status"], OrderRequestStatus.PENDING_WAREHOUSE)
        request_id = create_resp.data["id"]

        self.client.force_authenticate(self.buyer_viewer)
        feed_before = self.client.get("/api/v1/marketplace/feed/")
        ids_before = [item["id"] for item in self._results(feed_before)]
        self.assertNotIn(request_id, ids_before)

        self.client.force_authenticate(self.warehouse)
        verify_resp = self.client.post(
            f"/api/v1/warehouse/verify/{request_id}/",
            {"decision": "APPROVE"},
            format="json",
        )
        self.assertEqual(verify_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_resp.data["status"], OrderRequestStatus.APPROVED)

        self.client.force_authenticate(self.buyer_viewer)
        feed_after = self.client.get("/api/v1/marketplace/feed/")
        ids_after = [item["id"] for item in self._results(feed_after)]
        self.assertIn(request_id, ids_after)

    def test_soft_delete_hides_request_from_feed(self):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            "/api/v1/my/requests/",
            {
                "type": OrderRequestType.BUY,
                "product_title": "Buy coils",
            },
            format="json",
        )
        request_id = create_resp.data["id"]
        deactivate_resp = self.client.patch(
            f"/api/v1/my/requests/{request_id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(deactivate_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(deactivate_resp.data["status"], OrderRequestStatus.DEACTIVATED)

        self.assertTrue(
            OrderRequest.all_objects.filter(
                pk=request_id, is_active=False, status=OrderRequestStatus.DEACTIVATED
            ).exists()
        )

        self.client.force_authenticate(self.buyer_viewer)
        feed_resp = self.client.get("/api/v1/marketplace/feed/")
        ids = [item["id"] for item in self._results(feed_resp)]
        self.assertNotIn(request_id, ids)

    def test_reactivate_buy_request_returns_to_feed(self):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            "/api/v1/my/requests/",
            {"type": OrderRequestType.BUY, "product_title": "Buy plates"},
            format="json",
        )
        request_id = create_resp.data["id"]

        self.client.patch(
            f"/api/v1/my/requests/{request_id}/",
            {"is_active": False},
            format="json",
        )
        reactivate_resp = self.client.post(
            f"/api/v1/my/requests/{request_id}/reactivate/",
            format="json",
        )
        self.assertEqual(reactivate_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(reactivate_resp.data["status"], OrderRequestStatus.ACTIVE)
        self.assertTrue(reactivate_resp.data["is_active"])

        self.client.force_authenticate(self.buyer_viewer)
        feed_resp = self.client.get("/api/v1/marketplace/feed/")
        ids = [item["id"] for item in self._results(feed_resp)]
        self.assertIn(request_id, ids)

    def test_reactivate_sell_request_moves_to_pending_warehouse(self):
        self.client.force_authenticate(self.seller)
        create_resp = self.client.post(
            "/api/v1/my/requests/",
            {
                "type": OrderRequestType.SELL,
                "category": self.category.id,
                "product_title": "Sell sheets",
            },
            format="json",
        )
        request_id = create_resp.data["id"]

        self.client.force_authenticate(self.warehouse)
        self.client.post(
            f"/api/v1/warehouse/verify/{request_id}/",
            {"decision": "APPROVE"},
            format="json",
        )

        self.client.force_authenticate(self.seller)
        self.client.patch(
            f"/api/v1/my/requests/{request_id}/",
            {"is_active": False},
            format="json",
        )
        reactivate_resp = self.client.post(
            f"/api/v1/my/requests/{request_id}/reactivate/",
            format="json",
        )
        self.assertEqual(reactivate_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            reactivate_resp.data["status"], OrderRequestStatus.PENDING_WAREHOUSE
        )
        self.assertTrue(reactivate_resp.data["is_active"])
        self.assertIsNone(reactivate_resp.data["verified_by"])
        self.assertIsNone(reactivate_resp.data["verified_at"])

        self.client.force_authenticate(self.buyer_viewer)
        feed_resp = self.client.get("/api/v1/marketplace/feed/")
        ids = [item["id"] for item in self._results(feed_resp)]
        self.assertNotIn(request_id, ids)

    def test_edit_approved_sell_resets_to_pending(self):
        self.client.force_authenticate(self.seller)
        create_resp = self.client.post(
            "/api/v1/my/requests/",
            {
                "type": OrderRequestType.SELL,
                "category": self.category.id,
                "product_title": "Sell profile",
            },
            format="json",
        )
        request_id = create_resp.data["id"]

        self.client.force_authenticate(self.warehouse)
        verify_resp = self.client.post(
            f"/api/v1/warehouse/verify/{request_id}/",
            {"decision": "APPROVE"},
            format="json",
        )
        self.assertEqual(verify_resp.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.seller)
        patch_resp = self.client.patch(
            f"/api/v1/my/requests/{request_id}/",
            {"quantity": "99"},
            format="json",
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_resp.data["status"], OrderRequestStatus.PENDING_WAREHOUSE)

        self.client.force_authenticate(self.buyer_viewer)
        feed_resp = self.client.get("/api/v1/marketplace/feed/")
        ids = [item["id"] for item in self._results(feed_resp)]
        self.assertNotIn(request_id, ids)

    def test_upload_documents_accepts_pdf_and_zip_only(self):
        self.client.force_authenticate(self.seller)
        create_resp = self.client.post(
            "/api/v1/my/requests/",
            {"type": OrderRequestType.SELL, "product_title": "Sell wire"},
            format="json",
        )
        request_id = create_resp.data["id"]

        pdf_file = SimpleUploadedFile(
            "stock.pdf", b"%PDF-1.4 test", content_type="application/pdf"
        )
        zip_file = SimpleUploadedFile(
            "stock.zip", b"PK\x03\x04test", content_type="application/zip"
        )
        valid_resp = self.client.post(
            f"/api/v1/my/requests/{request_id}/documents/",
            {"file": [pdf_file, zip_file]},
            format="multipart",
        )
        self.assertEqual(valid_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(valid_resp.data), 2)

        txt_file = SimpleUploadedFile(
            "stock.txt", b"text", content_type="text/plain"
        )
        invalid_resp = self.client.post(
            f"/api/v1/my/requests/{request_id}/documents/",
            {"file": [txt_file]},
            format="multipart",
        )
        self.assertEqual(invalid_resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_warehouse_manager_can_verify(self):
        self.client.force_authenticate(self.seller)
        create_resp = self.client.post(
            "/api/v1/my/requests/",
            {"type": OrderRequestType.SELL, "product_title": "Sell billet"},
            format="json",
        )
        request_id = create_resp.data["id"]

        self.client.force_authenticate(self.buyer)
        verify_resp = self.client.post(
            f"/api/v1/warehouse/verify/{request_id}/",
            {"decision": "APPROVE"},
            format="json",
        )
        self.assertEqual(verify_resp.status_code, status.HTTP_403_FORBIDDEN)


class AdminDashboardAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ops_admin",
            email="ops_admin@example.com",
            password="pass1234",
            is_staff=True,
        )
        self.buyer = User.objects.create_user(
            username="ops_buyer",
            email="ops_buyer@example.com",
            password="pass1234",
        )
        self.seller = User.objects.create_user(
            username="ops_seller",
            email="ops_seller@example.com",
            password="pass1234",
        )
        self.other_user = User.objects.create_user(
            username="ops_other",
            email="ops_other@example.com",
            password="pass1234",
        )

        UserRole.objects.update_or_create(
            user=self.buyer,
            role=RoleCode.BUYER,
            defaults={"is_active": True, "activated_at": timezone.now()},
        )
        UserRole.objects.update_or_create(
            user=self.seller,
            role=RoleCode.SELLER,
            defaults={"is_active": True, "activated_at": timezone.now()},
        )

        self.category = ProductCategory.objects.create(name="Admin Dashboard Steel")

        self.client.force_authenticate(self.buyer)
        self.buy_request = self.client.post(
            "/api/v1/my/requests/",
            {
                "type": OrderRequestType.BUY,
                "category": self.category.id,
                "product_title": "Ops buy request",
                "quantity": "10",
                "quantity_unit": "ton",
            },
            format="json",
        ).data

        self.client.force_authenticate(self.seller)
        self.sell_request = self.client.post(
            "/api/v1/my/requests/",
            {
                "type": OrderRequestType.SELL,
                "category": self.category.id,
                "product_title": "Ops sell request",
                "quantity": "12",
                "quantity_unit": "ton",
            },
            format="json",
        ).data

        self.client.force_authenticate(self.other_user)
        self.client.post(
            "/api/v1/kyc/",
            {"requested_roles": [RoleCode.SELLER]},
            format="json",
        )

    def _results(self, response):
        if isinstance(response.data, list):
            return response.data
        return response.data.get("results", [])

    def test_admin_summary_requires_admin_access(self):
        self.client.force_authenticate(self.buyer)
        denied = self.client.get("/api/v1/admin/dashboard/summary/")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.admin)
        allowed = self.client.get("/api/v1/admin/dashboard/summary/")
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertIn("stats", allowed.data)
        self.assertIn("latest_order_requests", allowed.data)
        self.assertIn("latest_kyc_requests", allowed.data)
        self.assertGreaterEqual(allowed.data["stats"]["users_total"], 4)

    def test_admin_can_manage_order_requests(self):
        self.client.force_authenticate(self.admin)

        list_resp = self.client.get("/api/v1/admin/dashboard/order-requests/")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        listed_ids = [item["id"] for item in self._results(list_resp)]
        self.assertIn(self.buy_request["id"], listed_ids)
        self.assertIn(self.sell_request["id"], listed_ids)

        deactivate_resp = self.client.post(
            f"/api/v1/admin/dashboard/order-requests/{self.buy_request['id']}/deactivate/"
        )
        self.assertEqual(deactivate_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(deactivate_resp.data["status"], OrderRequestStatus.DEACTIVATED)
        self.assertFalse(deactivate_resp.data["is_active"])

        reactivate_resp = self.client.post(
            f"/api/v1/admin/dashboard/order-requests/{self.buy_request['id']}/reactivate/"
        )
        self.assertEqual(reactivate_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(reactivate_resp.data["status"], OrderRequestStatus.ACTIVE)
        self.assertTrue(reactivate_resp.data["is_active"])

        verify_resp = self.client.post(
            f"/api/v1/admin/dashboard/order-requests/{self.sell_request['id']}/verify/",
            {"decision": "APPROVE"},
            format="json",
        )
        self.assertEqual(verify_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_resp.data["status"], OrderRequestStatus.APPROVED)

    def test_admin_activity_feed_returns_events(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/v1/admin/dashboard/activities/?limit=20")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("results", resp.data)
        self.assertTrue(len(resp.data["results"]) > 0)
