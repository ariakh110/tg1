import uuid
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import override_settings
from rest_framework.test import APITestCase
from accounts.models import Profile,PhoneLoginIdentity
from assistant.models import AssistantInquiry,PurchaseInquiryNotice
from products.models import ProductCategory
from customers.models import CrmOpportunity

@override_settings(CACHES={'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'},'authentication':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}})
class AccountInquiryTests(APITestCase):
    base='/api/assistant/purchase-inquiry/'
    def setUp(self):
        caches['authentication'].clear()
        self.user=get_user_model().objects.create_user('buyer',first_name='آریا',last_name='خیر')
        Profile.objects.filter(user=self.user).update(phone='۰۹۱۲۳۴۵۶۷۸۹')
        self.category=ProductCategory.objects.create(name='ورق تست',code='account-sheet',product_kind='sheet')
        self.body={'request_id':str(uuid.uuid4()),'items':[{'category_code':self.category.code,'specification':'ST52 20x2000x6000','quantity':'10','unit':'ton'}],'city':'شهرضا','source_path':'/account/inquiries'}
        self.client.force_authenticate(self.user)
    def submit(self,**changes):
        return self.client.post(self.base+'account-submit/',{**self.body,**changes},format='json')
    def test_auth_required_and_bad_token_never_falls_back(self):
        self.client.force_authenticate(None)
        for path in ('account-context/','mine/'):
            self.assertIn(self.client.get(self.base+path).status_code,(401,403))
        self.assertIn(self.submit().status_code,(401,403))
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid')
        self.assertEqual(self.submit().status_code,401)
    @patch('messaging.providers.kavenegar.send_sms')
    @patch('messaging.providers.kavenegar.send_lookup')
    def test_account_contact_submission_atomic_notice_crm_and_no_sms(self,lookup,sms):
        context=self.client.get(self.base+'account-context/')
        self.assertEqual(context.status_code,200,context.data)
        self.assertEqual(context.data['phone'],'09123456789');self.assertEqual(context.data['name'],'آریا خیر')
        result=self.submit();self.assertEqual(result.status_code,201,result.data)
        inquiry=AssistantInquiry.objects.get()
        self.assertEqual(inquiry.contact_phone,'09123456789');self.assertEqual(inquiry.contact_name,'آریا خیر')
        self.assertNotIn('پیامک تأیید شده',inquiry.note)
        self.assertEqual(PurchaseInquiryNotice.objects.count(),1);self.assertEqual(CrmOpportunity.objects.count(),1)
        self.assertEqual(inquiry.requested_items[0]['unit'],'ton')
        sms.assert_not_called();lookup.assert_not_called()
    def test_retry_same_payload_after_profile_category_change_is_one_receipt(self):
        first=self.submit();self.assertEqual(first.status_code,201,first.data)
        Profile.objects.filter(user=self.user).update(phone='09111111111')
        self.category.is_active=False;self.category.save()
        again=self.submit();self.assertEqual(again.status_code,200,again.data)
        self.assertEqual(again.data['reference'],first.data['reference']);self.assertEqual(AssistantInquiry.objects.count(),1)
    def test_changed_payload_and_foreign_uuid_do_not_disclose_reference(self):
        first=self.submit();self.assertEqual(first.status_code,201,first.data)
        self.assertEqual(self.submit(city='تهران').status_code,409)
        other=get_user_model().objects.create_user('other');Profile.objects.filter(user=other).update(phone='09111111111')
        self.client.force_authenticate(other);response=self.submit()
        self.assertEqual(response.status_code,409);self.assertNotIn(first.data['reference'],str(response.data))
        self.assertEqual(self.client.get(self.base+'mine/').data['count'],0)
    def test_missing_contact_and_immutable_server_contact(self):
        self.assertEqual(self.submit(phone='09111111111',name='other',user_id=99).status_code,400)
        Profile.objects.filter(user=self.user).update(phone='')
        self.assertIs(self.client.get(self.base+'account-context/').data['can_submit'],False)
        self.assertEqual(self.submit().status_code,400)
        PhoneLoginIdentity.objects.create(phone='09123456789',user=self.user)
        self.assertIs(self.client.get(self.base+'account-context/').data['can_submit'],True)
        self.assertEqual(self.submit().status_code,201)
    def test_crm_failure_rolls_back_and_retry_succeeds_once(self):
        with patch('customers.opportunities.sync_assistant_inquiry_opportunity',side_effect=RuntimeError('secret')):
            response=self.submit();self.assertEqual(response.status_code,503,response.data)
        self.assertFalse(AssistantInquiry.objects.exists());self.assertFalse(PurchaseInquiryNotice.objects.exists())
        self.assertEqual(self.submit().status_code,201);self.assertEqual(self.submit().status_code,200)
        self.assertEqual(CrmOpportunity.objects.count(),1)
    def test_mine_is_owned_paginated_and_no_private_notes(self):
        from assistant.models import AccountPurchaseSubmission
        for i in range(21):
            inquiry=AssistantInquiry.objects.create(product='ورق',note='private-admin-note')
            AccountPurchaseSubmission.objects.create(id=uuid.uuid4(),user=self.user,payload_hash=str(i),inquiry=inquiry)
        other=get_user_model().objects.create_user('other')
        foreign=AssistantInquiry.objects.create(product='foreign-secret')
        AccountPurchaseSubmission.objects.create(id=uuid.uuid4(),user=other,payload_hash='other',inquiry=foreign)
        response=self.client.get(self.base+'mine/?user='+str(other.pk))
        self.assertEqual(response.data['count'],21);self.assertEqual(len(response.data['results']),20)
        self.assertNotIn('foreign-secret',str(response.data));self.assertNotIn('private-admin-note',str(response.data))
        self.assertEqual(len(self.client.get(self.base+'mine/?page=2').data['results']),1)
    def test_own_name_update_does_not_change_roles_or_another_user(self):
        other=get_user_model().objects.create_user('other')
        result=self.client.patch('/api/me/',{'first_name':'نام','last_name':'جدید','user':{'id':other.pk},'is_staff':True},format='json')
        self.assertEqual(result.status_code,200,result.data)
        self.user.refresh_from_db();other.refresh_from_db()
        self.assertEqual(self.user.first_name,'نام');self.assertEqual(other.first_name,'');self.assertFalse(self.user.is_staff)

    def test_cache_failure_is_registration_error_without_sms_instruction(self):
        with patch.object(caches['authentication'],'add',side_effect=RuntimeError()):
            response=self.submit()
        self.assertEqual(response.status_code,503)
        self.assertIn('ثبت لیست',str(response.data))
        self.assertFalse(AssistantInquiry.objects.exists())
