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
