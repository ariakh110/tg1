from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.admin_sections import ALL, effective_admin_sections
from accounts.models import RoleCode, UserRole
from customers.models import Customer

User = get_user_model()


class MarketerSectionAccessTests(APITestCase):
    """نقشِ بازاریاب فقط به بخش‌های CRM/فروش دسترسی دارد؛ بقیه در سرور بسته است."""

    def setUp(self):
        self.superuser = User.objects.create_user(
            username="root", password="pass", is_staff=True, is_superuser=True
        )
        self.admin = User.objects.create_user(username="admin1", password="pass")
        UserRole.objects.create(user=self.admin, role=RoleCode.ADMIN, is_active=True)
        self.marketer = User.objects.create_user(username="mkt", password="pass")
        UserRole.objects.create(user=self.marketer, role=RoleCode.MARKETER, is_active=True)
        self.inactive_marketer = User.objects.create_user(username="mkt-off", password="pass")
        UserRole.objects.create(user=self.inactive_marketer, role=RoleCode.MARKETER, is_active=False)
        Customer.objects.create(name="مشتری تست", phone="09120000009")

    # --- effective_admin_sections ---
    def test_superuser_and_admin_get_all(self):
        self.assertEqual(effective_admin_sections(self.superuser), ALL)
        self.assertEqual(effective_admin_sections(self.admin), ALL)

    def test_marketer_sections_are_limited(self):
        self.assertEqual(
            effective_admin_sections(self.marketer),
            {"crm", "crm-followups", "crm-funnel", "messaging", "assistant", "direct-sales"},
        )

    def test_inactive_marketer_has_no_sections(self):
        self.assertEqual(effective_admin_sections(self.inactive_marketer), set())

    # --- /me payload ---
    def test_me_returns_all_for_admin(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get("/api/v1/users/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["admin_sections"], "ALL")

    def test_me_returns_ordered_section_list_for_marketer(self):
        self.client.force_authenticate(self.marketer)
        res = self.client.get("/api/v1/users/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.data["admin_sections"],
            ["direct-sales", "crm", "crm-followups", "crm-funnel", "messaging", "assistant"],
        )

    # --- allowed sections work ---
    def test_marketer_can_access_crm_sections(self):
        self.client.force_authenticate(self.marketer)
        self.assertEqual(self.client.get("/api/crm/customers/").status_code, 200)
        self.assertEqual(self.client.get("/api/crm/customers/funnel/").status_code, 200)
        self.assertEqual(self.client.get("/api/crm/activities/follow_ups/").status_code, 200)
        self.assertEqual(self.client.get("/api/messaging/groups/").status_code, 200)

    def test_marketer_can_access_assistant(self):
        self.client.force_authenticate(self.marketer)
        self.assertEqual(self.client.get("/api/assistant/admin/inquiries/").status_code, 200)

    # --- forbidden sections are blocked server-side ---
    def test_marketer_denied_users_admin(self):
        self.client.force_authenticate(self.marketer)
        self.assertIn(self.client.get("/api/v1/admin/users/").status_code, (401, 403))

    def test_admin_keeps_full_access(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/v1/admin/users/").status_code, 200)
        self.assertEqual(self.client.get("/api/crm/customers/").status_code, 200)
