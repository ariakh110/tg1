"""Account-owned purchase requests; authentication replaces guest SMS challenge."""
import hashlib
import json
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import PhoneLoginIdentity, Profile
from customers.services import normalize_phone
from .models import AccountPurchaseSubmission
from .purchase_inquiries import InquiryUnavailable, InquiryRegistrationUnavailable, DIGITS, MAX_ITEMS, RequestedItemSerializer, available_categories, budget, persist_purchase_inquiry


def account_contact(user):
    profile_phone = Profile.objects.filter(user=user).values_list('phone', flat=True).first()
    verified = PhoneLoginIdentity.objects.filter(user=user).values_list('phone', flat=True).first()
    phone = normalize_phone(str(profile_phone or '').translate(DIGITS))
    if len(phone) != 11 or not phone.startswith('09') or not phone.isascii() or not phone.isdigit():
        phone = verified or ''
    name = user.get_full_name().strip()
    if not name and not user.username.startswith('mobile_'):
        name = user.username
    return {'user_id': user.pk, 'phone': phone, 'name': name[:120], 'can_submit': bool(phone),
            'phone_verified': bool(phone and phone == verified)}


class AccountInquiryInput(serializers.Serializer):
    request_id = serializers.UUIDField()
    items = RequestedItemSerializer(many=True, allow_empty=False, max_length=MAX_ITEMS)
    city = serializers.CharField(required=False, allow_blank=True, default='', max_length=80)
    source_path = serializers.CharField(required=False, allow_blank=True, default='/account/inquiries', max_length=300)

    def validate(self, data):
        if set(self.initial_data) - set(self.fields):
            raise serializers.ValidationError('اطلاعات تماس و مالک درخواست از حساب شما خوانده می‌شود.')
        return data


class AccountView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class AccountInquiryContext(AccountView):
    def get(self, request):
        return Response(account_contact(request.user))


class AccountInquirySubmit(AccountView):
    def post(self, request):
        serializer = AccountInquiryInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = json.loads(json.dumps(serializer.validated_data, default=lambda value:
            format(value.normalize(), 'f') if isinstance(value, Decimal) else str(value)))
        request_id = payload.pop('request_id')
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with transaction.atomic():
            receipt, _ = AccountPurchaseSubmission.objects.get_or_create(pk=request_id,
                defaults={'user': request.user, 'payload_hash': fingerprint})
            receipt = AccountPurchaseSubmission.objects.select_for_update().get(pk=receipt.pk)
            if receipt.user_id != request.user.pk or receipt.payload_hash != fingerprint:
                return Response({'detail': 'شناسه درخواست معتبر نیست یا لیست تغییر کرده است؛ درخواست تازه بسازید.'}, status=409)
            if receipt.inquiry_id:
                return Response({'ok': True, 'reference': f'KX-Q-{receipt.inquiry_id}'})
            contact = account_contact(request.user)
            if not contact['can_submit']:
                raise serializers.ValidationError({'detail': 'ابتدا شماره تماس را در اطلاعات حساب تکمیل کنید.'})
            try:
                budget('account-submit-hour', request.user.pk, 3600, 30)
            except InquiryUnavailable:
                raise InquiryRegistrationUnavailable() from None
            categories = {row['code']: row for row in available_categories()}
            for index, item in enumerate(payload['items']):
                category = categories.get(item['category_code'])
                if not category:
                    raise serializers.ValidationError({'detail': f'قلم {index+1}: دسته‌بندی فعال انتخاب کنید.'})
                item['category_name'] = category['name']
            payload['name'] = contact['name']
            inquiry = persist_purchase_inquiry(payload, contact['phone'], user=request.user,
                note='ثبت توسط کاربر واردشده؛ شماره تماس از حساب، بدون تأیید پیامکی مجدد')
            receipt.inquiry = inquiry
            receipt.save(update_fields=['inquiry'])
        return Response({'ok': True, 'reference': f'KX-Q-{inquiry.pk}'}, status=201)


class AccountInquiryList(AccountView):
    def get(self, request):
        rows = AccountPurchaseSubmission.objects.filter(user=request.user, inquiry__isnull=False).select_related('inquiry').order_by('-created_at', '-id')
        pager = PageNumberPagination()
        pager.page_size = 20
        page = pager.paginate_queryset(rows, request, view=self)
        return pager.get_paginated_response([{
            'reference': f'KX-Q-{row.inquiry_id}', 'created_at': row.inquiry.created_at.isoformat(),
            'status': row.inquiry.status, 'product': row.inquiry.product,
            'items': row.inquiry.requested_items, 'city': row.inquiry.city,
        } for row in page])
