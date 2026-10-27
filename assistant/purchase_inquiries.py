"""Public purchase inquiries: verified phone, bounded SMS cost, no AI calls."""
import hashlib
import json
import secrets
import time
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.cache import caches
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException, Throttled
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from customers.services import normalize_phone, upsert_lead
from messaging.models import MessagingSettings, OutboundMessage
from messaging.providers import kavenegar
from products.models import ProductSpecification, ProductCategory
from .models import AssistantInquiry, PurchaseInquiryChallenge

PRODUCTS = {'sheet': 'ورق سیاه', 'rebar': 'میلگرد'}
MAX_ITEMS = 50
UNITS = {'kg':'کیلوگرم','ton':'تن','branch':'شاخه','sheet':'ورق','piece':'عدد','meter':'متر'}
DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


class InquiryUnavailable(APIException):
    status_code = 503
    default_detail = 'ارسال کد تأیید فعلاً در دسترس نیست؛ کمی بعد تلاش کنید یا با فروش تماس بگیرید.'


class InquiryRegistrationUnavailable(APIException):
    status_code = 503
    default_detail = 'ثبت لیست فعلاً انجام نشد؛ اطلاعات شما حفظ شده است. دوباره تأیید کنید.'


def budget(scope, identity, seconds, limit, *, cooldown=False):
    digest = hashlib.sha256(str(identity).encode()).hexdigest()
    now = int(time.time())
    ttl = seconds if cooldown else seconds - now % seconds
    key = f'purchase-inquiry:v1:{scope}:{digest}' + ('' if cooldown else f':{now // seconds}')
    try:
        cache = caches['authentication']
        added = cache.add(key, 1, timeout=ttl + 1)
        count = 1 if added else (limit + 1 if cooldown else cache.incr(key))
    except Exception:
        raise InquiryUnavailable() from None
    if count > limit:
        raise Throttled(wait=ttl, detail='تعداد تلاش‌ها زیاد است؛ پس از زمان اعلام‌شده دوباره تلاش کنید.')


def available_categories():
    """Resolve paths/kinds without querying ancestors for each option."""
    categories=list(ProductCategory.objects.all().order_by('tree_id','lft'))
    by_id={category.pk:category for category in categories}
    result=[]
    for category in categories:
        chain=[]; current=category
        while current:
            chain.append(current)
            current=by_id.get(current.parent_id)
        if not category.code or any(not node.is_active for node in chain):
            continue
        kind=next((node.product_kind for node in chain if node.product_kind),'')
        result.append({'id':category.pk,'code':category.code,'name':category.name,
            'path':' / '.join(node.name for node in reversed(chain)),'kind':kind,
            'default_unit':'branch' if kind in ('rebar','beam') else 'kg'})
    return result


class RequestedItemSerializer(serializers.Serializer):
    category_code=serializers.CharField(max_length=80)
    specification=serializers.CharField(max_length=200)
    quantity=serializers.DecimalField(max_digits=11,decimal_places=2,min_value=Decimal('0.01'),max_value=100000000)
    unit=serializers.ChoiceField(choices=list(UNITS))

    def to_internal_value(self,data):
        if isinstance(data,dict):
            data={**data,'quantity':str(data.get('quantity','')).translate(DIGITS).replace('٫','.')}
        return super().to_internal_value(data)


class PurchaseInquirySerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    product = serializers.ChoiceField(choices=list(PRODUCTS),required=False)
    size_mm = serializers.DecimalField(max_digits=8, decimal_places=3, min_value=Decimal('0.01'), max_value=1000,required=False)
    quantity_kg = serializers.DecimalField(max_digits=11, decimal_places=2, min_value=1, max_value=100000000,required=False)
    items=RequestedItemSerializer(many=True,required=False,allow_empty=False,max_length=MAX_ITEMS)
    phone = serializers.CharField(max_length=30)
    name = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')
    city = serializers.CharField(max_length=80, required=False, allow_blank=True, default='')
    source_path = serializers.CharField(max_length=300, required=False, default='/', allow_blank=True)
    website = serializers.CharField(required=False, allow_blank=True, default='')
    resend = serializers.BooleanField(required=False, default=False)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = {key: value.translate(DIGITS) if isinstance(value, str) and key in {'phone', 'size_mm', 'quantity_kg'} else value for key, value in data.items()}
        return super().to_internal_value(data)

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if len(phone) != 11 or not phone.startswith('09') or not phone.isascii() or not phone.isdigit():
            raise serializers.ValidationError('شماره موبایل معتبر وارد کنید.')
        return phone

    def validate(self, data):
        if data.pop('website', ''):
            raise serializers.ValidationError('درخواست معتبر نیست.')
        legacy={'product','size_mm','quantity_kg'}
        if 'items' in data:
            if legacy.intersection(data):
                raise serializers.ValidationError('مشخصات تکی و لیست کالا را هم‌زمان ارسال نکنید.')
            categories={item['code']:item for item in available_categories()}
            for index,item in enumerate(data['items']):
                category=categories.get(item['category_code'])
                if not category:
                    raise serializers.ValidationError({'items':f'قلم {index+1}: دسته‌بندی فعال و معتبر انتخاب کنید.'})
                item['category_name']=category['name']
        elif not legacy.issubset(data):
            raise serializers.ValidationError('حداقل یک قلم کالا با مشخصات و مقدار وارد کنید.')
        return data


