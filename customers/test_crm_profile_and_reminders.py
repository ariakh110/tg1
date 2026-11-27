from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import RoleCode, UserRole
from messaging.models import BaleUserBinding, MessagingSettings
from messaging.providers.telegram import SendResult

from .bale_reminders import dispatch_crm_bale_reminders
from .models import CrmDueReminder, CrmFollowUp, CrmTask, Customer, CustomerActivity


class CrmProfileAndReminderTests(APITestCase):
    def setUp(self):
        users = get_user_model().objects
        self.admin = users.create_user(username="crm-owner", is_superuser=True)
        self.sales = users.create_user(username="salesperson")
        UserRole.objects.create(user=self.sales, role=RoleCode.CRM_SALES, is_active=True)
        self.customer = Customer.objects.create(
            name="09123456789", phone="09123456789", assigned_to=self.sales,
        )

    def test_mobile_and_web_update_one_scoped_profile(self):
        self.client.force_authenticate(self.sales)
        path = f"/api/v1/crm/mobile/customers/{self.customer.pk}/"
        response = self.client.patch(path, {"name": "نادر", "job_title": "مدیر خرید", "decision_role": "yes"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        other = Customer.objects.create(name="دیگری", phone="09121110000")
        forbidden = self.client.patch(f"/api/v1/crm/mobile/customers/{other.pk}/", {"name": "تغییر"}, format="json")
        self.assertEqual(forbidden.status_code, 404)

        self.client.force_authenticate(self.admin)
        web_path = f"/api/crm/customers/{self.customer.pk}/"
        self.assertEqual(self.client.get(web_path).data["name"], "نادر")
        response = self.client.patch(f"{web_path}profile/", {"decision_role": "no"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.get(path).data["decision_role"], "no")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.job_title, "مدیر خرید")
        self.assertEqual(self.customer.phone, "09123456789")

    def test_call_profile_creates_named_customer_and_replay_keeps_edits(self):
        self.client.force_authenticate(self.sales)
        policy = self.client.get("/api/v1/crm/mobile-call-policy/").data
        now = timezone.now().isoformat()
        payload = {
            "event_uuid": str(uuid4()), "policy_revision": policy["revision"],
            "role_code": "CRM_SALES", "phone": "+۹۸۹۱۲۳۴۰۰۰۰۰",
            "direction": "inbound", "summary": "تماس فروش",
            "call_at": now, "consented_at": now,
            "customer_profile": {"name": "رضا", "job_title": "مسئول خرید", "decision_role": "yes"},
        }
        url = "/api/v1/crm/mobile-call-captures/"
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        customer = Customer.objects.get(phone="09123400000")
        self.assertEqual((customer.name, customer.job_title, customer.assigned_to_id), ("رضا", "مسئول خرید", self.sales.pk))
        customer.name = "رضا رضایی"
        customer.save(update_fields=["name"])
        self.assertEqual(self.client.post(url, payload, format="json").status_code, 200)
        customer.refresh_from_db()
        self.assertEqual(customer.name, "رضا رضایی")

    def test_bale_binding_allows_a_salesperson_without_granting_global_crm_access(self):
        self.client.force_authenticate(self.admin)
        url = "/api/messaging/bale-bindings/"
        response = self.client.get(f"{url}eligible_users/")
        self.assertIn(self.sales.pk, [row["id"] for row in response.data])
        response = self.client.post(url, {"user": self.sales.pk, "bale_user_id": "111"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.client.force_authenticate(self.sales)
        self.assertEqual(self.client.get("/api/crm/customers/").status_code, 403)

    @patch("customers.bale_reminders.telegram.send_message", return_value=SendResult(ok=True, message_id="1"))
    def test_due_reminders_are_private_and_unique_per_due_date(self, send):
        cfg = MessagingSettings.load()
        cfg.telegram_enabled = True
        cfg.telegram_bot_token = "test-token"
        cfg.telegram_api_base = "https://tapi.bale.ai"
        cfg.save()
        BaleUserBinding.objects.create(user=self.sales, bale_user_id="111")
        BaleUserBinding.objects.create(user=self.admin, bale_user_id="222")
        due = timezone.now() - timedelta(minutes=10)
        task = CrmTask.objects.create(owner=self.sales, title="تماس پیگیری", due_at=due, created_by=self.admin)
        CrmFollowUp.objects.create(customer=self.customer, owner=self.admin, title="یادآوری مدیر", due_at=due)
        CrmTask.objects.create(owner=self.sales, title="انجام شد", due_at=due, status=CrmTask.STATUS_COMPLETED)
        CrmTask.objects.create(owner=self.sales, title="آینده", due_at=timezone.now() + timedelta(hours=1))
        CrmTask.objects.create(title="نامشخص", due_at=due)
        CustomerActivity.objects.create(customer=self.customer, follow_up_note="پیگیری قدیمی", follow_up_at=due)

        self.assertEqual(dispatch_crm_bale_reminders(), 3)
        self.assertEqual(dispatch_crm_bale_reminders(), 0)
        texts = {call.args[2].splitlines()[1]: call.args[1] for call in send.call_args_list}
        self.assertEqual(texts, {"تماس پیگیری": "111", "یادآوری مدیر": "222", "پیگیری قدیمی": "111"})
        self.assertEqual(CrmDueReminder.objects.filter(status="sent").count(), 3)

        task.due_at = due + timedelta(minutes=1)
        task.save(update_fields=["due_at"])
        self.assertEqual(dispatch_crm_bale_reminders(), 1)
        self.assertEqual(send.call_args.args[1], "111")
