from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (
    CrmOpportunity,
    CrmOpportunityStageHistory,
    CrmSyncEvent,
    Customer,
    CustomerActivity,
    CustomerTransaction,
)

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


class CrmOpportunityTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="opp-admin", password="pass", is_staff=True)
        self.outsider = User.objects.create_user(username="opp-outsider", password="pass")
        self.buyer = User.objects.create_user(username="opp-buyer", password="pass")
        self.customer = Customer.objects.create(
            name="شرکت خریدار",
            phone="09120000101",
            user=self.buyer,
            stage=Customer.STAGE_NEW,
        )

    def test_store_order_sync_is_unique_idempotent_and_keeps_customer_stage(self):
        from sales.models import StoreOrder, StoreOrderStatus

        from .opportunities import sync_store_order_opportunity

        order = StoreOrder.objects.create(
            buyer=self.buyer,
            contact_name=self.customer.name,
            contact_phone=self.customer.phone,
            status=StoreOrderStatus.QUOTE_REQUESTED,
            total_amount=80_000_000,
        )
        opportunity = sync_store_order_opportunity(order, event_key="test:order:pricing")
        self.assertEqual(opportunity.stage, CrmOpportunity.STAGE_PRICING)
        self.assertEqual(opportunity.expected_value_irr, 80_000_000)
        self.assertEqual(opportunity.customer, self.customer)

        duplicate = sync_store_order_opportunity(order, event_key="test:order:pricing")
        self.assertEqual(duplicate.pk, opportunity.pk)
        self.assertEqual(CrmOpportunity.objects.count(), 1)
        self.assertEqual(CrmOpportunityStageHistory.objects.count(), 1)

        order.status = StoreOrderStatus.PRICE_CONFIRMED
        order.total_amount = 120_000_000
        order.save(update_fields=["status", "total_amount", "updated_at"])
        opportunity = sync_store_order_opportunity(order, event_key="test:order:quoted")
        self.assertEqual(opportunity.stage, CrmOpportunity.STAGE_QUOTE_SENT)
        self.assertEqual(opportunity.expected_value_irr, 120_000_000)

        order.status = StoreOrderStatus.QUOTE_REQUESTED
        order.quote_rejection_reason = "نیاز به اصلاح مقدار"
        order.save(update_fields=["status", "quote_rejection_reason", "updated_at"])
        opportunity = sync_store_order_opportunity(order, event_key="test:order:quote-rejected")
        self.assertEqual(opportunity.stage, CrmOpportunity.STAGE_PRICING)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.stage, Customer.STAGE_NEW)

    def test_assistant_inquiry_sync_tracks_one_opportunity(self):
        from assistant.models import AssistantConversation, AssistantInquiry

        from .opportunities import sync_assistant_inquiry_opportunity

        conversation = AssistantConversation.objects.create(
            session_key="opp-inquiry",
            user=self.buyer,
            lead_name=self.customer.name,
            lead_phone=self.customer.phone,
        )
        inquiry = AssistantInquiry.objects.create(
            conversation=conversation,
            product="ورق",
            grade="CK45",
            size="۱۰ میل",
            quantity="۵ تن",
            matched_price=350_000,
            status=AssistantInquiry.STATUS_NEW,
        )
        opportunity = sync_assistant_inquiry_opportunity(inquiry, event_key="test:inquiry:new")
        self.assertEqual(opportunity.stage, CrmOpportunity.STAGE_NEW_INQUIRY)
        self.assertEqual(opportunity.expected_value_irr, 0)  # matched_price is a unit/catalog price, not deal total
        self.assertEqual(opportunity.metadata["matched_price_toman"], 350_000)

        inquiry.status = AssistantInquiry.STATUS_QUOTED
        inquiry.save(update_fields=["status", "updated_at"])
        opportunity = sync_assistant_inquiry_opportunity(inquiry, event_key="test:inquiry:quoted")
        self.assertEqual(opportunity.stage, CrmOpportunity.STAGE_QUOTE_SENT)
        self.assertEqual(CrmOpportunity.objects.count(), 1)

    def test_source_projected_fields_cannot_be_overwritten_from_crm_api(self):
        from sales.models import StoreOrder, StoreOrderStatus

        from .opportunities import sync_store_order_opportunity

        order = StoreOrder.objects.create(
            buyer=self.buyer,
            contact_phone=self.customer.phone,
            status=StoreOrderStatus.PAYMENT_PENDING,
            total_amount=75_000_000,
        )
        opportunity = sync_store_order_opportunity(order, event_key="test:source-protection")
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/crm/opportunities/{opportunity.pk}/",
            {"expected_value_irr": 1, "title": "دستکاری"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.expected_value_irr, 75_000_000)
        self.assertNotEqual(opportunity.title, "دستکاری")

    def test_opportunity_funnel_is_independent_from_customer_funnel(self):
        CrmOpportunity.objects.create(
            customer=self.customer,
            title="سفارش اول",
            stage=CrmOpportunity.STAGE_PAYMENT_PENDING,
            expected_value_irr=100_000_000,
            probability=75,
        )
        CrmOpportunity.objects.create(
            customer=self.customer,
            title="سفارش دوم",
            stage=CrmOpportunity.STAGE_WON,
            expected_value_irr=50_000_000,
            probability=100,
            closed_at=timezone.now(),
        )
        self.client.force_authenticate(self.admin)
        opportunity_data = self.client.get("/api/crm/opportunities/funnel/").data
        customer_data = self.client.get("/api/crm/customers/funnel/").data

        self.assertEqual(opportunity_data["total_opportunities"], 2)
        self.assertEqual(opportunity_data["open_count"], 1)
        self.assertEqual(opportunity_data["won_count"], 1)
        self.assertEqual(opportunity_data["open_pipeline_value_irr"], 100_000_000)
        self.assertEqual(opportunity_data["won_revenue_irr"], 50_000_000)
        self.assertEqual(customer_data["total_customers"], 1)
        self.assertEqual(customer_data["won_count"], 0)

    def test_manual_transition_records_history_and_requires_lost_reason(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/crm/opportunities/",
            {
                "customer": self.customer.pk,
                "title": "نیاز دستی",
                "expected_value_irr": 20_000_000,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        opportunity_id = created.data["id"]
        rejected = self.client.post(
            f"/api/crm/opportunities/{opportunity_id}/transition/",
            {"stage": CrmOpportunity.STAGE_LOST},
            format="json",
        )
        self.assertEqual(rejected.status_code, 400)

        transitioned = self.client.post(
            f"/api/crm/opportunities/{opportunity_id}/transition/",
            {"stage": CrmOpportunity.STAGE_QUALIFIED},
            format="json",
        )
        self.assertEqual(transitioned.status_code, 200, transitioned.data)
        self.assertEqual(transitioned.data["stage"], CrmOpportunity.STAGE_QUALIFIED)
        self.assertEqual(CrmOpportunityStageHistory.objects.filter(opportunity_id=opportunity_id).count(), 2)

        detail = self.client.get(f"/api/crm/customers/{self.customer.pk}/")
        self.assertEqual(detail.data["opportunities"][0]["id"], opportunity_id)

    def test_non_admin_cannot_read_opportunity_funnel_or_sync_events(self):
        self.client.force_authenticate(self.outsider)
        self.assertIn(self.client.get("/api/crm/opportunities/funnel/").status_code, (401, 403))
        self.assertIn(self.client.get("/api/crm/sync-events/").status_code, (401, 403))

    def test_retryable_sync_event_processes_order(self):
        from sales.models import StoreOrder, StoreOrderStatus

        from .opportunities import process_sync_event

        order = StoreOrder.objects.create(
            buyer=self.buyer,
            contact_name=self.customer.name,
            contact_phone=self.customer.phone,
            status=StoreOrderStatus.PAYMENT_PENDING,
            total_amount=60_000_000,
        )
        sync_event = CrmSyncEvent.objects.create(
            source_type=CrmOpportunity.SOURCE_STORE_ORDER,
            source_id=str(order.pk),
            event_key="test:sync-event:order",
        )
        opportunity = process_sync_event(sync_event)
        self.assertIsNotNone(opportunity)
        self.assertEqual(opportunity.stage, CrmOpportunity.STAGE_PAYMENT_PENDING)
        sync_event.refresh_from_db()
        self.assertEqual(sync_event.status, CrmSyncEvent.STATUS_PROCESSED)
        self.assertEqual(sync_event.attempts, 1)
