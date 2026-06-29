from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from customers.models import Customer, CustomerActivity
from . import service
from .models import MessagingSettings, OutboundMessage
from .providers.kavenegar import SendResult

User = get_user_model()


class PhoneNormalizationTests(APITestCase):
    def test_iranian_forms_normalize_to_09(self):
        for raw in ["09120000001", "+989120000001", "00989120000001", "989120000001", "9120000001", "0912 000 0001"]:
            self.assertEqual(service.normalize_phone(raw), "09120000001", raw)


class DryRunTests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="حسن رضایی", phone="09120000001")

    def test_disabled_settings_skip_without_contacting_provider(self):
        with patch("messaging.service.kavenegar.send_sms") as mock_send:
            msg = service.send_to_customer(self.customer, "سلام، قیمت میلگرد آماده است.")
        mock_send.assert_not_called()
        self.assertEqual(msg.status, OutboundMessage.STATUS_SKIPPED)
        self.assertEqual(msg.recipient, "09120000001")
        # حتی در حالتِ خشک، تماسِ خروجی روی تایم‌لاینِ مشتری ثبت می‌شود.
        self.assertTrue(
            CustomerActivity.objects.filter(customer=self.customer, kind=CustomerActivity.KIND_MESSAGE).exists()
        )

    def test_configured_send_records_provider_result(self):
        cfg = MessagingSettings.load()
        cfg.sms_enabled = True
        cfg.kavenegar_api_key = "TESTKEY"
        cfg.save()
        with patch(
            "messaging.service.kavenegar.send_sms",
            return_value=SendResult(ok=True, status="sent", message_id="555", cost=120),
        ) as mock_send:
            msg = service.send_to_customer(self.customer, "متن تست")
        mock_send.assert_called_once()
        self.assertEqual(msg.status, OutboundMessage.STATUS_SENT)
        self.assertEqual(msg.provider_message_id, "555")
        self.assertEqual(msg.cost, 120)


class MessagingApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="msg-admin", password="pass", is_staff=True)
        self.outsider = User.objects.create_user(username="msg-outsider", password="pass")
        self.c1 = Customer.objects.create(name="حسن", phone="09120000001", stage=Customer.STAGE_PROPOSAL)
        self.c2 = Customer.objects.create(name="رضا", phone="09120000002", stage=Customer.STAGE_PROPOSAL)
        self.c3 = Customer.objects.create(name="مریم", phone="09120000003", stage=Customer.STAGE_NEW)

    def test_non_admin_denied(self):
        self.client.force_authenticate(self.outsider)
        self.assertIn(self.client.get("/api/messaging/settings/").status_code, (401, 403))
        self.assertIn(self.client.get("/api/messaging/messages/").status_code, (401, 403))
        self.assertIn(self.client.post("/api/messaging/send/", {"recipient": "09120000001", "message": "x"}, format="json").status_code, (401, 403))

    def test_settings_key_is_write_only(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch("/api/messaging/settings/", {"kavenegar_api_key": "SECRET123", "sms_enabled": True}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertNotIn("kavenegar_api_key", res.data)
        self.assertTrue(res.data["api_key_configured"])
        # ارسالِ بدونِ کلید نباید کلیدِ ذخیره‌شده را پاک کند.
        res2 = self.client.patch("/api/messaging/settings/", {"sender": "10004346"}, format="json")
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(MessagingSettings.load().kavenegar_api_key, "SECRET123")

    def test_single_send_logs_message_and_activity(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post("/api/messaging/send/", {"customer_id": self.c1.id, "message": "قیمت امروز آماده است."}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["customer"], self.c1.id)
        self.assertEqual(OutboundMessage.objects.filter(customer=self.c1).count(), 1)
        self.assertTrue(CustomerActivity.objects.filter(customer=self.c1, kind=CustomerActivity.KIND_MESSAGE).exists())

    def test_bulk_send_to_segment(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post("/api/messaging/send-bulk/", {"stage": Customer.STAGE_PROPOSAL, "message": "تخفیف ویژه"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["total"], 2)  # فقط دو مشتریِ proposal
        self.assertEqual(OutboundMessage.objects.filter(purpose=OutboundMessage.PURPOSE_BULK).count(), 2)

    def test_notify_step_records_order_status(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post("/api/messaging/notify-step/", {"customer_id": self.c1.id, "step": "shipped", "order_no": "1024"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["purpose"], OutboundMessage.PURPOSE_ORDER_STATUS)
        self.assertIn("ارسال شد", res.data["body"])
        self.assertIn("1024", res.data["body"])

    def test_notify_step_rejects_invalid_step(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post("/api/messaging/notify-step/", {"customer_id": self.c1.id, "step": "nope"}, format="json")
        self.assertEqual(res.status_code, 400)


class WebhookTests(APITestCase):
    def setUp(self):
        self.secret = MessagingSettings.load().webhook_secret
        self.customer = Customer.objects.create(name="حسن", phone="09120000001")

    def test_status_callback_updates_message(self):
        msg = OutboundMessage.objects.create(
            channel=OutboundMessage.CHANNEL_SMS, recipient="09120000001",
            provider_message_id="999", status=OutboundMessage.STATUS_SENT,
        )
        res = self.client.get(f"/api/messaging/kavenegar/status/{self.secret}/?messageid=999&status=10")
        self.assertEqual(res.status_code, 200)
        msg.refresh_from_db()
        self.assertEqual(msg.status, OutboundMessage.STATUS_DELIVERED)

    def test_status_callback_bad_secret_forbidden(self):
        res = self.client.get("/api/messaging/kavenegar/status/wrong-secret/?messageid=999&status=10")
        self.assertEqual(res.status_code, 403)

    def test_incoming_callback_logs_activity_for_known_customer(self):
        res = self.client.get(
            f"/api/messaging/kavenegar/incoming/{self.secret}/",
            {"from": "09120000001", "to": "10004346", "message": "قیمت میلگرد؟", "messageId": "5"},
        )
        self.assertEqual(res.status_code, 200)
        act = CustomerActivity.objects.filter(customer=self.customer, kind=CustomerActivity.KIND_MESSAGE).first()
        self.assertIsNotNone(act)
        self.assertIn("قیمت میلگرد؟", act.body)

    def test_incoming_callback_unknown_sender_is_ignored(self):
        res = self.client.get(
            f"/api/messaging/kavenegar/incoming/{self.secret}/",
            {"from": "09129999999", "message": "سلام"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(CustomerActivity.objects.count(), 0)


class LeadIntakeAndAdminAlertTests(APITestCase):
    """ورودِ خودکارِ سرنخ (ثبت‌نام/خرید/چت) + اطلاع‌رسانیِ ادمین (تلگرام/پیامک)."""

    def test_upsert_lead_is_idempotent_by_phone_and_keeps_source(self):
        from customers.services import upsert_lead

        c1, created1 = upsert_lead("0912 000 0000", name="حسن", source=Customer.SOURCE_CHAT)
        self.assertTrue(created1)
        self.assertEqual(c1.phone, "09120000000")
        # همان شماره با شکلِ دیگر ⇒ همان مشتری؛ منبعِ قبلی بازنویسی نمی‌شود.
        c2, created2 = upsert_lead("989120000000", name="حسن رضایی", source=Customer.SOURCE_OTHER)
        self.assertFalse(created2)
        self.assertEqual(c1.pk, c2.pk)
        self.assertEqual(c2.source, Customer.SOURCE_CHAT)

    def test_upsert_lead_rejects_blank_phone(self):
        from customers.services import upsert_lead

        customer, created = upsert_lead("", name="x")
        self.assertIsNone(customer)
        self.assertFalse(created)

    def test_notify_admin_dry_run_logs_skipped(self):
        msgs = service.notify_admin("تست", ["خط ۱"])
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].status, OutboundMessage.STATUS_SKIPPED)
        self.assertEqual(msgs[0].purpose, OutboundMessage.PURPOSE_ADMIN_ALERT)

    def test_notify_admin_sends_to_each_telegram_chat(self):
        from messaging.providers.telegram import SendResult as TgResult

        cfg = MessagingSettings.load()
        cfg.telegram_enabled = True
        cfg.telegram_bot_token = "TOKEN"
        cfg.telegram_admin_chat_id = "111, 222"
        cfg.telegram_api_base = "https://tg.example.com"
        cfg.save()
        with patch(
            "messaging.service.telegram.send_message",
            return_value=TgResult(ok=True, status="sent", message_id="9"),
        ) as mock_tg:
            msgs = service.notify_admin("تست", ["x"])
        self.assertEqual(mock_tg.call_count, 2)
        self.assertEqual(len(msgs), 2)
        self.assertTrue(all(m.channel == OutboundMessage.CHANNEL_TELEGRAM for m in msgs))
        self.assertTrue(all(m.status == OutboundMessage.STATUS_SENT for m in msgs))
        # واسطِ قابل‌تنظیم (برای سرورِ ایران) باید به provider منتقل شود.
        self.assertEqual(mock_tg.call_args.kwargs.get("base_url"), "https://tg.example.com")

    def test_signup_event_creates_website_lead_and_notifies(self):
        from messaging import events

        user = User.objects.create_user(username="buyer1", password="x")
        with patch("messaging.service.notify_admin") as mock_notify:
            events.on_user_signup(user, phone="09120000001")
        self.assertTrue(
            Customer.objects.filter(phone="09120000001", source=Customer.SOURCE_WEBSITE).exists()
        )
        mock_notify.assert_called_once()

    def test_order_event_creates_store_purchase_lead(self):
        from types import SimpleNamespace

        from messaging import events

        order = SimpleNamespace(
            pk="abcd1234", buyer=None, contact_phone="09120000002",
            contact_name="کارخانهٔ فولاد", total_amount=50000000, items=None,
        )
        with patch("messaging.service.notify_admin"):
            events.on_order_submitted(order)
        self.assertTrue(
            Customer.objects.filter(phone="09120000002", source=Customer.SOURCE_STORE_PURCHASE).exists()
        )
