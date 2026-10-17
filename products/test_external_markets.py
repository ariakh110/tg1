from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .external_markets import (
    MarketSyncError,
    gregorian_to_jalali,
    import_global_metals_csv,
    sync_global_metals,
    sync_ime_market,
)
from .models import (
    CommodityExchangeTrade,
    GlobalMetalInstrument,
    GlobalMetalObservation,
    MarketDataSyncState,
)


class ExternalMarketSyncTests(APITestCase):
    def ime_row(self, report_id=1001, price="525000"):
        published_date = timezone.localdate().isoformat().replace("-", "/")
        return {
            "xTalarReportPK": report_id,
            "GoodsName": "میلگرد 14 A3",
            "Symbol": "M-A3-14",
            "ProducerName": "فولاد نمونه",
            "ContractType": "نقدی",
            "MinPrice": "510000",
            "Price": price,
            "MaxPrice": "530000",
            "arze": "1000",
            "ArzeBasePrice": "500000",
            "taghaza": "1400",
            "Quantity": "800",
            "TotalPrice": "420000000",
            "date": published_date,
            "DeliveryDate": published_date,
            "Currency": "ریال",
            "Unit": "کیلوگرم",
            "Talar": "تالار صنعتی",
        }

    @patch("products.external_markets._post_json")
    def test_ime_sync_is_filtered_and_idempotent(self, post_json):
        post_json.return_value = {
            "d": [
                self.ime_row(),
                {**self.ime_row(1002), "GoodsName": "پلی اتیلن", "Symbol": "PET"},
            ]
        }

        first = sync_ime_market()
        post_json.return_value = {"d": [self.ime_row(price="535000")]}
        second = sync_ime_market()

        self.assertEqual((first, second), (1, 1))
        self.assertEqual(CommodityExchangeTrade.objects.count(), 1)
        trade = CommodityExchangeTrade.objects.get()
        self.assertEqual(str(trade.weighted_price), "535000.00")
        self.assertEqual(trade.currency, "ریال")
        self.assertEqual(trade.unit, "کیلوگرم")

    @patch("products.external_markets._post_json", side_effect=MarketSyncError("upstream failed"))
    def test_ime_failure_preserves_last_good_rows_and_health(self, _post_json):
        CommodityExchangeTrade.objects.create(
            source_report_id=7,
            symbol="OLD",
            goods_name="ورق فولادی",
            product_group="ورق و کلاف",
            trade_date=timezone.localdate(),
            trade_date_jalali=gregorian_to_jalali(timezone.localdate()),
        )
        with self.assertRaises(MarketSyncError):
            sync_ime_market()
        self.assertTrue(CommodityExchangeTrade.objects.filter(source_report_id=7).exists())
        self.assertEqual(MarketDataSyncState.objects.get(key="ime").status, "error")

    @override_settings(METALS_DEV_API_KEY="server-secret")
    @patch("products.external_markets._get_json")
    def test_global_provider_parsing_is_idempotent_and_secret_is_not_stored(self, get_json):
        get_json.return_value = {
            "timestamp": timezone.now().isoformat(),
            "metals": {"lme_copper": "9300.25", "lme_zinc": "2780.5"},
        }
        self.assertEqual(sync_global_metals(force=True), 2)
        get_json.return_value["metals"]["lme_copper"] = "9400"
        self.assertEqual(sync_global_metals(force=True), 2)
        self.assertEqual(GlobalMetalObservation.objects.count(), 2)
        self.assertEqual(str(GlobalMetalObservation.objects.get(instrument__code="copper").price), "9400.000000")
        self.assertNotIn("server-secret", str(GlobalMetalObservation.objects.values("raw", "source_url")))

    def test_csv_import_validates_source_and_upserts(self):
        header = "instrument_code,name_fa,name_en,price,currency,unit,exchange,observed_at,provider,source_url\n"
        row = "hrc,ورق گرم,HRC,620,USD,metric_ton,FOB Black Sea,2026-10-17T08:00:00+00:00,Licensed CSV,https://example.com/source\n"
        self.assertEqual(import_global_metals_csv(header + row), 1)
        self.assertEqual(import_global_metals_csv(header + row.replace("620", "625")), 1)
        self.assertEqual(GlobalMetalObservation.objects.count(), 1)
        self.assertEqual(str(GlobalMetalObservation.objects.get().price), "625.000000")
        with self.assertRaises(MarketSyncError):
            import_global_metals_csv(header + row.replace("https://example.com/source", "javascript:bad"))

    @override_settings(METALS_DEV_API_KEY="")
    def test_missing_provider_key_sets_an_explicit_unavailable_state(self):
        self.assertEqual(sync_global_metals(), 0)
        state = MarketDataSyncState.objects.get(key="metals_dev")
        self.assertEqual(state.status, MarketDataSyncState.Status.ERROR)
        self.assertIn("کلید API", state.error_message)