def send_purchase_code(phone, code, request_id):
    # Reserve a redacted log row before the paid request; never store code/raw provider data.
    with transaction.atomic():
        cfg = MessagingSettings.objects.select_for_update().get(pk=MessagingSettings.load().pk)
        if not cfg.is_configured:
            raise InquiryUnavailable()
        from messaging.service import _today_sent_count
        if cfg.daily_send_cap and _today_sent_count() >= cfg.daily_send_cap:
            raise InquiryUnavailable()
        log = OutboundMessage.objects.create(channel='sms', provider='kavenegar', recipient=phone,
            purpose='otp', body='کد تأیید استعلام خرید (محرمانه)', meta={'purchase_request_id': str(request_id)})
    try:
        if cfg.purchase_inquiry_otp_template:
            result = kavenegar.send_lookup(cfg.kavenegar_api_key, phone, cfg.purchase_inquiry_otp_template, code)
        else:
            result = kavenegar.send_sms(cfg.kavenegar_api_key, phone,
                f'کد تأیید استعلام خرید کاوه‌متال: {code}\nاعتبار: ۵ دقیقه', cfg.sender)
        ok = result.ok is True
    except Exception:
        ok = False
        result = None
    log.status = 'sent' if ok else 'failed'
    log.error = '' if ok else 'ارسال کد تأیید انجام نشد یا نتیجه تأیید نشد.'
    log.provider_message_id = str(result.message_id or '')[:64] if result else ''
    log.cost = result.cost if result else None
    log.save(update_fields=['status', 'error', 'provider_message_id', 'cost', 'updated_at'])
    return ok


def challenge_response(challenge):
    return {'request_id': str(challenge.pk), 'expires_in': max(0, int((challenge.expires_at-timezone.now()).total_seconds())),
        'resend_after': max(0, 60-int((timezone.now()-challenge.last_sent_at).total_seconds())) if challenge.last_sent_at else 60}


class PurchaseOptionsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        active = ProductSpecification.objects.filter(product__is_active=True)
        sizes = {}
        for kind, field in [('sheet', 'thickness_mm'), ('rebar', 'diameter_mm')]:
            rows = active.filter(material_type=kind, **{field+'__gt': 0})
            if kind == 'sheet':
                rows = rows.filter(surface_finish='black')
            sizes[kind] = [format(value.normalize(), 'f') for value in rows.order_by(field).values_list(field, flat=True).distinct()[:100]]
        return Response({'sizes': sizes,'categories':available_categories(),
            'units':[{'value':key,'label':label} for key,label in UNITS.items()],'max_items':MAX_ITEMS})


