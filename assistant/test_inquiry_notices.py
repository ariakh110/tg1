from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from assistant.models import AssistantInquiry
from messaging.models import MessagingSettings,OutboundMessage
from messaging.providers.telegram import SendResult


class InquiryNoticeTests(TestCase):
    def setUp(self):
        self.inquiry=AssistantInquiry.objects.create(product='لیست خرید',contact_name='خریدار',contact_phone='09123456789',city='اصفهان',
            requested_items=[{'category_name':'ورق','specification':'ST52 30 میل','quantity':'2.5','unit':'ton'}]*50)
        cfg=MessagingSettings.load();cfg.telegram_enabled=True;cfg.telegram_bot_token='private-test';cfg.telegram_admin_chat_id='123,456';cfg.telegram_api_base='https://tapi.bale.ai';cfg.save()
        self.client=APIClient();self.admin=get_user_model().objects.create_user('notice-admin',is_staff=True)

    def notice(self):
        from assistant.inquiry_notices import create_inquiry_notice
        return create_inquiry_notice(self.inquiry)

    @patch('messaging.providers.telegram.send_message',return_value=SendResult(ok=True,status='sent',message_id='81'))
    def test_delivery_is_claimed_once_and_bounded_with_link(self,send):
        from assistant.inquiry_notices import dispatch_inquiry_notices
        notice=self.notice();self.assertEqual(self.notice().pk,notice.pk)
        dispatch_inquiry_notices();dispatch_inquiry_notices()
        self.assertEqual(send.call_count,2)
        body=send.call_args.args[2]
        self.assertLess(len(body),3800);self.assertIn('KX-Q-',body);self.assertIn('09123456789',body)
        self.assertIn('50',body);self.assertIn('inquiry=',body);self.assertIn('ST52',body)
        notice.refresh_from_db();self.assertEqual(notice.bale_status,'sent')
        self.assertEqual(OutboundMessage.objects.filter(purpose='admin_alert',provider='bale').count(),2)

    @patch('messaging.providers.telegram.send_message',side_effect=RuntimeError('private-test-secret'))
    def test_unknown_and_stale_delivery_never_retry(self,send):
        from assistant.inquiry_notices import dispatch_inquiry_notices
        notice=self.notice();dispatch_inquiry_notices();dispatch_inquiry_notices()
        self.assertEqual(send.call_count,2)
        notice.refresh_from_db();self.assertEqual(notice.bale_status,'unknown')
        self.assertNotIn('private-test-secret',str(notice.bale_deliveries))
        notice.bale_status='pending';notice.bale_deliveries={'123':{'status':'sending','started_at':(timezone.now()-timedelta(minutes=11)).isoformat()}};notice.save()
        dispatch_inquiry_notices();notice.refresh_from_db();self.assertEqual(notice.bale_status,'unknown')
        self.assertEqual(send.call_count,2)

    @patch('messaging.providers.telegram.send_message')
    def test_disabled_or_wrong_host_still_has_site_notice_without_send(self,send):
        from assistant.inquiry_notices import dispatch_inquiry_notices
        cfg=MessagingSettings.load();cfg.telegram_api_base='https://api.telegram.org';cfg.save()
        notice=self.notice();dispatch_inquiry_notices();self.assertEqual(notice.bale_status,'unconfigured');send.assert_not_called()

    def test_feed_permission_and_per_user_read_do_not_change_inquiry_status(self):
        notice=self.notice();url='/api/assistant/admin/purchase-notices/'
        self.assertIn(self.client.get(url).status_code,(401,403))
        outsider=get_user_model().objects.create_user('notice-outsider');self.client.force_authenticate(outsider)
        self.assertEqual(self.client.get(url).status_code,403)
        self.client.force_authenticate(self.admin)
        data=self.client.get(url).data;self.assertEqual(data['unread_count'],1)
        self.assertNotIn('09123456789',str(data));self.assertNotIn('private-test',str(data))
        read=url+str(notice.pk)+'/read/'
        self.assertEqual(self.client.post(read).status_code,200);self.assertEqual(self.client.post(read).status_code,200)
        self.assertEqual(self.client.get(url).data['unread_count'],0)
        other=get_user_model().objects.create_user('notice-other',is_staff=True);self.client.force_authenticate(other)
        self.assertEqual(self.client.get(url).data['unread_count'],1)
        self.inquiry.refresh_from_db();self.assertEqual(self.inquiry.status,'new')

    @patch('messaging.providers.telegram.send_message')
    def test_only_private_numeric_admin_destinations_and_no_empty_pending(self,send):
        cfg=MessagingSettings.load();cfg.telegram_admin_chat_id='@public-channel,-10012, ,0';cfg.save()
        notice=self.notice();self.assertEqual(notice.bale_status,'unconfigured')
        self.assertEqual(notice.bale_deliveries,{})
        send.assert_not_called()

    def test_overlapping_dispatch_claims_each_recipient_once(self):
        from assistant.inquiry_notices import dispatch_inquiry_notices
        notice=self.notice();nested=False
        def deliver(*args,**kwargs):
            nonlocal nested
            if not nested:nested=True;dispatch_inquiry_notices()
            return SendResult(ok=True,status='sent',message_id='82')
        with patch('messaging.providers.telegram.send_message',side_effect=deliver) as send:
            dispatch_inquiry_notices();self.assertEqual(send.call_count,2)
        notice.refresh_from_db();self.assertEqual(notice.bale_status,'sent')

    @patch('messaging.providers.telegram.send_message',return_value=SendResult(ok=True,status='sent',message_id='83'))
    def test_equivalent_numeric_recipients_send_once(self,send):
        from assistant.inquiry_notices import dispatch_inquiry_notices
        cfg=MessagingSettings.load();cfg.telegram_admin_chat_id='123,0123';cfg.save()
        notice=self.notice()
        self.assertEqual(list(notice.bale_deliveries),['123'])
        dispatch_inquiry_notices();self.assertEqual(send.call_count,1)

    @patch('assistant.inquiry_notices.dispatch_inquiry_notices',return_value=0)
    def test_management_command_dispatches_without_provider_calls(self,dispatch):
        from django.core.management import call_command
        call_command('dispatch_purchase_inquiry_notices')
        dispatch.assert_called_once_with()
