"""SMS login identities are independent of editable, unverified profile phones."""
import hashlib
import secrets
import time
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import caches
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException, PermissionDenied, Throttled
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import SiteSettings
from customers.services import normalize_phone
from messaging.models import MessagingSettings, OutboundMessage
from messaging.providers import kavenegar
from messaging.otp_delivery import ready, channels, send_bale_code
from .models import PhoneLoginChallenge, PhoneLoginIdentity, Profile

DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
User = get_user_model()


class LoginUnavailable(APIException):
    status_code = 503
    default_detail = 'ارسال کد ورود فعلاً در دسترس نیست؛ با رمز عبور وارد شوید یا کمی بعد تلاش کنید.'


def enabled():
    if not SiteSettings.load().sms_login_enabled:
        raise PermissionDenied('ورود پیامکی غیرفعال است؛ از ورود با رمز عبور استفاده کنید.')


def locked_enabled():
    # Same row lock as the admin PATCH: disable and credential mutation serialize.
    cfg = SiteSettings.objects.select_for_update().get(pk=SiteSettings.load().pk)
    if not cfg.sms_login_enabled:
        raise PermissionDenied('ورود پیامکی غیرفعال است؛ از ورود با رمز عبور استفاده کنید.')


def budget(scope, identity, seconds, limit):
    now = int(time.time())
    key = f'mobile-login:v1:{scope}:{hashlib.sha256(str(identity).encode()).hexdigest()}:{now // seconds}'
    ttl = seconds - now % seconds
    try:
        cache = caches['authentication']
        count = 1 if cache.add(key, 1, timeout=ttl + 1) else cache.incr(key)
    except Exception:
        raise LoginUnavailable() from None
    if count > limit:
        raise Throttled(wait=ttl, detail='تعداد تلاش‌ها زیاد است؛ بعداً دوباره تلاش کنید.')


def canonical_phone(value):
    phone = normalize_phone(str(value).translate(DIGITS))
    if len(phone) != 11 or not phone.startswith('09') or not phone.isascii() or not phone.isdigit():
        raise serializers.ValidationError({'phone': 'شماره موبایل معتبر وارد کنید.'})
    return phone


class CodeInput(serializers.Serializer):
    channel = serializers.ChoiceField(choices=["sms", "bale"], default="sms")
    phone = serializers.CharField(max_length=30)
    def validate_phone(self, value):
        return canonical_phone(value)


class VerifyInput(serializers.Serializer):
    request_id = serializers.UUIDField()
    code = serializers.RegexField(r'^[0-9]{6}$')
    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = {**data, 'code': str(data.get('code', '')).translate(DIGITS)}
        return super().to_internal_value(data)


def issue_code(phone, bind_user_id, channel="sms"):
    now = timezone.now()
    with transaction.atomic():
        locked_enabled()
        cfg = MessagingSettings.objects.select_for_update().get(pk=MessagingSettings.load().pk)
        if not ready(cfg, channel):
            raise LoginUnavailable()
        from messaging.service import _today_sent_count
        if channel == 'sms' and cfg.daily_send_cap and _today_sent_count() >= cfg.daily_send_cap:
            raise LoginUnavailable()
        slot, _ = PhoneLoginChallenge.objects.get_or_create(phone=phone, defaults={
            'request_id': uuid.uuid4(), 'code_hash': '', 'expires_at': now,
            'last_sent_at': now - timedelta(seconds=61)})
        slot = PhoneLoginChallenge.objects.select_for_update().get(pk=slot.pk)
        remaining = 60 - int((now - slot.last_sent_at).total_seconds())
        if remaining > 0:
            raise Throttled(wait=remaining)
        budget('phone-hour', phone, 3600, 3)
        budget('phone-day', phone, 86400, 10)
        budget('global-day', 'all', 86400, getattr(settings, 'SMS_LOGIN_DAILY_LIMIT', 200))
        code = f'{secrets.randbelow(1000000):06d}'
        slot.request_id = uuid.uuid4()
        slot.code_hash = make_password(code)
        slot.expires_at = now + timedelta(minutes=5)
        slot.last_sent_at = now
        slot.attempts = 0
        slot.sent = False
        slot.consumed = False
        slot.bind_user_id = bind_user_id
        slot.delivery_channel = channel
        slot.save()
        request_id = slot.request_id
        log = OutboundMessage.objects.create(channel=channel, provider='safir' if channel == 'bale' else 'kavenegar', recipient=phone,
            purpose='otp', status='queued', body='کد ورود سایت (محرمانه)',
            meta={'login_request_id': str(request_id)})
    try:
        if channel == 'bale':
            result = send_bale_code(cfg, phone, code, request_id)
        elif cfg.login_otp_template:
            result = kavenegar.send_lookup(cfg.kavenegar_api_key, phone, cfg.login_otp_template, code)
        else:
            result = kavenegar.send_sms(cfg.kavenegar_api_key, phone,
                f'کد ورود کاوه‌متال: {code}\nاعتبار: ۵ دقیقه', cfg.sender)
        ok = result.ok is True
    except Exception:
        ok = False
        result = None
    with transaction.atomic():
        PhoneLoginChallenge.objects.filter(pk=slot.pk, request_id=request_id).update(sent=ok)
        raw = getattr(result, 'raw', None)
        returned = raw.get('return') if isinstance(raw, dict) else None
        rejection = returned.get('status') if isinstance(returned, dict) else None
        # Only an explicit API rejection releases the paid-attempt reservation.
        rejected = type(rejection) is int and 400 <= rejection < 500
        reserved = not ok and not rejected
        log.meta.update(login_cost_reserved=reserved,
            delivery_state='sent' if ok else 'unknown' if reserved else 'rejected')
        log.status = 'sent' if ok else 'failed'
        log.error = '' if ok else ('نتیجه ارسال نامشخص است؛ سهم هزینه حفظ شد.' if reserved else 'درخواست ارسال توسط ارائه‌دهنده رد شد.')
        log.provider_message_id = str(result.message_id or '')[:64] if result else ''
        log.cost = getattr(result, "cost", None) if result else None
        log.save(update_fields=['status', 'error', 'provider_message_id', 'cost', 'meta', 'updated_at'])
    if not ok:
        raise LoginUnavailable()
    return {'request_id': str(request_id), 'expires_in': 300, 'resend_after': 60, 'channel': channel}


