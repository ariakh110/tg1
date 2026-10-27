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

    def list_body(self, items=None):
        return {key:value for key,value in {**self.body,'items':items or [
            {'category_code':'sheet','specification':'ST52 اکسین 30 میل 2000x6000','quantity':'2.5','unit':'ton'},
            {'category_code':'rebar','specification':'آجدار سایز 16','quantity':'30','unit':'branch'}]}.items()
            if key not in ('product','size_mm','quantity_kg')}

    @patch('messaging.providers.kavenegar.send_sms',return_value=SendResult(ok=True))
    def test_multi_item_list_creates_one_complete_inquiry_and_crm_opportunity(self,send):
        from customers.models import CrmOpportunity
        body=self.list_body()
        response=self.client.post('/api/assistant/purchase-inquiry/code/',body,format='json')
        self.assertEqual(response.status_code,200,response.data)
        code=re.search(r'\b\d{6}\b',send.call_args.args[2]).group()
        with self.captureOnCommitCallbacks(execute=True):
            first=self.verify(code)
        self.assertEqual(first.status_code,201,first.data)
        self.assertEqual(self.verify(code).data['reference'],first.data['reference'])
        inquiry=AssistantInquiry.objects.get()
        self.assertEqual(len(inquiry.requested_items),2)
        self.assertEqual(inquiry.requested_items[0]['quantity'],'2.5')
        self.assertEqual(inquiry.requested_items[1]['unit'],'branch')
        self.assertIn('اکسین',inquiry.raw_text)
        opportunity=CrmOpportunity.objects.get(source_type='assistant_inquiry')
        self.assertEqual(opportunity.metadata['requested_items'],inquiry.requested_items)
        self.assertEqual(send.call_count,1)

    @patch('messaging.providers.kavenegar.send_sms',return_value=SendResult(ok=True))
    def test_fifty_items_and_immutable_list(self,send):
        body=self.list_body();body['items']=[{**body['items'][0],'specification':f'ST52 {i}'} for i in range(50)]
        response=self.client.post('/api/assistant/purchase-inquiry/code/',body,format='json')
        self.assertEqual(response.status_code,200,response.data)
        changed={**body,'items':[{**body['items'][0],'quantity':'3'}]}
        self.assertEqual(self.client.post('/api/assistant/purchase-inquiry/code/',changed,format='json').status_code,409)
        code=re.search(r'\b\d{6}\b',send.call_args.args[2]).group()
        self.assertEqual(self.verify(code).status_code,201)
        self.assertEqual(len(AssistantInquiry.objects.get().requested_items),50)

    @patch('messaging.providers.kavenegar.send_sms')
    def test_invalid_lists_never_send_or_persist(self,send):
        body=self.list_body();item=body['items'][0]
        for items in ([],[item]*51,[{**item,'category_code':'missing'}],[{**item,'specification':''}],
                      [{**item,'specification':'x'*201}],[{**item,'quantity':'0'}],[{**item,'unit':'unknown'}],
                      [{**item,'quantity':'NaN'}],[{**item,'quantity':'2.123'}]):
            response=self.client.post('/api/assistant/purchase-inquiry/code/',{**body,'items':items},format='json')
            self.assertEqual(response.status_code,400,response.data)
        mixed={**self.body,'items':[item]}
        self.assertEqual(self.client.post('/api/assistant/purchase-inquiry/code/',mixed,format='json').status_code,400)
        send.assert_not_called();self.assertFalse(AssistantInquiry.objects.exists())

    def test_options_cover_active_categories_and_admin_list_is_read_only(self):
        from products.models import ProductCategory
        from .serializers import AssistantInquirySerializer
        parent=ProductCategory.objects.create(name='Hidden family',code='hidden-family',is_active=False)
        ProductCategory.objects.create(name='Hidden child',code='hidden-child',parent=parent,is_active=True)
        ProductCategory.objects.create(name='Custom fasteners',code='custom-fasteners',is_active=True)
        data=self.client.get('/api/assistant/purchase-inquiry/options/').data
        codes={category['code'] for category in data['categories']}
        self.assertIn('custom-fasteners',codes);self.assertNotIn('hidden-child',codes)
        self.assertEqual(data['max_items'],50)
        serializer=AssistantInquirySerializer()
        self.assertTrue(serializer.fields['requested_items'].read_only)

    @patch('messaging.providers.kavenegar.send_sms',return_value=SendResult(ok=True))
    def test_crm_failure_rolls_back_verified_list_and_same_code_can_retry(self,send):
        from customers.models import CrmOpportunity,Customer
        from .models import PurchaseInquiryChallenge
        response=self.client.post('/api/assistant/purchase-inquiry/code/',self.list_body(),format='json')
        self.assertEqual(response.status_code,200,response.data)
        code=re.search(r'\b\d{6}\b',send.call_args.args[2]).group()
        with patch('customers.opportunities.sync_assistant_inquiry_opportunity',side_effect=RuntimeError('private storage')):
            failed=self.verify(code)
        self.assertEqual(failed.status_code,503,failed.data)
        self.assertNotIn('private storage',str(failed.data))
        self.assertFalse(AssistantInquiry.objects.exists());self.assertFalse(CrmOpportunity.objects.exists())
        self.assertFalse(Customer.objects.filter(phone='09123456789').exists())
        self.assertIsNone(PurchaseInquiryChallenge.objects.get().inquiry_id)
        self.assertEqual(self.verify(code).status_code,201)
        self.assertEqual(CrmOpportunity.objects.filter(source_type='assistant_inquiry').count(),1)

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

    @patch('messaging.providers.kavenegar.send_sms',return_value=SendResult(ok=True))
    def test_expired_code_is_rejected_and_phone_cooldown_cannot_be_bypassed_with_new_id(self, send):
        from .models import PurchaseInquiryChallenge
        self.assertEqual(self.request_code().status_code,200)
        code=re.search(r'\b\d{6}\b',send.call_args.args[2]).group()
        PurchaseInquiryChallenge.objects.filter(pk=self.body['request_id']).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.verify(code).status_code,400)
        self.assertEqual(self.request_code(request_id=str(uuid.uuid4())).status_code,429)
        self.assertEqual(send.call_count,1)

    @patch('messaging.providers.kavenegar.send_lookup',return_value=SendResult(ok=True))
    @patch('messaging.providers.kavenegar.send_sms')
    def test_dedicated_otp_template_and_hashed_code(self, plain, lookup):
        from .models import PurchaseInquiryChallenge
        from django.contrib.auth.hashers import check_password
        cfg=MessagingSettings.load();cfg.purchase_inquiry_otp_template='purchase-otp';cfg.save()
        self.assertEqual(self.request_code().status_code,200)
        plain.assert_not_called()
        self.assertEqual(lookup.call_args.args[2],'purchase-otp')
        code=lookup.call_args.args[3]
        challenge=PurchaseInquiryChallenge.objects.get()
        self.assertNotEqual(challenge.otp_hash,code)
        self.assertTrue(check_password(code,challenge.otp_hash))

    @patch('messaging.providers.kavenegar.send_sms')
    def test_sms_daily_cap_and_cache_failure_fail_closed(self, send):
        cfg=MessagingSettings.load();cfg.daily_send_cap=1;cfg.save()
        OutboundMessage.objects.create(channel='sms',status='sent',recipient='09120000000')
        self.assertEqual(self.request_code().status_code,503)
        with patch('assistant.purchase_inquiries.caches') as cache:
            cache.__getitem__.side_effect=RuntimeError('private storage detail')
            response=self.request_code()
        self.assertEqual(response.status_code,503)
        self.assertNotIn('private storage detail',str(response.data))
        send.assert_not_called()

    @patch('messaging.providers.kavenegar.send_sms',return_value=SendResult(ok=True))
    def test_verified_request_reaches_existing_crm_opportunity_flow(self, send):
        from customers.models import CrmOpportunity
        self.request_code()
        code=re.search(r'\b\d{6}\b',send.call_args.args[2]).group()
        with self.captureOnCommitCallbacks(execute=True):
            response=self.verify(code)
        self.assertEqual(response.status_code,201)
        self.assertTrue(CrmOpportunity.objects.filter(source_type='assistant_inquiry').exists())
