from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import RoleCode, UserRole

User = get_user_model()


class KYCFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="seller", password="pass1234")
        UserRole.objects.create(user=self.user, role=RoleCode.SELLER, is_active=False)
        self.admin = User.objects.create_user(
            username="admin", password="pass1234", is_staff=True
        )

    def test_kyc_approve_activates_role(self):
        self.client.force_authenticate(self.user)
        create_resp = self.client.post(
            "/api/v1/kyc/",
            {"requested_roles": [RoleCode.SELLER]},
            format="json",
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        kyc_id = create_resp.data["id"]

        self.client.force_authenticate(self.admin)
        approve_resp = self.client.post(f"/api/v1/kyc/{kyc_id}/approve/")
        self.assertEqual(approve_resp.status_code, status.HTTP_200_OK)

        role = UserRole.objects.get(user=self.user, role=RoleCode.SELLER)
        self.assertTrue(role.is_active)


class AdminUsersAndKycReadTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_reader",
            email="admin_reader@example.com",
            password="pass1234",
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="kyc_user",
            email="kyc_user@example.com",
            password="pass1234",
        )
        UserRole.objects.create(user=self.user, role=RoleCode.SELLER, is_active=False)

    def test_admin_users_endpoint_lists_users(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/v1/admin/users/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        usernames = [item["username"] for item in results]
        self.assertIn("kyc_user", usernames)

    def test_admin_kyc_list_includes_request_user(self):
        self.client.force_authenticate(self.user)
        create_resp = self.client.post(
            "/api/v1/kyc/",
            {"requested_roles": [RoleCode.SELLER]},
            format="json",
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.admin)
        list_resp = self.client.get("/api/v1/kyc/?status=PENDING")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        results = list_resp.data if isinstance(list_resp.data, list) else list_resp.data.get("results", [])
        self.assertTrue(any(item.get("user", {}).get("username") == "kyc_user" for item in results))
