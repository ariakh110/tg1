from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from core.models import SiteSettings
from .models import CommodityExchangeTrade, MarketDataSyncState
from . import tasks


class MarketRefreshTests(APITestCase):
    def test_admin_can_configure_commodity_and_global_automatic_mode(self):
        self.client.force_authenticate(get_user_model().objects.create_user('market-admin', is_staff=True))
        response = self.client.patch('/api/site-settings/', {
            'commodity_exchange': {'auto_refresh': False, 'refresh_minutes': 45},
            'global_metals': {'auto_refresh': False},
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['commodity_exchange'], {'auto_refresh': False, 'refresh_minutes': 45})
        self.assertFalse(response.data['global_metals']['auto_refresh'])
        self.assertEqual(self.client.patch('/api/site-settings/', {'commodity_exchange': {'refresh_minutes': True}}, format='json').status_code, 400)

    @patch('products.tasks.sync_ime_market', return_value=3)
    def test_automatic_refresh_respects_mode_interval_and_lease(self, sync):
        config = SiteSettings.load()
        config.ime_auto_refresh = False
        config.save()
        tasks.sync_ime_market_task()
        sync.assert_not_called()
        config.ime_auto_refresh = True
        config.save()
        tasks.sync_ime_market_task()
        sync.assert_called_once()
        tasks.sync_ime_market_task()
        sync.assert_called_once()

    @patch('products.tasks.sync_ime_market', return_value=3)
    def test_manual_refresh_requires_admin_and_bypasses_automatic_mode(self, sync):
        self.assertIn(self.client.post('/api/admin/commodity-exchange/sync/').status_code, (401, 403))
        config = SiteSettings.load()
        config.ime_auto_refresh = False
        config.save()
        self.client.force_authenticate(get_user_model().objects.create_user('sync-admin', is_staff=True))
        response = self.client.post('/api/admin/commodity-exchange/sync/')
        self.assertEqual(response.status_code, 200, response.data)
        sync.assert_called_once()

    def test_daily_summary_never_relabels_old_trades_as_today(self):
        old = timezone.localdate() - timedelta(days=3)
        CommodityExchangeTrade.objects.create(source_report_id=17, symbol='A', goods_name='sheet',
            product_group='sheet', trade_date=old, trade_date_jalali='1405/07/29')
        response = self.client.get('/api/commodity-exchange/summary/')
        self.assertFalse(response.data['has_today_data'])
        self.assertEqual(response.data['latest_trade_date'], old.isoformat())
        self.assertEqual(response.data['available_dates'][0]['date'], old.isoformat())
        today = self.client.get('/api/commodity-exchange/summary/', {'date': timezone.localdate().isoformat()})
        self.assertEqual(today.data['records'], 0)
        self.assertEqual(today.data['selected_date'], timezone.localdate().isoformat())
        self.assertEqual(self.client.get('/api/commodity-exchange/summary/?date=broken').status_code, 400)

    @patch('products.tasks.sync_ime_market', side_effect=RuntimeError('private upstream URL'))
    def test_failed_run_releases_lease_and_records_safe_error(self, sync):
        with self.assertRaises(Exception):
            tasks.sync_ime_market_task()
        state = MarketDataSyncState.objects.get(key='ime')
        self.assertEqual(state.status, 'error')
        self.assertNotIn('private upstream URL', state.error_message)

