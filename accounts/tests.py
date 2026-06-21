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


class AdminUserManagementTests(APITestCase):
    def setUp(self):
        self.superadmin = User.objects.create_superuser(
            username="root", email="root@example.com", password="pass1234"
        )
        self.admin = User.objects.create_user(  # ادمینِ غیرسوپریوزر
            username="staffadmin", password="pass1234", is_staff=True
        )
        self.user = User.objects.create_user(
            username="member", email="member@example.com", password="oldpass1234"
        )

    def _token(self, username, password):
        return self.client.post(
            "/api/token/", {"username": username, "password": password}, format="json"
        )

    # --- approve / suspend ---
    def test_set_active_gates_login(self):
        self.client.force_authenticate(self.admin)
        # تعلیق
        resp = self.client.post(f"/api/v1/admin/users/{self.user.id}/set_active/", {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.client.force_authenticate(None)
        self.assertEqual(self._token("member", "oldpass1234").status_code, 401)
        # تأیید مجدد
        self.client.force_authenticate(self.admin)
        self.client.post(f"/api/v1/admin/users/{self.user.id}/set_active/", {"is_active": True}, format="json")
        self.client.force_authenticate(None)
        self.assertEqual(self._token("member", "oldpass1234").status_code, 200)

    def test_admin_cannot_deactivate_self(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f"/api/v1/admin/users/{self.admin.id}/set_active/", {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    # --- password ---
    def test_set_password_allows_new_login(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/v1/admin/users/{self.user.id}/set_password/", {"password": "newpass1234"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.client.force_authenticate(None)
        self.assertEqual(self._token("member", "oldpass1234").status_code, 401)
        self.assertEqual(self._token("member", "newpass1234").status_code, 200)

    def test_set_password_rejects_short(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/v1/admin/users/{self.user.id}/set_password/", {"password": "123"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.client.force_authenticate(None)
        self.assertEqual(self._token("member", "oldpass1234").status_code, 200)  # رمز عوض نشده

    # --- roles ---
    def test_superuser_grants_admin_role(self):
        self.client.force_authenticate(self.superadmin)
        resp = self.client.post(
            f"/api/v1/admin/users/{self.user.id}/set_role/",
            {"role": RoleCode.ADMIN, "is_active": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(UserRole.objects.get(user=self.user, role=RoleCode.ADMIN).is_active)
        # حالا کاربر باید دسترسی ادمین داشته باشد
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get("/api/v1/admin/users/").status_code, 200)

    def test_non_superuser_cannot_grant_admin_role(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/v1/admin/users/{self.user.id}/set_role/",
            {"role": RoleCode.ADMIN, "is_active": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_grants_seller_role(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/v1/admin/users/{self.user.id}/set_role/",
            {"role": RoleCode.SELLER, "is_active": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(UserRole.objects.get(user=self.user, role=RoleCode.SELLER).is_active)

    # --- guards ---
    def test_non_superuser_cannot_modify_superuser(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/v1/admin/users/{self.superadmin.id}/set_active/", {"is_active": False}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_non_admin_denied(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post(
            f"/api/v1/admin/users/{self.user.id}/set_active/", {"is_active": True}, format="json"
        )
        self.assertIn(resp.status_code, (401, 403))