def consume_code(data, bind_user_id):
    """All credential changes and code consumption commit together."""
    invalid = {'detail': 'کد نادرست، مصرف‌شده یا منقضی است؛ دوباره درخواست کد کنید.'}
    with transaction.atomic():
        locked_enabled()
        cfg = MessagingSettings.objects.select_for_update().get(pk=MessagingSettings.load().pk)
        slot = PhoneLoginChallenge.objects.select_for_update().filter(request_id=data['request_id']).first()
        if not slot or slot.bind_user_id != bind_user_id or not slot.sent or slot.consumed or slot.expires_at <= timezone.now() or slot.attempts >= 5:
            return Response(invalid, status=400)
        if not ready(cfg, slot.delivery_channel):
            raise LoginUnavailable()
        slot.attempts += 1
        valid = check_password(data['code'], slot.code_hash)
        slot.consumed = valid
        slot.save(update_fields=['attempts', 'consumed'])
        if not valid:
            return Response(invalid, status=400)
        identity = PhoneLoginIdentity.objects.filter(phone=slot.phone).first()
        if bind_user_id:
            user = User.objects.select_for_update().get(pk=bind_user_id)
            own = PhoneLoginIdentity.objects.filter(user=user).first()
            if (identity and identity.user_id != user.pk) or (own and own.phone != slot.phone):
                return Response({'detail': 'این شماره یا حساب قبلاً متصل شده است؛ تغییر آن نیاز به بررسی پشتیبانی دارد.'}, status=409)
            if not user.is_active:
                return Response({'detail': 'حساب غیرفعال است.'}, status=403)
            PhoneLoginIdentity.objects.get_or_create(phone=slot.phone, defaults={'user': user})
            Profile.objects.update_or_create(user=user, defaults={'phone': slot.phone})
            return Response({'ok': True, 'phone': slot.phone})
        if identity:
            user = User.objects.select_for_update().get(pk=identity.user_id)
        else:
            # Old profile phones have never been ownership-verified: no automatic linking.
            if any(normalize_phone(str(value or '').translate(DIGITS)) == slot.phone
                   for value in Profile.objects.exclude(phone__isnull=True).exclude(phone='').values_list('phone', flat=True).iterator()):
                return Response({'detail': 'برای اتصال شماره به حساب قبلی، با رمز عبور وارد شوید و در ویرایش حساب، شماره را تأیید کنید.'}, status=409)
            user = User.objects.create_user(username='mobile_' + uuid.uuid4().hex, password=None, is_active=True)
            PhoneLoginIdentity.objects.create(phone=slot.phone, user=user)
            Profile.objects.update_or_create(user=user, defaults={'phone': slot.phone})
        if not user.is_active:
            return Response({'detail': 'حساب غیرفعال است.'}, status=403)
        refresh = RefreshToken.for_user(user)
        return Response({'access': str(refresh.access_token), 'refresh': str(refresh),
            'user': {'id': user.pk, 'username': user.username, 'email': user.email, 'is_active': user.is_active}})


class MobileCodeView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    binding = False
    def post(self, request):
        enabled()
        serializer = CodeInput(data=request.data); serializer.is_valid(raise_exception=True)
        budget('issue-ip', BaseThrottle().get_ident(request), 3600, 10)
        try:
            return Response(issue_code(serializer.validated_data['phone'], request.user.pk if self.binding else None, serializer.validated_data['channel']))
        except IntegrityError:
            raise LoginUnavailable() from None


class MobileVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    binding = False
    def post(self, request):
        enabled()
        serializer = VerifyInput(data=request.data); serializer.is_valid(raise_exception=True)
        budget('verify-ip', BaseThrottle().get_ident(request), 60, 30)
        try:
            return consume_code(serializer.validated_data, request.user.pk if self.binding else None)
        except IntegrityError:
            return Response({'detail': 'اتصال شماره تغییر کرده است؛ دوباره تلاش کنید.'}, status=409)


class BindCodeView(MobileCodeView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    binding = True


class BindVerifyView(MobileVerifyView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    binding = True


class MobileBindingView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        phone = PhoneLoginIdentity.objects.filter(user=request.user).values_list('phone', flat=True).first()
        return Response({'phone': phone})


class MobileChannelsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def get(self, request):
        return Response({'channels': channels(MessagingSettings.load()) if SiteSettings.load().sms_login_enabled else []})
