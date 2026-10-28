import re
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from core.models import SiteSettings
from messaging.models import MessagingSettings, OutboundMessage
from messaging.providers.kavenegar import SendResult
from accounts.models import Profile

@override_settings(CACHES={'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'},'authentication':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}})
class MobileLoginTests(APITestCase):
    def setUp(self):
        caches['authentication'].clear()
        site=SiteSettings.load();site.sms_login_enabled=True;site.save()
        cfg=MessagingSettings.load();cfg.sms_enabled=True;cfg.kavenegar_api_key='secret-key';cfg.save()
        self.phone='09123456789'
        self.send=patch('messaging.providers.kavenegar.send_sms',return_value=SendResult(ok=True,message_id='1')).start()
        self.addCleanup(patch.stopall)
    def issue(self,phone=None,bind=False):
        return self.client.post('/api/auth/mobile/'+('bind/' if bind else '')+'code/',{'phone':phone or self.phone},format='json')
    def code(self):
        return re.search(r'[0-9]{6}',self.send.call_args.args[2]).group()
    def verify(self,res,code=None,bind=False):
        return self.client.post('/api/auth/mobile/'+('bind/' if bind else '')+'verify/',{'request_id':res.data['request_id'],'code':code or self.code()},format='json')
    def test_new_identity_login_replay_and_redacted_logs(self):
        from accounts.models import PhoneLoginIdentity,PhoneLoginChallenge
        first=self.issue();self.assertEqual(first.status_code,200,first.data)
        code=self.code();challenge=PhoneLoginChallenge.objects.get();self.assertNotEqual(challenge.code_hash,code)
        response=self.verify(first);self.assertEqual(response.status_code,200,response.data)
        identity=PhoneLoginIdentity.objects.get();self.assertEqual(identity.phone,self.phone)
        self.assertFalse(identity.user.has_usable_password());self.assertFalse(identity.user.is_staff)
        self.assertIn('access',response.data);self.assertNotIn(code,str(first.data));self.assertNotIn(code,OutboundMessage.objects.get().body)
        self.assertEqual(self.verify(first).status_code,400)
    def test_normalization_and_existing_verified_login(self):
        from accounts.models import PhoneLoginIdentity
        user=get_user_model().objects.create_user('known')
        PhoneLoginIdentity.objects.create(user=user,phone=self.phone)
        r=self.issue('+۹۸۹۱۲۳۴۵۶۷۸۹');self.assertEqual(r.status_code,200,r.data)
        result=self.verify(r);self.assertEqual(result.data['user']['id'],user.pk)
    def test_legacy_duplicate_phone_is_never_implicitly_linked(self):
        for name in ('legacy','other'):
            u=get_user_model().objects.create_user(name);Profile.objects.update_or_create(user=u,defaults={'phone':'+98 912 345 6789'})
        r=self.issue();result=self.verify(r)
        self.assertEqual(result.status_code,409,result.data);self.assertNotIn('access',result.data)
    def test_bind_requires_authenticated_same_user_and_never_issues_tokens(self):
        user=get_user_model().objects.create_user('legacy')
        self.assertIn(self.issue(bind=True).status_code,(401,403))
        self.client.force_authenticate(user);r=self.issue(bind=True);self.assertEqual(r.status_code,200,r.data)
        other=get_user_model().objects.create_user('other');self.client.force_authenticate(other)
        self.assertEqual(self.verify(r,bind=True).status_code,400)
        self.client.force_authenticate(user);result=self.verify(r,bind=True)
        self.assertEqual(result.status_code,200,result.data);self.assertNotIn('access',result.data)
        self.assertEqual(self.client.get('/api/auth/mobile/binding/').data['phone'],self.phone)
        self.client.force_authenticate(None)
    def test_inactive_identity_and_cross_owner_binding_denied(self):
        from accounts.models import PhoneLoginIdentity,PhoneLoginChallenge
        user=get_user_model().objects.create_user('inactive',is_active=False);PhoneLoginIdentity.objects.create(user=user,phone=self.phone)
        r=self.issue();self.assertEqual(self.verify(r).status_code,403)
        PhoneLoginChallenge.objects.all().delete()
        other=get_user_model().objects.create_user('other');self.client.force_authenticate(other)
        caches['authentication'].clear()
        r=self.issue(bind=True);self.assertEqual(self.verify(r,bind=True).status_code,409)
    def test_wrong_five_times_expiry_and_disabled_pending(self):
        from accounts.models import PhoneLoginChallenge
        r=self.issue()
        for _ in range(5):self.assertEqual(self.verify(r,'000000' if self.code()!='000000' else '111111').status_code,400)
        self.assertEqual(self.verify(r).status_code,400)
        challenge=PhoneLoginChallenge.objects.get();challenge.attempts=0;challenge.expires_at=timezone.now()-timedelta(seconds=1);challenge.save()
        self.assertEqual(self.verify(r).status_code,400)
        site=SiteSettings.load();site.sms_login_enabled=False;site.save()
        self.assertEqual(self.issue().status_code,403);self.assertEqual(self.verify(r).status_code,403)
    def test_provider_failure_cache_failure_invalid_phone_and_missing_config(self):
        from accounts.models import PhoneLoginChallenge
        self.assertEqual(self.issue('123').status_code,400)
        self.send.return_value=SendResult(ok=False,error='secret-key-code')
        r=self.issue();self.assertEqual(r.status_code,503)
        self.assertFalse(PhoneLoginChallenge.objects.get().sent)
        self.assertNotIn('secret-key',str(list(OutboundMessage.objects.values())))
        with patch.object(caches['authentication'],'add',side_effect=RuntimeError()):
            self.assertEqual(self.issue('09111111111').status_code,503)
        cfg=MessagingSettings.load();cfg.sms_enabled=False;cfg.save()
        self.assertEqual(self.issue('09222222222').status_code,503)
    def test_cooldown_resend_invalidates_old_id_and_daily_cost_cap(self):
        from accounts.models import PhoneLoginChallenge
        r=self.issue();self.assertEqual(self.issue().status_code,429)
        challenge=PhoneLoginChallenge.objects.get();challenge.last_sent_at-=timedelta(seconds=61);challenge.save()
        r2=self.issue();self.assertNotEqual(r.data['request_id'],r2.data['request_id'])
        self.assertEqual(self.verify(r).status_code,400);self.assertEqual(self.verify(r2).status_code,200)
        cfg=MessagingSettings.load();cfg.daily_send_cap=2;cfg.save()
        self.assertEqual(self.issue('09111111111').status_code,503)
    def test_separate_lookup_template(self):
        cfg=MessagingSettings.load();cfg.login_otp_template='login';cfg.purchase_inquiry_otp_template='purchase';cfg.save()
        with patch('messaging.providers.kavenegar.send_lookup',return_value=SendResult(ok=True)) as lookup:
            r=self.issue();self.assertEqual(r.status_code,200,r.data)
            self.assertEqual(lookup.call_args.args[2],'login');self.send.assert_not_called()
    def test_admin_toggle_and_public_boolean(self):
        site=SiteSettings.load();site.sms_login_enabled=False;site.save()
        self.assertIs(self.client.get('/api/site-settings/').data['sms_login_enabled'],False)
        self.assertIn(self.client.patch('/api/site-settings/',{'sms_login_enabled':True},format='json').status_code,(401,403))
        admin=get_user_model().objects.create_user('admin',is_staff=True);self.client.force_authenticate(admin)
        self.assertEqual(self.client.patch('/api/site-settings/',{'sms_login_enabled':'false'},format='json').status_code,400)
        self.assertEqual(self.client.patch('/api/site-settings/',{'sms_login_enabled':True},format='json').status_code,200)
        self.assertIs(self.client.get('/api/site-settings/').data['sms_login_enabled'],True)

    def test_ip_limit_uses_production_trusted_proxy_contract(self):
        with override_settings(REST_FRAMEWORK={'NUM_PROXIES':1}), patch('accounts.mobile_login.budget') as limit:
            self.client.post('/api/auth/mobile/code/',{'phone':self.phone},format='json',HTTP_X_FORWARDED_FOR='198.51.100.27',REMOTE_ADDR='127.0.0.1')
            self.assertIn(('issue-ip','198.51.100.27',3600,10),[call.args for call in limit.call_args_list])
