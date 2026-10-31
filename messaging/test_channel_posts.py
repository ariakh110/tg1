from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from messaging.models import MessagingSettings, MarketChannelDraft, GoogleRelayJob

class ChannelPostTests(APITestCase):
 def setUp(self):
  self.user=get_user_model().objects.create_user('publisher',is_staff=True)
  self.client.force_authenticate(self.user)
  self.cfg=MessagingSettings.load();self.cfg.channel_posts_enabled=True;self.cfg.market_bale_bot_token='bale-secret';self.cfg.market_bale_channel_id='@channel';self.cfg.save()
  self.now=datetime(2026,10,31,8,5,tzinfo=ZoneInfo('Asia/Tehran'))
 def create(self,**extra):
  body={'title':'روزانه','body':'سلام {{jalali_date}} {{weekday}}','send_time':'08:00','weekdays':list(range(7)),'platforms':['bale'],'enabled':True,**extra}
  r=self.client.post('/api/messaging/channel-posts/',body,format='json');self.assertEqual(r.status_code,201,r.data);return r.data
 def test_permissions_validation_and_preview_no_send(self):
  with patch('messaging.market_channels.bot_send') as send:
   r=self.client.post('/api/messaging/channel-posts/preview/',{'title':'صبح','body':'سلام {{jalali_date}}','send_time':'08:00','weekdays':[5],'platforms':['bale']},format='json')
   self.assertEqual(r.status_code,200,r.data);self.assertNotIn('{{',r.data['text']);send.assert_not_called()
  for changes in [{'weekdays':[7]},{'platforms':['sms']},{'body':'x'*3501},{'body':'{{password}}'}]:
   r=self.client.post('/api/messaging/channel-posts/',{'title':'x','body':'x','send_time':'08:00','weekdays':[1],'platforms':['bale'],**changes},format='json');self.assertEqual(r.status_code,400)
  self.client.force_authenticate(None);self.assertIn(self.client.get('/api/messaging/channel-posts/').status_code,(401,403))
 def test_daily_reservation_survives_edit_and_rerun(self):
  from messaging.channel_posts import dispatch_due
  from messaging.models import ChannelPostRun
  row=self.create()
  with patch('messaging.market_channels.bot_send',return_value='1') as send:
   dispatch_due(self.now);dispatch_due(self.now)
   self.client.patch(f"/api/messaging/channel-posts/{row['id']}/",{'body':'متن تازه'},format='json');dispatch_due(self.now)
  self.assertEqual(send.call_count,1);self.assertEqual(ChannelPostRun.objects.count(),1)
  self.assertNotIn('{{',send.call_args.args[3]);self.assertEqual(ChannelPostRun.objects.get().status,'sent')
 def test_unknown_is_not_retried_and_crashed_claim_expires(self):
  from messaging.channel_posts import dispatch_due
  from messaging.models import ChannelPostRun
  self.create()
  with patch('messaging.market_channels.bot_send',side_effect=TimeoutError) as send:
   dispatch_due(self.now);dispatch_due(self.now+timedelta(minutes=1));self.assertEqual(send.call_count,1)
  run=ChannelPostRun.objects.get();self.assertEqual(run.status,'unknown')
  run.status='reserved';run.created_at=self.now-timedelta(minutes=11);run.save()
  with patch('messaging.market_channels.bot_send') as send:dispatch_due(self.now);send.assert_not_called()
  run.refresh_from_db();self.assertEqual(run.status,'unknown')
 def test_switches_window_days_and_google_transport(self):
  from messaging.channel_posts import dispatch_due
  from messaging.models import ChannelPostSchedule
  row=self.create();schedule=ChannelPostSchedule.objects.get(pk=row['id'])
  with patch('messaging.market_channels.bot_send') as send:
   self.cfg.channel_posts_enabled=False;self.cfg.save();dispatch_due(self.now)
   self.cfg.channel_posts_enabled=True;self.cfg.save();dispatch_due(self.now+timedelta(hours=2))
   schedule.enabled=False;schedule.save();dispatch_due(self.now);send.assert_not_called()
  schedule.enabled=True;schedule.platforms=['telegram'];schedule.save()
  self.cfg.market_telegram_transport='google';self.cfg.market_google_relay_key_hash='hash';self.cfg.save()
  with patch('messaging.market_channels.bot_send') as send:dispatch_due(self.now);send.assert_not_called()
  self.assertEqual(GoogleRelayJob.objects.count(),1)
 def test_morning_seed_disabled_and_history_no_secret(self):
  r=self.client.get('/api/messaging/channel-posts/');self.assertEqual(r.status_code,200,r.data)
  rows=r.data if isinstance(r.data,list) else r.data['results'];self.assertTrue(any('صبح' in x['title'] and not x['enabled'] for x in rows))
  self.assertNotIn('bale-secret',str(r.data))

 def test_one_bad_transport_never_suppresses_healthy_destination(self):
  from messaging.channel_posts import dispatch_due,run_payload
  from messaging.models import ChannelPostRun,ChannelPostSchedule
  for broken in ('telegram','bale'):
   self.cfg.market_bale_bot_token='' if broken=='bale' else 'bale-secret';self.cfg.market_telegram_bot_token='' if broken=='telegram' else 'tg-secret';self.cfg.save()
   self.create(platforms=['telegram','bale'])
   with patch('messaging.market_channels.bot_send',return_value='sent') as send:
    dispatch_due(self.now);dispatch_due(self.now)
   self.assertEqual(send.call_count,1);self.assertEqual(send.call_args.args[0],'telegram' if broken=='bale' else 'bale')
   details=run_payload(ChannelPostRun.objects.order_by('-id').first())['publications']
   self.assertEqual(details[broken]['status'],'failed')
 def test_template_becomes_invalid_without_starving_other_schedules(self):
  from messaging.channel_posts import dispatch_due
  from messaging.models import ChannelPostRun
  from core.models import SiteSettings
  site=SiteSettings.load();site.site_name='x';site.save()
  self.create(body='{{site_name}} '*200);self.create(title='سالم',body='سلام')
  site.site_name='x'*22;site.save()
  with patch('messaging.market_channels.bot_send',return_value='ok') as send:
   dispatch_due(self.now);dispatch_due(self.now)
  self.assertEqual(send.call_count,1);self.assertEqual(ChannelPostRun.objects.count(),2)
  self.assertEqual(ChannelPostRun.objects.filter(status='failed').count(),1)
 def test_late_google_ambiguity_takes_precedence_over_bale_rejection(self):
  from messaging.channel_posts import dispatch_due,run_payload
  from messaging.models import ChannelPostRun
  from messaging.market_channels import BotRejected
  self.cfg.market_telegram_transport='google';self.cfg.market_google_relay_key_hash='hash';self.cfg.save();self.create(platforms=['bale','telegram'])
  with patch('messaging.market_channels.bot_send',side_effect=BotRejected('rejected')):dispatch_due(self.now)
  job=GoogleRelayJob.objects.get();job.status='unknown';job.save()
  data=run_payload(ChannelPostRun.objects.get());self.assertEqual(data['status'],'unknown');self.assertIn('بررسی',data['error'])
