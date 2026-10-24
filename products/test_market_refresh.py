from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.management import call_command, CommandError
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

    @patch('products.tasks.sync_ime_market')
    def test_active_lease_blocks_even_manual_run_and_expired_lease_recovers(self, sync):
        state = MarketDataSyncState.objects.create(key='ime', lease_until=timezone.now() + timedelta(minutes=1))
        self.assertIn('skipped', tasks.refresh_market('ime', force=True))
        sync.assert_not_called()
        state.lease_until = timezone.now() - timedelta(seconds=1)
        state.save()
        sync.return_value = 1
        self.assertEqual(tasks.refresh_market('ime', force=True)['synchronized'], 1)

    @patch('products.tasks.sync_global_metals', return_value=5)
    def test_global_manual_mode_and_interval(self, sync):
        config = SiteSettings.load()
        config.global_metals_auto_refresh = False
        config.save()
        tasks.sync_global_metals_task()
        sync.assert_not_called()
        tasks.refresh_market('metals_dev', force=True)
        sync.assert_called_once_with(force=True)
        config.global_metals_auto_refresh = True
        config.save()
        tasks.sync_global_metals_task()
        sync.assert_called_once()

    @patch('products.tasks.sync_ime_market', side_effect=RuntimeError('internal'))
    def test_failure_preserves_last_success_and_throttles_retry(self, sync):
        previous = timezone.now() - timedelta(days=2)
        MarketDataSyncState.objects.create(key='ime', last_success_at=previous)
        with self.assertRaises(Exception):
            tasks.refresh_market('ime')
        self.assertEqual(MarketDataSyncState.objects.get(key='ime').last_success_at, previous)
        self.assertIn('skipped', tasks.refresh_market('ime'))
        sync.assert_called_once()

    @patch('products.tasks.sync_ime_market', return_value=1)
    def test_manual_sync_rejects_ordinary_authenticated_user(self, sync):
        self.client.force_authenticate(get_user_model().objects.create_user('ordinary-market-user'))
        self.assertEqual(self.client.post('/api/admin/commodity-exchange/sync/').status_code, 403)
        sync.assert_not_called()

    @patch('products.management.commands.sync_external_markets.refresh_market')
    def test_command_checks_both_providers_after_one_fails_and_records_heartbeat(self, refresh):
        from .external_markets import MarketSyncError
        from io import StringIO
        refresh.side_effect = [MarketSyncError('source unavailable'), {'skipped': 'manual_mode'}]
        with self.assertRaises(CommandError):
            call_command('sync_external_markets', stdout=StringIO())
        self.assertEqual(refresh.call_count, 2)
        self.assertIsNotNone(MarketDataSyncState.objects.get(key='market_scheduler').finished_at)

    @patch('products.tasks.sync_global_metals')
    def test_global_disabled_source_rejects_manual_request_without_network(self, sync):
        from .external_markets import MarketSyncError
        config = SiteSettings.load()
        config.global_metals_enabled = False
        config.save()
        self.assertEqual(tasks.refresh_market('metals_dev'), {'skipped': 'manual_mode'})
        with self.assertRaises(MarketSyncError):
            tasks.refresh_market('metals_dev', force=True)
        sync.assert_not_called()

    @patch('products.tasks.sync_global_metals')
    def test_provider_error_state_is_not_recorded_as_success(self, sync):
        from .external_markets import MarketSyncError
        def provider():
            MarketDataSyncState.objects.filter(key='metals_dev').update(status='error', error_message='API key missing')
            return 0
        sync.side_effect = lambda **kwargs: provider()
        with self.assertRaises(MarketSyncError):
            tasks.refresh_market('metals_dev', force=True)
        state = MarketDataSyncState.objects.get(key='metals_dev')
        self.assertIsNone(state.last_success_at)
        self.assertIsNone(state.lease_until)

    def test_settings_reject_invalid_modes_and_intervals_atomically(self):
        self.client.force_authenticate(get_user_model().objects.create_user('validation-admin', is_staff=True))
        for payload in [
            {'commodity_exchange': []}, {'commodity_exchange': {'auto_refresh': 'false'}},
            {'commodity_exchange': {'refresh_minutes': 4}}, {'commodity_exchange': {'refresh_minutes': 1441}},
            {'commodity_exchange': {'refresh_minutes': 5.5}}, {'global_metals': {'auto_refresh': 'false'}},
        ]:
            self.assertEqual(self.client.patch('/api/site-settings/', payload, format='json').status_code, 400)
        self.assertTrue(SiteSettings.load().ime_auto_refresh)

