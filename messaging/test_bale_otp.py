import json
from unittest.mock import patch, MagicMock
from django.test import override_settings
from django.core.cache import caches
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from core.models import SiteSettings
from messaging.models import MessagingSettings, OutboundMessage
from messaging.providers import safir

@override_settings(CACHES={'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'},'authentication':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}})
class BaleOtpTests(APITestCase):
 def setUp(self):
  caches['authentication'].clear();site=SiteSettings.load();site.sms_login_enabled=True;site.save()
  self.cfg=MessagingSettings.load();self.cfg.safir_enabled=True;self.cfg.safir_access_key='secret';self.cfg.safir_bot_id='123';self.cfg.bale_otp_enabled=True;self.cfg.save()
 def issue(self,channel='bale'):
  return self.client.post('/api/auth/mobile/code/',{'phone':'09123456789','channel':channel},format='json')
 def test_native_payload_preserves_zeroes(self):
  response=MagicMock();response.read.return_value=b'{"message_id":"sent"}'
  with patch('messaging.providers.safir.urlopen') as http:
   http.return_value.__enter__.return_value=response
   result=safir.send_otp('key','123','989123456789','001234',request_id='once')
  self.assertTrue(result.ok);data=json.loads(http.call_args.args[0].data)
  self.assertEqual(data['message_data'],{'otp_message':{'otp':'001234'}});self.assertEqual(data['request_id'],'once')
 def test_bale_only_login_and_redacted_receipt(self):
  with patch('messaging.providers.safir.send_otp',create=True,return_value=safir.SendResult(ok=True,message_id='b1')) as send, patch('messaging.providers.kavenegar.send_sms') as sms:
   response=self.issue();self.assertEqual(response.status_code,200,response.data)
   code=send.call_args.args[3];self.assertRegex(code,r'^[0-9]{6}$');self.assertEqual(send.call_args.args[2],'989123456789')
   self.assertEqual(response.data['channel'],'bale')
   row=OutboundMessage.objects.get();self.assertEqual(row.channel,'bale');self.assertNotIn(code,str(row.meta)+row.body);sms.assert_not_called()
   verified=self.client.post('/api/auth/mobile/verify/',{'request_id':response.data['request_id'],'code':code},format='json')
   self.assertEqual(verified.status_code,200,verified.data);self.assertIn('access',verified.data)
   self.assertEqual(self.client.post('/api/auth/mobile/verify/',{'request_id':response.data['request_id'],'code':code},format='json').status_code,400)
 def test_disabled_unknown_and_no_automatic_fallback(self):
  with patch('messaging.providers.safir.send_otp',create=True,return_value=safir.SendResult(ok=False,error='private')) as send,patch('messaging.providers.kavenegar.send_sms') as sms:
   self.assertEqual(self.issue('telegram').status_code,400)
   self.assertEqual(self.issue().status_code,503);sms.assert_not_called();self.assertEqual(send.call_count,1)
   self.cfg.bale_otp_enabled=False;self.cfg.save();self.assertIn(self.issue().status_code,(403,503));self.assertEqual(send.call_count,1)
 def test_pending_bale_disabled_and_channel_switch_share_cooldown(self):
  with patch('messaging.providers.safir.send_otp',create=True,return_value=safir.SendResult(ok=True,message_id='b')) as send:
   r=self.issue();self.assertEqual(r.status_code,200,r.data);code=send.call_args.args[3]
   self.cfg.sms_enabled=True;self.cfg.kavenegar_api_key='key';self.cfg.save()
   self.assertEqual(self.issue('sms').status_code,429)
   self.cfg.bale_otp_enabled=False;self.cfg.save()
   denied=self.client.post('/api/auth/mobile/verify/',{'request_id':r.data['request_id'],'code':code},format='json')
   self.assertIn(denied.status_code,(400,403,503));self.assertNotIn('access',denied.data)
 def test_method_metadata_has_no_secrets(self):
  r=self.client.get('/api/auth/mobile/channels/');self.assertEqual(r.status_code,200,r.data);self.assertEqual(r.data['channels'],['bale']);self.assertNotIn('secret',str(r.data))

 def test_guest_inquiry_bale_choice_snapshot_and_redaction(self):
  import uuid
  body={'request_id':str(uuid.uuid4()),'product':'sheet','size_mm':'20','quantity_kg':'100','phone':'09123456789','channel':'bale'}
  with patch('messaging.providers.safir.send_otp',create=True,return_value=safir.SendResult(ok=True,message_id='b')) as send,patch('messaging.providers.kavenegar.send_sms') as sms:
   response=self.client.post('/api/assistant/purchase-inquiry/code/',body,format='json');self.assertEqual(response.status_code,200,response.data)
   code=send.call_args.args[3];sms.assert_not_called()
   conflict=self.client.post('/api/assistant/purchase-inquiry/code/',{**body,'channel':'sms'},format='json')
   self.assertIn(conflict.status_code,(409,503))
   result=self.client.post('/api/assistant/purchase-inquiry/verify/',{'request_id':body['request_id'],'code':code},format='json')
   self.assertEqual(result.status_code,201,result.data)
   from assistant.models import AssistantInquiry
   self.assertIn('بله',AssistantInquiry.objects.get().note)
   self.assertNotIn(code,str(OutboundMessage.objects.get().meta))