class ExternalMarketAPITests(APITestCase):
    def setUp(self):
        today = timezone.localdate()
        self.trade = CommodityExchangeTrade.objects.create(
            source_report_id=10,
            symbol="REB-14",
            goods_name="میلگرد ۱۴",
            product_group="میلگرد",
            producer_name="فولاد نمونه",
            weighted_price="525000",
            offered_volume="1000",
            demand_volume="1200",
            traded_volume="800",
            currency="ریال",
            unit="کیلوگرم",
            trade_date=today,
            trade_date_jalali=gregorian_to_jalali(today),
        )
        self.instrument = GlobalMetalInstrument.objects.create(
            code="copper", name_fa="مس", name_en="Copper", exchange="LME"
        )
        for offset, price in ((1, "9000"), (0, "9180")):
            observed_at = timezone.now() - timedelta(days=offset)
            GlobalMetalObservation.objects.create(
                instrument=self.instrument,
                provider="Test Provider",
                price=price,
                observed_at=observed_at,
                observed_on=timezone.localdate() - timedelta(days=offset),
                source_url="https://example.com/market",
            )

    def test_ime_summary_filters_and_history(self):
        summary = self.client.get("/api/commodity-exchange/summary/")
        listing = self.client.get("/api/commodity-exchange/trades/", {"search": "نمونه"})
        history = self.client.get("/api/commodity-exchange/symbols/REB-14/history/", {"range": "30d"})
        self.assertEqual(summary.status_code, status.HTTP_200_OK)
        self.assertEqual(summary.data["records"], 1)
        self.assertEqual(summary.data["totals"]["traded_volume"], "800")
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(history.data["points"][0]["currency"], "ریال")

    @override_settings(METALS_DEV_API_KEY="server-secret")
    def test_global_summary_calculates_change_without_exposing_secret(self):
        response = self.client.get("/api/global-metals/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["instruments"][0]["percent_change"], "2.00")
        self.assertFalse(response.data["instruments"][0]["is_stale"])
        self.assertNotIn("server-secret", str(response.data))

    def test_csv_import_requires_staff_and_accepts_valid_file(self):
        csv_data = (
            "instrument_code,name_fa,name_en,price,currency,unit,exchange,observed_at,provider,source_url\n"
            "billet,شمش,Billet,510,USD,metric_ton,FOB,2026-10-17T08:00:00+00:00,Licensed,https://example.com/feed\n"
        )
        denied = self.client.post("/api/admin/global-metals/import/", {"file": self._upload(csv_data)})
        self.assertEqual(denied.status_code, status.HTTP_401_UNAUTHORIZED)
        user = get_user_model().objects.create_user("market-admin", password="pass", is_staff=True)
        self.client.force_authenticate(user)
        accepted = self.client.post("/api/admin/global-metals/import/", {"file": self._upload(csv_data)})
        self.assertEqual(accepted.status_code, status.HTTP_201_CREATED, accepted.data)
        self.assertEqual(accepted.data["imported"], 1)

    @patch("products.external_markets._get_json")
    def test_admin_can_force_global_metals_sync_with_panel_key(self, get_json):
        from core.models import SiteSettings

        config = SiteSettings.load()
        config.global_metals_api_key = "panel-secret"
        config.save()
        get_json.return_value = {
            "timestamp": timezone.now().isoformat(),
            "metals": {"lme_copper": "9345.50"},
        }
        user = get_user_model().objects.create_user("sync-admin", password="pass", is_staff=True)
        self.client.force_authenticate(user)

        response = self.client.post("/api/admin/global-metals/sync/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["synchronized"], 1)
        self.assertNotIn("panel-secret", str(response.data))

    @staticmethod
    def _upload(content):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile("metals.csv", content.encode("utf-8"), content_type="text/csv")
