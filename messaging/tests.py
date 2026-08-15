import json
from importlib import import_module
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from customers.models import CrmOpportunity, Customer, CustomerActivity
from . import service
from .models import BaleUserBinding, MessagingContactGroup, MessagingSettings, OutboundMessage
from .providers.kavenegar import SendResult
from .providers.telegram import SendResult as TelegramSendResult

User = get_user_model()


class MessagingDomainMigrationTests(APITestCase):
    def test_only_legacy_site_base_url_is_migrated(self):
        cfg = MessagingSettings.load()
        cfg.site_base_url = "https://kavex.ir/"
        cfg.save(update_fields=["site_base_url"])

        migration = import_module(
            "messaging.migrations.0008_alter_messagingsettings_site_base_url"
        )

        class CurrentApps:
            @staticmethod
            def get_model(app_label, model_name):
                return MessagingSettings

        migration.migrate_site_base_url(CurrentApps(), None)
        cfg.refresh_from_db()
        self.assertEqual(cfg.site_base_url, "https://kavehmetal.com")

        cfg.site_base_url = "https://shop.example.com"
        cfg.save(update_fields=["site_base_url"])
        migration.migrate_site_base_url(CurrentApps(), None)
        cfg.refresh_from_db()
        self.assertEqual(cfg.site_base_url, "https://shop.example.com")


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
        self.assertIn(self.client.get("/api/messaging/bale-bindings/").status_code, (401, 403))
        self.assertIn(self.client.get("/api/messaging/groups/").status_code, (401, 403))
        self.assertIn(
            self.client.post(
                "/api/messaging/audience-preview/",
                {"all_active": True},
                format="json",
            ).status_code,
            (401, 403),
        )
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

    def test_single_send_rejects_unknown_channel(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/messaging/send/",
            {"customer_id": self.c1.id, "channel": "telegram", "message": "نباید ارسال شود"},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(OutboundMessage.objects.count(), 0)

    def test_bulk_send_to_segment(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post("/api/messaging/send-bulk/", {"stage": Customer.STAGE_PROPOSAL, "message": "تخفیف ویژه"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["total"], 2)  # فقط دو مشتریِ proposal
        self.assertEqual(OutboundMessage.objects.filter(purpose=OutboundMessage.PURPOSE_BULK).count(), 2)

    def test_group_import_normalizes_deduplicates_and_previews(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/messaging/groups/",
            {"name": "مشتریان ورق", "source": "kavenegar", "kavenegar_tag": "sheet-list"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        group_id = created.data["id"]

        replaced = self.client.post(
            f"/api/messaging/groups/{group_id}/replace-members/",
            {
                "customer_ids": [self.c1.id],
                "phones": "رضا, +989120000002\nتکراری, 09120000001\nشماره خراب",
            },
            format="json",
        )
        self.assertEqual(replaced.status_code, 200, replaced.data)
        self.assertEqual(replaced.data["import_summary"]["member_count"], 2)
        self.assertEqual(replaced.data["import_summary"]["duplicate_count"], 1)
        self.assertEqual(replaced.data["import_summary"]["invalid_count"], 1)

        preview = self.client.post(
            "/api/messaging/audience-preview/",
            {"group_ids": [group_id]},
            format="json",
        )
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data["valid_count"], 2)
        self.assertEqual(preview.data["source_counts"]["groups"], 2)
        self.assertEqual(OutboundMessage.objects.count(), 0)

    def test_product_audience_unites_interests_and_site_purchases(self):
        from products.models import Product, ProductCategory
        from sales.models import StoreOrder, StoreOrderItem, StoreOrderStatus

        root = ProductCategory.objects.create(name="خانواده مصرفی تست", code="consumer-test", product_kind="sheet")
        child = ProductCategory.objects.create(
            name="ورق گالوانیزه مصرفی تست",
            code="consumer-test-galvanized",
            parent=root,
            product_kind="sheet",
        )
        product = Product.objects.create(
            category=child,
            name="ورق گالوانیزه تست کمپین",
            short_description="تست",
            description="تست",
        )
        self.c1.product_interests.add(child)
        buyer = User.objects.create_user(username="campaign-buyer", password="pass")
        self.c2.user = buyer
        self.c2.save(update_fields=["user"])
        order = StoreOrder.objects.create(buyer=buyer, status=StoreOrderStatus.SUBMITTED)
        StoreOrderItem.objects.create(order=order, product=product, product_name=product.name)
        self.client.force_authenticate(self.admin)

        preview = self.client.post(
            "/api/messaging/audience-preview/",
            {"product_category_ids": [root.id]},
            format="json",
        )
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data["valid_count"], 2)
        self.assertEqual({item["customer_id"] for item in preview.data["sample"]}, {self.c1.id, self.c2.id})

        updated = self.client.patch(
            f"/api/crm/customers/{self.c3.id}/",
            {"product_interests": [child.id]},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["product_interests"], [child.id])
        self.assertEqual(updated.data["product_interest_details"][0]["code"], child.code)

    def test_sms_group_campaign_batches_with_kavenegar_tag(self):
        cfg = MessagingSettings.load()
        cfg.sms_enabled = True
        cfg.kavenegar_api_key = "TESTKEY"
        cfg.sender = "10004346"
        cfg.save()
        group = MessagingContactGroup.objects.create(
            name="گروه کمپین تست",
            source=MessagingContactGroup.SOURCE_KAVENEGAR,
            kavenegar_tag="campaign-test",
            created_by=self.admin,
        )
        service.replace_group_members(group, customer_ids=[self.c1.id, self.c2.id])
        self.client.force_authenticate(self.admin)
        provider_results = [
            SendResult(ok=True, status="sent", message_id="901", cost=100),
            SendResult(ok=True, status="sent", message_id="902", cost=100),
        ]

        with patch("messaging.service.kavenegar.send_sms_many", return_value=provider_results) as send_many:
            response = self.client.post(
                "/api/messaging/send-bulk/",
                {"group_ids": [group.id], "channel": "sms", "message": "لیست بار امروز"},
                format="json",
            )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["sent"], 2)
        self.assertEqual(response.data["total"], 2)
        send_many.assert_called_once()
        self.assertEqual(send_many.call_args.args[1], ["09120000001", "09120000002"])
        self.assertEqual(send_many.call_args.kwargs["tag"], "campaign-test")
        self.assertEqual(OutboundMessage.objects.filter(status=OutboundMessage.STATUS_SENT).count(), 2)

    def test_bale_group_campaign_uses_safir_for_each_unique_recipient(self):
        from messaging.providers.safir import SendResult as SafirResult

        cfg = MessagingSettings.load()
        cfg.safir_enabled = True
        cfg.safir_access_key = "SAFIR-TEST"
        cfg.safir_bot_id = "123"
        cfg.save()
        group = MessagingContactGroup.objects.create(name="گروه بله تست", created_by=self.admin)
        service.replace_group_members(group, customer_ids=[self.c1.id, self.c2.id])
        self.client.force_authenticate(self.admin)

        with patch(
            "messaging.service.safir.send_message",
            side_effect=[
                SafirResult(ok=True, status="sent", message_id="bale-1"),
                SafirResult(ok=True, status="sent", message_id="bale-2"),
            ],
        ) as send_bale:
            response = self.client.post(
                "/api/messaging/send-bulk/",
                {"group_ids": [group.id], "channel": "bale", "message": "لیست بار در بله"},
                format="json",
            )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["sent"], 2)
        self.assertEqual(send_bale.call_count, 2)
        self.assertEqual(
            OutboundMessage.objects.filter(
                channel=OutboundMessage.CHANNEL_BALE,
                status=OutboundMessage.STATUS_SENT,
            ).count(),
            2,
        )

    def test_sms_group_campaign_respects_daily_cap(self):
        cfg = MessagingSettings.load()
        cfg.sms_enabled = True
        cfg.kavenegar_api_key = "TESTKEY"
        cfg.daily_send_cap = 1
        cfg.save()
        OutboundMessage.objects.create(
            channel=OutboundMessage.CHANNEL_SMS,
            recipient="09120000009",
            body="ارسال قبلی",
            status=OutboundMessage.STATUS_SENT,
        )
        group = MessagingContactGroup.objects.create(name="گروه سقف روزانه", created_by=self.admin)
        service.replace_group_members(group, customer_ids=[self.c1.id, self.c2.id])
        self.client.force_authenticate(self.admin)

        with patch("messaging.service.kavenegar.send_sms_many") as send_many:
            response = self.client.post(
                "/api/messaging/send-bulk/",
                {"group_ids": [group.id], "channel": "sms", "message": "ارسال محدود"},
                format="json",
            )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["cap_limited"], 2)
        self.assertEqual(response.data["skipped"], 2)
        send_many.assert_not_called()

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

    def test_admin_configures_verified_bale_binding(self):
        self.client.force_authenticate(self.admin)
        eligible = self.client.get("/api/messaging/bale-bindings/eligible_users/")
        self.assertEqual(eligible.status_code, 200)
        self.assertIn(self.admin.pk, [row["id"] for row in eligible.data])
        self.assertNotIn(self.outsider.pk, [row["id"] for row in eligible.data])

        created = self.client.post(
            "/api/messaging/bale-bindings/",
            {"user": self.admin.pk, "bale_user_id": "554433", "display_name": "مدیر بله"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        binding = BaleUserBinding.objects.get(pk=created.data["id"])
        self.assertEqual(binding.verified_by, self.admin)
        self.assertEqual(binding.user, self.admin)

    def test_scoped_marketer_cannot_manage_bale_identity_bindings(self):
        from accounts.models import RoleCode, UserRole

        marketer = User.objects.create_user(username="binding-marketer", password="pass")
        UserRole.objects.create(user=marketer, role=RoleCode.MARKETER, is_active=True)
        self.client.force_authenticate(marketer)
        self.assertEqual(self.client.get("/api/messaging/bale-bindings/").status_code, 403)

    def test_connecting_bale_registers_webhook_and_command_menu(self):
        cfg = MessagingSettings.load()
        cfg.telegram_bot_token = "TOKEN"
        cfg.telegram_api_base = "https://tapi.bale.ai"
        cfg.save()
        self.client.force_authenticate(self.admin)

        ok = TelegramSendResult(ok=True, status="sent", raw={"ok": True})
        with patch("messaging.providers.telegram.set_webhook", return_value=ok) as set_webhook, \
             patch("messaging.providers.telegram.set_my_commands", return_value=ok) as set_commands, \
             patch("messaging.providers.telegram.get_webhook_info", return_value=ok):
            response = self.client.post(
                "/api/messaging/bale/set-webhook/",
                {"url": "https://kavehmetal.com/api/messaging/bale/webhook/secret/"},
                format="json",
            )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["commands_ok"])
        set_webhook.assert_called_once()
        commands = set_commands.call_args.args[1]
        self.assertIn("menu", [item["command"] for item in commands])

    def test_command_menu_failure_does_not_break_registered_webhook(self):
        cfg = MessagingSettings.load()
        cfg.telegram_bot_token = "TOKEN"
        cfg.telegram_api_base = "https://tapi.bale.ai"
        cfg.save()
        self.client.force_authenticate(self.admin)

        webhook_ok = TelegramSendResult(ok=True, status="sent", raw={"ok": True})
        commands_failed = TelegramSendResult(ok=False, status="failed", error="unsupported")
        with patch("messaging.providers.telegram.set_webhook", return_value=webhook_ok), \
             patch("messaging.providers.telegram.set_my_commands", return_value=commands_failed), \
             patch("messaging.providers.telegram.get_webhook_info", return_value=webhook_ok):
            response = self.client.post("/api/messaging/bale/set-webhook/", {}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["ok"])
        self.assertFalse(response.data["commands_ok"])
        self.assertEqual(response.data["commands_error"], "unsupported")

    def test_telegram_provider_serializes_command_menu(self):
        from .providers import telegram

        with patch("messaging.providers.telegram._call", return_value=TelegramSendResult(ok=True)) as call:
            telegram.set_my_commands(
                "TOKEN",
                [{"command": "/menu", "description": "منوی مدیریت"}],
                base_url="https://tapi.bale.ai",
            )

        self.assertEqual(call.call_args.args[1], "setMyCommands")
        payload = json.loads(call.call_args.args[2]["commands"])
        self.assertEqual(payload, [{"command": "menu", "description": "منوی مدیریت"}])


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

    def test_quote_request_uses_quote_title(self):
        from types import SimpleNamespace

        from messaging import events

        order = SimpleNamespace(
            pk="q1234", buyer=None, contact_phone="09120000004",
            contact_name="کارخانه", total_amount=0, items=None,
        )
        with patch("messaging.service.notify_admin") as mock_notify:
            events.on_order_submitted(order, needs_quote=True)
        self.assertTrue(
            Customer.objects.filter(phone="09120000004", source=Customer.SOURCE_STORE_PURCHASE).exists()
        )
        self.assertIn("استعلام", mock_notify.call_args.args[0])

    def test_chat_inquiry_notifies_even_without_phone(self):
        from types import SimpleNamespace

        from messaging import events

        conv = SimpleNamespace(lead_phone="", lead_name="", user=None)
        inquiry = SimpleNamespace(summary="۲۰ تن میلگرد ۱۴", contact_phone="", contact_name="")
        before = Customer.objects.count()
        with patch("messaging.service.notify_admin") as mock_notify:
            events.on_chat_inquiry(conv, inquiry)
        mock_notify.assert_called_once()
        self.assertEqual(Customer.objects.count(), before)  # بدون شماره ⇒ مشتری ساخته نمی‌شود

    def test_chat_inquiry_with_phone_creates_chat_lead(self):
        from types import SimpleNamespace

        from messaging import events

        conv = SimpleNamespace(lead_phone="09120000003", lead_name="علی", user=None)
        inquiry = SimpleNamespace(summary="ورق سیاه ۳ میل", contact_phone="09120000003", contact_name="علی")
        with patch("messaging.service.notify_admin"):
            events.on_chat_inquiry(conv, inquiry)
        self.assertTrue(
            Customer.objects.filter(phone="09120000003", source=Customer.SOURCE_CHAT).exists()
        )


class BaleTwoWayBotTests(APITestCase):
    """ربات دوطرفهٔ بله: امنیتِ وب‌هوک، دکمه‌های عملیاتیِ CRM، دستورها و ربات قیمت."""

    def setUp(self):
        self.cfg = MessagingSettings.load()
        self.cfg.telegram_enabled = True
        self.cfg.telegram_bot_token = "TOKEN"
        self.cfg.telegram_admin_chat_id = "-100"  # گروهِ ادمین
        self.cfg.bale_webhook_enabled = True
        self.cfg.save()
        self.operator = User.objects.create_user(username="bale-operator", password="pass", is_staff=True)
        self.reporter = User.objects.create_user(username="bale-reporter", password="pass", is_staff=True)
        BaleUserBinding.objects.create(user=self.operator, bale_user_id="555", display_name="علی")
        BaleUserBinding.objects.create(user=self.reporter, bale_user_id="5", display_name="گزارشگر")
        self.customer = Customer.objects.create(name="حسن", phone="09120000010")

    def test_webhook_rejects_wrong_secret(self):
        res = self.client.post("/api/messaging/bale/webhook/WRONG/", {"message": {"text": "سلام"}}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_callback_won_sets_stage_for_admin(self):
        update = {
            "callback_query": {
                "id": "cb1", "data": f"crm:won:{self.customer.id}",
                "from": {"id": 555, "first_name": "علی"},
                "message": {"chat": {"id": -100}},
            }
        }
        with patch("messaging.providers.telegram.answer_callback_query"), \
             patch("messaging.providers.telegram.send_message"):
            res = self.client.post(
                f"/api/messaging/bale/webhook/{self.cfg.webhook_secret}/", update, format="json"
            )
        self.assertEqual(res.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.stage, Customer.STAGE_WON)

    def test_callback_denied_for_non_admin(self):
        update = {
            "callback_query": {
                "id": "cb2", "data": f"crm:won:{self.customer.id}",
                "from": {"id": 999, "first_name": "غریبه"},
                "message": {"chat": {"id": 12345}},  # نه گروهِ ادمین، نه آیدیِ مجاز
            }
        }
        with patch("messaging.providers.telegram.answer_callback_query") as ack, \
             patch("messaging.providers.telegram.send_message"):
            self.client.post(f"/api/messaging/bale/webhook/{self.cfg.webhook_secret}/", update, format="json")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.stage, Customer.STAGE_NEW)  # تغییر نکرد
        ack.assert_called_once()

    def test_admin_group_does_not_authorize_unbound_member(self):
        update = {"message": {"text": "/قیف", "chat": {"id": -100}, "from": {"id": 999}}}
        with patch("messaging.providers.telegram.send_message") as send:
            self.client.post(f"/api/messaging/bale/webhook/{self.cfg.webhook_secret}/", update, format="json")
        text = send.call_args.args[2]
        self.assertNotIn("قیف مشتریان", text)
        self.assertIn("متصل نیست", text)
        self.assertIn("999", text)
        callback_data = [
            button["callback_data"]
            for row in send.call_args.kwargs["reply_markup"]["inline_keyboard"]
            for button in row
        ]
        self.assertIn("public:my_id", callback_data)
        self.assertNotIn("menu:funnel", callback_data)

    def test_bound_operator_receives_button_menu(self):
        update = {"message": {"text": "/menu", "chat": {"id": -100}, "from": {"id": 5}}}
        with patch("messaging.providers.telegram.send_message") as send:
            self.client.post(f"/api/messaging/bale/webhook/{self.cfg.webhook_secret}/", update, format="json")

        callback_data = [
            button["callback_data"]
            for row in send.call_args.kwargs["reply_markup"]["inline_keyboard"]
            for button in row
        ]
        self.assertIn("menu:today", callback_data)
        self.assertIn("menu:funnel", callback_data)
        self.assertIn("menu:opportunities", callback_data)

    def test_button_callback_opens_both_funnels_for_bound_operator(self):
        update = {
            "callback_query": {
                "id": "menu-funnel",
                "data": "menu:funnel",
                "from": {"id": 5},
                "message": {"chat": {"id": -100}},
            }
        }
        with patch("messaging.providers.telegram.answer_callback_query") as ack, \
             patch("messaging.providers.telegram.send_message") as send:
            self.client.post(f"/api/messaging/bale/webhook/{self.cfg.webhook_secret}/", update, format="json")

        ack.assert_called_once()
        self.assertIn("قیف مشتریان", send.call_args.args[2])
        self.assertIn("قیف فروش سایت", send.call_args.args[2])

    def test_public_user_can_get_own_bale_id_from_button(self):
        update = {
            "callback_query": {
                "id": "public-id",
                "data": "public:my_id",
                "from": {"id": 887766},
                "message": {"chat": {"id": 12345}},
            }
        }
        with patch("messaging.providers.telegram.answer_callback_query") as ack, \
             patch("messaging.providers.telegram.send_message") as send:
            self.client.post(f"/api/messaging/bale/webhook/{self.cfg.webhook_secret}/", update, format="json")

        ack.assert_called_once()
        self.assertIn("887766", send.call_args.args[2])

    def test_price_bot_replies_to_free_text(self):
        sample = {"products": [{"title": "میلگرد ۱۴", "price_toman": "100000", "url": "/products/1"}]}
        update = {"message": {"text": "میلگرد", "chat": {"id": 777}, "from": {"id": 777}}}
        with patch("assistant.tools.search_products", return_value=sample), \
             patch("messaging.providers.telegram.send_message") as send:
            self.client.post(f"/api/messaging/bale/webhook/{self.cfg.webhook_secret}/", update, format="json")
        send.assert_called_once()
        self.assertIn("میلگرد", send.call_args.args[2])

    def test_today_command_for_admin(self):
        update = {"message": {"text": "/امروز", "chat": {"id": -100}, "from": {"id": 5}}}
        with patch("messaging.providers.telegram.send_message") as send:
            self.client.post(f"/api/messaging/bale/webhook/{self.cfg.webhook_secret}/", update, format="json")
        send.assert_called_once()
        self.assertIn("امروز", send.call_args.args[2])

    def test_daily_digest_builder(self):
        from messaging.bale_bot import build_daily_digest

        title, lines = build_daily_digest()
        self.assertIn("امروز", title)
        self.assertTrue(any("سرنخ" in line for line in lines))

    def test_funnel_command_reports_customer_and_site_funnels(self):
        CrmOpportunity.objects.create(
            customer=self.customer,
            title="سفارش ورق CK45",
            stage=CrmOpportunity.STAGE_PRICING,
            expected_value_irr=90_000_000,
            probability=40,
        )
        update = {"message": {"text": "/قیف", "chat": {"id": -100}, "from": {"id": 5}}}
        with patch("messaging.providers.telegram.send_message") as send:
            self.client.post(f"/api/messaging/bale/webhook/{self.cfg.webhook_secret}/", update, format="json")
        text = send.call_args.args[2]
        self.assertIn("قیف مشتریان", text)
        self.assertIn("قیف فروش سایت", text)
        self.assertIn("قیمت‌گذاری", text)

    def test_opportunity_commands_read_live_site_data(self):
        opportunity = CrmOpportunity.objects.create(
            customer=self.customer,
            title="استعلام ورق ۱۰ میل",
            stage=CrmOpportunity.STAGE_QUOTE_SENT,
            source_type=CrmOpportunity.SOURCE_ASSISTANT_INQUIRY,
            source_id="991",
            source_status="quoted",
            expected_value_irr=50_000_000,
            probability=55,
        )
        updates = [
            {"message": {"text": "/فرصتها", "chat": {"id": -100}, "from": {"id": 5}}},
            {"message": {"text": f"/فرصت {opportunity.pk}", "chat": {"id": -100}, "from": {"id": 5}}},
        ]
        with patch("messaging.providers.telegram.send_message") as send:
            for update in updates:
                self.client.post(
                    f"/api/messaging/bale/webhook/{self.cfg.webhook_secret}/",
                    update,
                    format="json",
                )
        replies = [call.args[2] for call in send.call_args_list]
        self.assertIn("استعلام ورق ۱۰ میل", replies[0])
        self.assertIn(f"فرصت #{opportunity.pk}", replies[1])
        self.assertIn("پیشنهاد ارسال‌شده", replies[1])

    def test_opportunity_buttons_open_live_opportunity_card(self):
        opportunity = CrmOpportunity.objects.create(
            customer=self.customer,
            title="استعلام ورق CK45",
            stage=CrmOpportunity.STAGE_PRICING,
            expected_value_irr=70_000_000,
        )
        list_update = {
            "callback_query": {
                "id": "opp-list",
                "data": "menu:opportunities",
                "from": {"id": 5},
                "message": {"chat": {"id": -100}},
            }
        }
        detail_update = {
            "callback_query": {
                "id": "opp-detail",
                "data": f"opp:view:{opportunity.pk}",
                "from": {"id": 5},
                "message": {"chat": {"id": -100}},
            }
        }
        with patch("messaging.providers.telegram.answer_callback_query"), \
             patch("messaging.providers.telegram.send_message") as send:
            self.client.post(
                f"/api/messaging/bale/webhook/{self.cfg.webhook_secret}/",
                list_update,
                format="json",
            )
            self.client.post(
                f"/api/messaging/bale/webhook/{self.cfg.webhook_secret}/",
                detail_update,
                format="json",
            )

        list_buttons = send.call_args_list[0].kwargs["reply_markup"]["inline_keyboard"]
        list_callbacks = [button["callback_data"] for row in list_buttons for button in row]
        self.assertIn(f"opp:view:{opportunity.pk}", list_callbacks)
        self.assertIn(f"فرصت #{opportunity.pk}", send.call_args_list[1].args[2])
        detail_buttons = send.call_args_list[1].kwargs["reply_markup"]["inline_keyboard"]
        detail_callbacks = [button["callback_data"] for row in detail_buttons for button in row]
        self.assertIn("menu:opportunities", detail_callbacks)


class SafirBaleSendTests(APITestCase):
    """سفیر: تبدیلِ شماره، ارسالِ خشک، ارسالِ پیکربندی‌شده، و مسیریابیِ کانال در API."""

    def setUp(self):
        self.admin = User.objects.create_user(username="safir-admin", password="pass", is_staff=True)
        self.customer = Customer.objects.create(name="حسن", phone="09120000001")

    def test_phone_to_safir_format(self):
        from messaging.providers.safir import to_safir_phone

        self.assertEqual(to_safir_phone("09120000001"), "989120000001")
        self.assertEqual(to_safir_phone("989120000001"), "989120000001")
        self.assertEqual(to_safir_phone("9120000001"), "989120000001")
        self.assertEqual(to_safir_phone("bad"), "")

    def test_send_bale_dry_run_when_disabled(self):
        with patch("messaging.service.safir.send_message") as mock_send:
            msg = service.send_bale("09120000001", "سلام", customer=self.customer)
        mock_send.assert_not_called()
        self.assertEqual(msg.channel, OutboundMessage.CHANNEL_BALE)
        self.assertEqual(msg.status, OutboundMessage.STATUS_SKIPPED)

    def test_send_bale_when_configured(self):
        from messaging.providers.safir import SendResult as SafirResult

        cfg = MessagingSettings.load()
        cfg.safir_enabled = True
        cfg.safir_access_key = "KEY"
        cfg.safir_bot_id = "123456"
        cfg.save()
        with patch(
            "messaging.service.safir.send_message",
            return_value=SafirResult(ok=True, status="sent", message_id="abc"),
        ) as mock_send:
            msg = service.send_bale("09120000001", "سلام", customer=self.customer)
        mock_send.assert_called_once()
        # شماره باید به فرمتِ ۹۸ به سفیر برود.
        self.assertEqual(mock_send.call_args.args[2], "989120000001")
        self.assertEqual(msg.status, OutboundMessage.STATUS_SENT)
        self.assertEqual(msg.provider_message_id, "abc")

    def test_send_api_routes_to_bale_channel(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(
            "/api/messaging/send/",
            {"customer_id": self.customer.id, "message": "سلام بله", "channel": "bale"},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["channel"], OutboundMessage.CHANNEL_BALE)
