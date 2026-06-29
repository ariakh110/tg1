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