class PurchaseCodeView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PurchaseInquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        budget('request-minute', BaseThrottle().get_ident(request), 60, 5)
        budget('request-day', BaseThrottle().get_ident(request), 86400, 30)
        if not MessagingSettings.load().is_configured:
            raise InquiryUnavailable()
        request_id = data.pop('request_id')
        resend = data.pop('resend')
        payload = json.loads(json.dumps(data,default=lambda value:format(value.normalize(),'f') if isinstance(value,Decimal) else str(value)))
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with transaction.atomic():
            challenge, _ = PurchaseInquiryChallenge.objects.get_or_create(pk=request_id,
                defaults={'phone': data['phone'], 'payload': payload, 'payload_hash': fingerprint, 'expires_at': timezone.now()})
            challenge = PurchaseInquiryChallenge.objects.select_for_update().get(pk=request_id)
            if challenge.payload_hash != fingerprint or challenge.inquiry_id:
                return Response({'detail': 'مشخصات درخواست تغییر کرده است؛ درخواست تازه بسازید.'}, status=409)
            if not resend and challenge.delivery == 'sent' and challenge.expires_at > timezone.now():
                return Response(challenge_response(challenge))
            if challenge.last_sent_at and timezone.now()-challenge.last_sent_at < timedelta(seconds=60):
                raise Throttled(wait=60)
            budget('phone-cooldown', data['phone'], 60, 1, cooldown=True)
            budget('phone-hour', data['phone'], 3600, 3)
            budget('phone-day', data['phone'], 86400, 10)
            budget('sms-global', 'all', 86400, int(getattr(settings, 'PURCHASE_INQUIRY_SMS_DAILY_LIMIT', 200)))
            code = f'{secrets.randbelow(1000000):06d}'
            challenge.otp_hash = make_password(code)
            challenge.last_sent_at = timezone.now()
            challenge.expires_at = timezone.now()+timedelta(minutes=5)
            challenge.attempts = 0
            challenge.delivery = 'sending'
            challenge.save()
        ok = send_purchase_code(data['phone'], code, request_id)
        PurchaseInquiryChallenge.objects.filter(pk=request_id).update(delivery='sent' if ok else 'failed')
        if not ok:
            raise InquiryUnavailable()
        return Response(challenge_response(challenge))


class PurchaseVerifySerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    code = serializers.RegexField(r'^[0-9]{6}$')

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = {**data, 'code': str(data.get('code', '')).translate(DIGITS)}
        return super().to_internal_value(data)


class PurchaseVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PurchaseVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        budget('verify', BaseThrottle().get_ident(request), 60, 20)
        data = serializer.validated_data
        with transaction.atomic():
            challenge = PurchaseInquiryChallenge.objects.select_for_update().filter(pk=data['request_id']).first()
            if not challenge or challenge.delivery != 'sent' or challenge.attempts >= 5 or (not challenge.inquiry_id and challenge.expires_at <= timezone.now()):
                return Response({'detail': 'کد منقضی یا نامعتبر است؛ دوباره کد بگیرید.'}, status=400)
            if not check_password(data['code'], challenge.otp_hash):
                challenge.attempts += 1
                challenge.save(update_fields=['attempts'])
                return Response({'detail': 'کد تأیید درست نیست.'}, status=400)
            if challenge.inquiry_id:
                return Response({'ok': True, 'reference': f'KX-Q-{challenge.inquiry_id}'})
            payload = challenge.payload
            items=payload.get('items',[])
            if items:
                product=items[0]['category_name'][:120] if len(items)==1 else 'لیست خرید چندقلمی'
                size=items[0]['specification'][:60] if len(items)==1 else ''
                quantity=(items[0]['quantity']+' '+UNITS[items[0]['unit']]) if len(items)==1 else f'{len(items)} قلم کالا'
                raw_text='\n'.join(f"{i+1}. {item['category_name']} | {item['specification']} | {item['quantity']} {UNITS[item['unit']]}" for i,item in enumerate(items))
            else:
                product=PRODUCTS[payload['product']];size=payload['size_mm']+' میلی‌متر'
                quantity=payload['quantity_kg']+' کیلوگرم';raw_text=''
            inquiry = AssistantInquiry.objects.create(product=product,size=size,quantity=quantity,requested_items=items,
                city=payload['city'], contact_name=payload['name'], contact_phone=challenge.phone,
                note='فرم استعلام خرید؛ موبایل با پیامک تأیید شده', raw_text='فرم استعلام خرید از '+payload['source_path']+'\n'+raw_text)
            upsert_lead(challenge.phone, name=payload['name'], city=payload['city'])
            if items:
                # Persist the new list and its sales opportunity in one transaction.
                # The existing post-commit signal remains an idempotent projection.
                from customers.opportunities import sync_assistant_inquiry_opportunity
                try:
                    sync_assistant_inquiry_opportunity(inquiry)
                except Exception:
                    raise InquiryRegistrationUnavailable() from None
            challenge.inquiry = inquiry
            challenge.save(update_fields=['inquiry'])
        return Response({'ok': True, 'reference': f'KX-Q-{inquiry.pk}'}, status=201)
