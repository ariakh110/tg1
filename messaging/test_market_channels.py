from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from products.models import CommodityExchangeTrade
from .models import MarketChannelDraft, MarketChannelPublication, MessagingSettings, OutboundMessage
from .market_channels import BotRejected


class MarketChannelTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user("publisher", password="pass", is_staff=True)
        self.client.force_authenticate(self.admin)
        self.date = timezone.localdate()
        self.trade = CommodityExchangeTrade.objects.create(
            source_report_id=1, symbol="BLOOM-130-3SP", goods_name="شمش بلوم (130*130)3SP",
            product_group="شمش و اسلب", producer_name="فولاد نمونه", contract_type="سلف",
            base_price="1000", weighted_price="1200", offered_volume="100", demand_volume="150",
            traded_volume="80", unit="تن", currency="ریال", trade_date=self.date,
            trade_date_jalali="1405/07/29", delivery_date_jalali="1405/08/04", raw={"arzehPk": "100"},
        )
        self.cfg = MessagingSettings.load()
        self.cfg.market_telegram_bot_token = "telegram-secret"
        self.cfg.market_bale_bot_token = "bale-secret"
        self.cfg.save()

    def generate(self, **extra):
        response = self.client.post("/api/messaging/market-drafts/", {"date": str(self.date), **extra}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["results"]

    def publish(self, draft, platforms=None):
        return self.client.post(f"/api/messaging/market-drafts/{draft['id']}/publish/",
                                {"platforms": platforms or ["telegram", "bale"]}, format="json")

    @patch("messaging.market_channels.bot_send", return_value="42")
    def test_preview_is_branded_secret_free_and_does_not_send(self, send):
        draft = self.generate()[0]
        self.assertIn("کاوه‌متال", draft["texts"]["telegram"])
        self.assertIn("https://t.me/kavehmetal", draft["texts"]["telegram"])
        self.assertIn("https://ble.ir/kavehmetal", draft["texts"]["bale"])
        self.assertIn("3SP", draft["texts"]["bale"])
        self.assertIn("۲۰.۰۰٪", draft["texts"]["telegram"])
        self.assertNotIn("Spad", str(draft))
        self.assertNotIn("telegram-secret", str(draft))
        self.assertNotIn("bale-secret", str(self.client.get("/api/messaging/settings/").data))
        send.assert_not_called()
        self.assertEqual(self.generate()[0]["id"], draft["id"])
        self.assertEqual(MarketChannelDraft.objects.count(), 1)

    @patch("messaging.market_channels.bot_send", return_value="42")
    def test_explicit_publish_targets_both_channels_once(self, send):
        draft = self.generate()[0]
        response = self.publish(draft)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(send.call_count, 2)
        self.assertEqual(send.call_args_list[0].args[2], "@kavehmetal")
        self.assertIn("telegram-secret", send.call_args_list[0].args)
        self.assertIn("bale-secret", send.call_args_list[1].args)
        self.publish(draft)
        self.assertEqual(send.call_count, 2)
        self.assertEqual(MarketChannelPublication.objects.count(), 2)
        self.assertEqual(OutboundMessage.objects.filter(status="sent").count(), 2)

    @patch("messaging.market_channels.bot_send", side_effect=TimeoutError("secret-in-url"))
    def test_uncertain_delivery_is_logged_without_secret_or_automatic_retry(self, send):
        draft = self.generate()[0]
        response = self.publish(draft, ["telegram"])
        self.assertEqual(response.data["publications"]["telegram"]["status"], "queued")
        self.assertNotIn("secret-in-url", str(response.data))
        self.publish(draft, ["telegram"])
        self.assertEqual(send.call_count, 1)

    @patch("messaging.market_channels.bot_send", side_effect=BotRejected("rejected"))
    def test_rejected_send_is_reported_as_failed(self, send):
        response = self.publish(self.generate()[0], ["bale"])
        self.assertEqual(response.data["publications"]["bale"]["status"], "failed")

    def test_missing_configuration_fails_before_any_publication(self):
        self.cfg.market_bale_bot_token = ""
        self.cfg.save()
        response = self.publish(self.generate()[0])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(MarketChannelPublication.objects.count(), 0)

    def test_daily_filter_vat_and_deduplicated_offer_volume(self):
        self.cfg.market_vat_percent = Decimal("10")
        self.cfg.save()
        CommodityExchangeTrade.objects.create(
            source_report_id=2, symbol=self.trade.symbol, goods_name=self.trade.goods_name,
            product_group=self.trade.product_group, producer_name=self.trade.producer_name,
            contract_type="سلف", delivery_date_jalali=self.trade.delivery_date_jalali,
            base_price="1000", weighted_price="1300", offered_volume="100", demand_volume="150",
            traded_volume="20", unit="تن", currency="ریال", trade_date=self.date,
            trade_date_jalali="1405/07/29", raw={"arzehPk": "100"},
        )
        draft = self.generate()[0]
        self.assertIn("حجم عرضه: ۱۰۰ تن", draft["texts"]["telegram"])
        self.assertIn("نرخ پایه: ۱,۱۰۰ ریال", draft["texts"]["telegram"])
        self.assertIn("نرخ میانگین معامله: ۱,۳۴۲ ریال", draft["texts"]["telegram"])
        self.assertIn("۲۲.۰۰٪", draft["texts"]["telegram"])
        summary = self.generate(kind="summary")[0]
        self.assertIn("تعداد نمادها: ۱", summary["texts"]["telegram"])
        response = self.client.post("/api/messaging/market-drafts/", {"date": str(self.date - timedelta(days=1))}, format="json")
        self.assertEqual(response.data["results"], [])

    def test_non_admin_cannot_generate_or_publish(self):
        draft = self.generate()[0]
        user = get_user_model().objects.create_user("ordinary", password="pass")
        self.client.force_authenticate(user)
        self.assertEqual(self.client.post("/api/messaging/market-drafts/", {"date": str(self.date)}, format="json").status_code, 403)
        self.assertEqual(self.publish(draft).status_code, 403)

    @patch("messaging.market_channels.bot_send")
    def test_only_confirmed_failure_allows_explicit_retry(self, send):
        send.side_effect = BotRejected("rejected")
        draft = self.generate()[0]
        self.publish(draft, ["telegram"])
        send.side_effect = None
        send.return_value = "confirmed"
        response = self.client.post(f"/api/messaging/market-drafts/{draft['id']}/publish/",
            {"platforms": ["telegram"], "retry_failed": True}, format="json")
        self.assertEqual(response.data["publications"]["telegram"]["status"], "sent")
        self.assertEqual(send.call_count, 2)
        self.assertEqual(MarketChannelPublication.objects.count(), 1)


    def test_mtproto_settings_hide_hash_preserve_blank_and_validate_links(self):
        response = self.client.patch("/api/messaging/settings/", {
            "market_telegram_transport": "mtproto", "market_telegram_api_id": 123,
            "market_telegram_api_hash": "a" * 32,
            "market_telegram_proxies": ["tg://proxy?server=proxy.example.com&port=443&secret=" + "ab" * 16],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["market_telegram_api_hash_configured"])
        self.assertNotIn("market_telegram_api_hash", response.data)
        self.client.patch("/api/messaging/settings/", {"market_telegram_api_hash": ""}, format="json")
        self.cfg.refresh_from_db()
        self.assertEqual(self.cfg.market_telegram_api_hash, "a" * 32)
        bad = self.client.patch("/api/messaging/settings/", {"market_telegram_proxies": ["http://localhost"]}, format="json")
        self.assertEqual(bad.status_code, 400)

    @patch("messaging.telegram_transport.test_mtproto", return_value={"ok": True, "detail": "connected"})
    def test_proxy_connection_test_is_admin_only_and_never_publishes(self, test):
        response = self.client.post("/api/messaging/market-telegram/test/", {"index": 0}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(OutboundMessage.objects.count(), 0)
        self.client.force_authenticate(get_user_model().objects.create_user("no-access", password="pass"))
        self.assertEqual(self.client.post("/api/messaging/market-telegram/test/", {}, format="json").status_code, 403)

    @patch("messaging.telegram_transport.send_mtproto", return_value="123")
    @patch("messaging.market_channels.bot_send", return_value="456")
    def test_mtproto_telegram_keeps_bale_https(self, https, mtproto):
        self.cfg.market_telegram_transport = "mtproto"
        self.cfg.market_telegram_api_id = 123
        self.cfg.market_telegram_api_hash = "a" * 32
        self.cfg.market_telegram_proxies = ["tg://proxy?server=proxy.example.com&port=443&secret=" + "ab" * 16]
        self.cfg.save()
        response = self.publish(self.generate()[0])
        self.assertEqual(response.data["publications"]["telegram"]["status"], "sent")
        self.assertEqual(response.data["publications"]["bale"]["status"], "sent")
        mtproto.assert_called_once()
        https.assert_called_once()
        self.assertEqual(https.call_args.args[0], "bale")


    @patch("messaging.market_channels.bot_send", side_effect=TimeoutError())
    def test_only_explicit_admin_review_can_release_completed_uncertainty(self, send):
        draft = self.generate()[0]
        self.publish(draft, ["telegram"])
        url = f"/api/messaging/market-drafts/{draft['id']}/resolve/"
        self.assertEqual(self.client.post(url, {"platform": "telegram"}, format="json").status_code, 400)
        response = self.client.post(url, {"platform": "telegram", "confirm_not_delivered": True}, format="json")
        self.assertEqual(response.data["publications"]["telegram"]["status"], "failed")
        self.assertEqual(send.call_count, 1)
        self.assertEqual(OutboundMessage.objects.get().meta["not_delivered_confirmed_by"], self.admin.pk)

    def test_review_cannot_release_active_claim_or_sent_message(self):
        from .market_channels import generate_drafts
        draft = generate_drafts(self.date, actor=self.admin)[0]
        outbound = OutboundMessage.objects.create(channel="telegram", provider="telegram_bot", recipient="@kavehmetal", body="x", status="queued")
        MarketChannelPublication.objects.create(draft=draft, platform="telegram", outbound=outbound)
        url = f"/api/messaging/market-drafts/{draft.id}/resolve/"
        body = {"platform": "telegram", "confirm_not_delivered": True}
        self.assertEqual(self.client.post(url, body, format="json").status_code, 400)
        outbound.status = "sent"
        outbound.save()
        self.assertEqual(self.client.post(url, body, format="json").status_code, 400)
