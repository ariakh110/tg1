from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Customer, CustomerActivity, CustomerTransaction

User = get_user_model()


class CrmActivityFollowUpTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="crm-admin", password="pass", is_staff=True)
        self.outsider = User.objects.create_user(username="crm-outsider", password="pass")
        self.customer = Customer.objects.create(name="حسن رضایی", phone="09120000001")

    # --- stage / source ---
    def test_new_customer_defaults_to_new_stage(self):
        self.assertEqual(self.customer.stage, Customer.STAGE_NEW)
        self.assertEqual(self.customer.source, Customer.SOURCE_OTHER)

    def test_customer_payload_exposes_stage_and_follow_up_annotations(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get("/api/crm/customers/")
        self.assertEqual(res.status_code, 200)
        row = res.data[0]
        self.assertIn("stage", row)
        self.assertIn("stage_display", row)
        self.assertIn("source", row)
        self.assertEqual(row["open_follow_up_count"], 0)
        self.assertIsNone(row["next_follow_up_at"])

    # --- access control ---
    def test_non_admin_denied(self):
        self.client.force_authenticate(self.outsider)
        self.assertIn(self.client.get("/api/crm/activities/").status_code, (401, 403))
        self.assertIn(self.client.get("/api/crm/activities/follow_ups/").status_code, (401, 403))

    # --- activity timeline ---
    def test_log_activity_records_author_and_appears_in_timeline(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(
            "/api/crm/activities/",
            {"customer": self.customer.id, "kind": "call", "body": "قیمت میلگرد ۱۴ را دادم"},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        activity = CustomerActivity.objects.get(id=res.data["id"])
        self.assertEqual(activity.created_by, self.admin)

        detail = self.client.get(f"/api/crm/customers/{self.customer.id}/")
        self.assertEqual(detail.data["activities"][0]["body"], "قیمت میلگرد ۱۴ را دادم")

    # --- follow-up dashboard buckets ---
    def test_follow_ups_buckets_and_customer_annotation(self):
        now = timezone.now()
        CustomerActivity.objects.create(customer=self.customer, kind="call", follow_up_at=now - timedelta(days=2))
        CustomerActivity.objects.create(customer=self.customer, kind="call", follow_up_at=now + timedelta(hours=2))
        CustomerActivity.objects.create(customer=self.customer, kind="call", follow_up_at=now + timedelta(days=3))
        CustomerActivity.objects.create(customer=self.customer, kind="call", follow_up_at=now + timedelta(days=30))
        # انجام‌شده نباید بیاید:
        CustomerActivity.objects.create(
            customer=self.customer, kind="call", follow_up_at=now - timedelta(days=1), follow_up_done=True
        )

        self.client.force_authenticate(self.admin)
        res = self.client.get("/api/crm/activities/follow_ups/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["counts"], {"overdue": 1, "today": 1, "upcoming": 1})

        # مشتری باید همهٔ پیگیری‌های بازِ خود را بشمارد (شاملِ ۳۰روزه = ۴ باز)
        row = self.client.get("/api/crm/customers/").data[0]
        self.assertEqual(row["open_follow_up_count"], 4)

    def test_complete_clears_from_dashboard_but_keeps_on_timeline(self):
        activity = CustomerActivity.objects.create(
            customer=self.customer, kind="call", body="تماس اول", follow_up_at=timezone.now() + timedelta(hours=1)
        )
        self.client.force_authenticate(self.admin)
        res = self.client.post(f"/api/crm/activities/{activity.id}/complete/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["follow_up_done"])
        self.assertIsNotNone(res.data["follow_up_done_at"])

        follow_ups = self.client.get("/api/crm/activities/follow_ups/").data
        self.assertEqual(follow_ups["counts"], {"overdue": 0, "today": 0, "upcoming": 0})
        # هنوز روی تایم‌لاین هست
        detail = self.client.get(f"/api/crm/customers/{self.customer.id}/")
        self.assertEqual(len(detail.data["activities"]), 1)

    def test_complete_rejects_activity_without_follow_up(self):
        activity = CustomerActivity.objects.create(customer=self.customer, kind="note", body="فقط یادداشت")
        self.client.force_authenticate(self.admin)
        res = self.client.post(f"/api/crm/activities/{activity.id}/complete/")
        self.assertEqual(res.status_code, 400)

    # --- stage-change history ---
    def test_changing_stage_logs_an_activity(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(
            f"/api/crm/customers/{self.customer.id}/", {"stage": Customer.STAGE_PROPOSAL}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        log = CustomerActivity.objects.get(customer=self.customer, kind=CustomerActivity.KIND_STAGE)
        self.assertEqual(log.stage_from, Customer.STAGE_NEW)
        self.assertEqual(log.stage_to, Customer.STAGE_PROPOSAL)
        self.assertEqual(log.created_by, self.admin)
        self.assertIsNone(log.follow_up_at)  # نباید پیگیریِ باز بسازد

    def test_saving_same_stage_does_not_log(self):
        self.client.force_authenticate(self.admin)
        self.client.patch(f"/api/crm/customers/{self.customer.id}/", {"company": "فولاد آریا"}, format="json")
        self.assertFalse(
            CustomerActivity.objects.filter(customer=self.customer, kind=CustomerActivity.KIND_STAGE).exists()
        )

    # --- funnel dashboard ---
    def test_non_admin_denied_funnel(self):
        self.client.force_authenticate(self.outsider)
        self.assertIn(self.client.get("/api/crm/customers/funnel/").status_code, (401, 403))

    def test_funnel_counts_conversion_and_ledger_kpis(self):
        # self.customer در مرحلهٔ new است؛ یک برنده و یک پیش‌فاکتور اضافه می‌کنیم
        won = Customer.objects.create(name="کارخانه الف", phone="09120000002", stage=Customer.STAGE_WON)
        Customer.objects.create(name="کارخانه ب", phone="09120000003", stage=Customer.STAGE_PROPOSAL)
        CustomerTransaction.objects.create(customer=won, kind=CustomerTransaction.KIND_PURCHASE, amount=10_000_000)
        CustomerTransaction.objects.create(customer=won, kind=CustomerTransaction.KIND_PAYMENT, amount=4_000_000)

        self.client.force_authenticate(self.admin)
        data = self.client.get("/api/crm/customers/funnel/").data
        self.assertEqual(data["total_customers"], 3)
        self.assertEqual(data["won_count"], 1)
        self.assertAlmostEqual(data["conversion_rate"], round(1 / 3, 4))
        self.assertEqual(data["total_sales"], 10_000_000)
        self.assertEqual(data["total_outstanding"], 6_000_000)  # فقط ماندهٔ مثبت
        self.assertEqual(data["clv"], 10_000_000)  # یک مشتریِ برنده
        stage_map = {s["code"]: s["count"] for s in data["stages"]}
        self.assertEqual(stage_map[Customer.STAGE_NEW], 1)
        self.assertEqual(stage_map[Customer.STAGE_WON], 1)
        self.assertEqual(stage_map[Customer.STAGE_PROPOSAL], 1)

    def test_time_based_kpis_from_stage_history(self):
        self.client.force_authenticate(self.admin)
        # سرنخ → پیش‌فاکتور → مشتری فعال
        self.client.patch(
            f"/api/crm/customers/{self.customer.id}/", {"stage": Customer.STAGE_PROPOSAL}, format="json"
        )
        self.client.patch(
            f"/api/crm/customers/{self.customer.id}/", {"stage": Customer.STAGE_WON}, format="json"
        )
        data = self.client.get("/api/crm/customers/funnel/").data
        self.assertEqual(data["quote_to_close"], 1.0)  # ۱ برنده / ۱ پیش‌فاکتور
        self.assertIsNotNone(data["avg_cycle_days"])

    def test_time_based_kpis_unavailable_without_history(self):
        self.client.force_authenticate(self.admin)
        data = self.client.get("/api/crm/customers/funnel/").data
        self.assertIsNone(data["avg_cycle_days"])
        self.assertIsNone(data["quote_to_close"])
