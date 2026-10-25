import hashlib
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from .models import MessagingSettings, MarketChannelDraft, MarketChannelPublication, OutboundMessage


class GoogleRelayTests(APITestCase):
    key = 'a1' * 32

    def setUp(self):
        self.admin = get_user_model().objects.create_user('relay-admin', is_staff=True)
        self.client.force_authenticate(self.admin)
        self.cfg = MessagingSettings.load()
        self.cfg.market_telegram_transport = 'google'
        self.cfg.market_google_relay_key_hash = hashlib.sha256(self.key.encode()).hexdigest()
        self.cfg.market_telegram_bot_token = ''
        self.cfg.save()
        self.draft = MarketChannelDraft.objects.create(fingerprint='relay-draft', report_date=timezone.localdate(),
            kind='item', product_group='sheet', title='Test', texts={'telegram': 'approved text'},
            targets={'telegram': self.cfg.market_telegram_channel_id})

    def publish(self):
        return self.client.post(f'/api/messaging/market-drafts/{self.draft.pk}/publish/', {'platforms': ['telegram']}, format='json')

    def relay(self, action, data=None):
        self.client.force_authenticate(None)
        return self.client.post(f'/api/messaging/market-relay/{action}/', data or {}, format='json', HTTP_AUTHORIZATION=f'Bearer {self.key}')

    @patch('messaging.market_channels.bot_send')
    def test_google_mode_queues_without_site_bot_token_or_network_and_deduplicates(self, send):
        for _ in range(2):
            result = self.publish()
            self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(MarketChannelPublication.objects.count(), 1)
        self.assertEqual(result.data['publications']['telegram']['relay_status'], 'pending')
        send.assert_not_called()
        first = self.relay('claim').data['job']
        self.assertEqual(first['text'], 'approved text')
        self.assertIsNone(self.relay('claim').data['job'])
        ack = {'id': first['id'], 'receipt': first['receipt'], 'status': 'sent', 'message_id': '123'}
        self.assertEqual(self.relay('ack', ack).status_code, 200)
        self.assertEqual(self.relay('ack', ack).status_code, 200)
        self.assertEqual(OutboundMessage.objects.get().status, 'sent')

    def test_missing_or_wrong_relay_key_cannot_claim(self):
        self.client.force_authenticate(None)
        for headers in [{}, {'HTTP_AUTHORIZATION': 'Bearer ' + 'b2' * 32}]:
            self.assertIn(self.client.post('/api/messaging/market-relay/claim/', {}, format='json', **headers).status_code, (401, 403))

    def test_key_is_write_only_hashed_and_empty_update_preserves_it(self):
        response = self.client.patch('/api/messaging/settings/', {'market_telegram_transport': 'google', 'market_google_relay_key': self.key}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['market_google_relay_configured'])
        self.assertNotIn(self.key, str(response.data))
        self.client.patch('/api/messaging/settings/', {'market_google_relay_key': ''}, format='json')
        self.cfg.refresh_from_db()
        self.assertEqual(self.cfg.market_google_relay_key_hash, hashlib.sha256(self.key.encode()).hexdigest())

    def test_wrong_receipt_or_conflicting_ack_cannot_change_delivery(self):
        self.publish()
        job = self.relay('claim').data['job']
        payload = {'id': job['id'], 'receipt': 'wrong', 'status': 'sent', 'message_id': '2'}
        self.assertEqual(self.relay('ack', payload).status_code, 409)
        payload.update(receipt=job['receipt'], status='unknown', message_id='')
        self.assertEqual(self.relay('ack', payload).status_code, 200)
        self.assertEqual(OutboundMessage.objects.get().status, 'queued')
        payload.update(status='sent', message_id='2')
        self.assertEqual(self.relay('ack', payload).status_code, 409)
