import re
import uuid
from datetime import timedelta
from unittest.mock import patch
from django.core.cache import caches
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from assistant.models import AssistantInquiry
from messaging.models import MessagingSettings, OutboundMessage
from messaging.providers.kavenegar import SendResult


class PurchaseInquiryTests(APITestCase):
    def setUp(self):
        caches['authentication'].clear()
        cfg=MessagingSettings.load();cfg.sms_enabled=True;cfg.kavenegar_api_key='test-secret';cfg.save()
        self.body={'request_id':str(uuid.uuid4()),'product':'sheet','size_mm':'30','quantity_kg':'20000',
            'phone':'۰۹۱۲۳۴۵۶۷۸۹','name':'خریدار','city':'اصفهان','source_path':'/market'}

    def request_code(self, **changes):
        return self.client.post('/api/assistant/purchase-inquiry/code/',{**self.body,**changes},format='json')

    def verify(self, code):
        return self.client.post('/api/assistant/purchase-inquiry/verify/',{'request_id':self.body['request_id'],'code':code},format='json')

    @patch('messaging.providers.kavenegar.send_sms',return_value=SendResult(ok=True,message_id='1'))
    def test_verification_creates_one_real_inquiry_and_customer_without_exposing_code(self, send):
        response=self.request_code()
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(AssistantInquiry.objects.count(),0)
        code=re.search(r'\b\d{6}\b',send.call_args.args[2]).group()
        self.assertNotIn(code,str(response.data))
        self.assertNotIn(code,str(list(OutboundMessage.objects.values())))
        self.assertEqual(self.verify(code).status_code,201)
        self.assertEqual(self.verify(code).status_code,200)
        inquiry=AssistantInquiry.objects.get()
        self.assertEqual(inquiry.contact_phone,'09123456789')
        self.assertEqual(inquiry.quantity,'20000 کیلوگرم')
        from customers.models import Customer
        self.assertTrue(Customer.objects.filter(phone='09123456789').exists())

    @patch('messaging.providers.kavenegar.send_sms',return_value=SendResult(ok=True))
    def test_wrong_code_is_limited_and_expired_code_cannot_create_inquiry(self, send):
        self.assertEqual(self.request_code().status_code,200)
        code=re.search(r'\b\d{6}\b',send.call_args.args[2]).group()
        wrong='000001' if code!='000001' else '000002'
        for _ in range(5):self.assertEqual(self.verify(wrong).status_code,400)
        self.assertEqual(self.verify(code).status_code,400)
        self.assertFalse(AssistantInquiry.objects.exists())

    @patch('messaging.providers.kavenegar.send_sms',return_value=SendResult(ok=True))
    def test_retry_code_request_is_idempotent_but_resend_and_phone_change_are_limited(self, send):
        self.assertEqual(self.request_code().status_code,200)
        self.assertEqual(self.request_code().status_code,200)
        self.assertEqual(send.call_count,1)
        self.assertEqual(self.request_code(resend=True).status_code,429)
        self.assertEqual(self.request_code(phone='09121111111').status_code,409)

    @patch('messaging.providers.kavenegar.send_sms',return_value=SendResult(ok=False,error='private-token'))
    def test_provider_failure_is_redacted_and_does_not_accept_a_code(self, send):
        response=self.request_code()
        self.assertEqual(response.status_code,503)
        self.assertNotIn('private-token',str(response.data))
        self.assertFalse(AssistantInquiry.objects.exists())

    @patch('messaging.providers.kavenegar.send_sms')
    def test_invalid_requests_and_disabled_sms_never_send(self, send):
        for field,value in [('phone','123'),('quantity_kg','0'),('size_mm','-1'),('product','arbitrary')]:
            self.assertEqual(self.request_code(**{field:value}).status_code,400)
        cfg=MessagingSettings.load();cfg.sms_enabled=False;cfg.save()
        self.assertEqual(self.request_code().status_code,503)
        send.assert_not_called()
