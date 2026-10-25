"""Private pull delivery: a claim is never automatically redelivered."""
import hashlib
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GoogleRelayJob, MessagingSettings, OutboundMessage

UNKNOWN_ERROR = 'نتیجه ارسال گوگل نامشخص است؛ کانال را بررسی کنید. پیام خودکار دوباره ارسال نمی‌شود.'


class RelayIdentity:
    is_authenticated = True


class RelayAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return 'Bearer'

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        configured = MessagingSettings.load().market_google_relay_key_hash
        if len(parts) != 2 or parts[0] != b'Bearer' or len(parts[1]) != 64 or not configured:
            raise AuthenticationFailed('اتصال مجاز نیست.')
        if not secrets.compare_digest(hashlib.sha256(parts[1]).hexdigest(), configured):
            raise AuthenticationFailed('اتصال مجاز نیست.')
        return RelayIdentity(), None


def expire_claims():
    with transaction.atomic():
        for job in GoogleRelayJob.objects.select_for_update().filter(status='claimed', claimed_until__lt=timezone.now()):
            job.status = 'unknown'
            job.result = {'status': 'unknown', 'message_id': ''}
            job.save(update_fields=['status', 'result'])
            OutboundMessage.objects.filter(pk=job.outbound_id, status='queued').update(error=UNKNOWN_ERROR)


class RelayClaimView(APIView):
    authentication_classes = [RelayAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cfg = MessagingSettings.load()
        if cfg.market_telegram_transport != 'google':
            return Response({'detail': 'مسیر گوگل فعال نیست.'}, status=409)
        expire_claims()
        MessagingSettings.objects.filter(pk=cfg.pk).update(market_google_relay_last_poll_at=timezone.now())
        with transaction.atomic():
            job = GoogleRelayJob.objects.select_for_update().filter(status='pending').order_by('created_at', 'id').first()
            if not job:
                return Response({'job': None}, headers={'Cache-Control': 'no-store'})
            receipt = secrets.token_urlsafe(32)
            job.receipt_hash = hashlib.sha256(receipt.encode()).hexdigest()
            job.status = 'claimed'
            job.claimed_until = timezone.now() + timedelta(minutes=10)
            job.save(update_fields=['receipt_hash', 'status', 'claimed_until'])
            outbound = job.outbound
            return Response({'job': {'id': str(job.pk), 'receipt': receipt, 'chat_id': outbound.recipient,
                'text': outbound.body, 'expires_at': job.claimed_until.isoformat()}}, headers={'Cache-Control': 'no-store'})


class RelayAckSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    receipt = serializers.CharField(max_length=128)
    status = serializers.ChoiceField(choices=['sent', 'failed', 'unknown'])
    message_id = serializers.RegexField(r'^[1-9][0-9]{0,19}$', required=False, allow_blank=True, default='')

    def validate(self, data):
        if data['status'] == 'sent' and not data['message_id']:
            raise serializers.ValidationError('شناسه پیام الزامی است.')
        if data['status'] != 'sent':
            data['message_id'] = ''
        return data


class RelayAckView(APIView):
    authentication_classes = [RelayAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RelayAckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = {'status': data['status'], 'message_id': data['message_id']}
        with transaction.atomic():
            job = GoogleRelayJob.objects.select_for_update().filter(pk=data['id']).first()
            if not job or not job.receipt_hash or not secrets.compare_digest(job.receipt_hash, hashlib.sha256(data['receipt'].encode()).hexdigest()):
                return Response({'detail': 'رسید معتبر نیست.'}, status=409)
            if job.status != 'claimed':
                if job.status == data['status'] and job.result == result:
                    return Response({'ok': True})
                return Response({'detail': 'این تلاش پایان یافته است؛ کانال را بررسی کنید.'}, status=409)
            outbound = OutboundMessage.objects.select_for_update().get(pk=job.outbound_id)
            job.status = data['status']
            job.result = result
            job.save(update_fields=['status', 'result'])
            outbound.status = {'sent': 'sent', 'failed': 'failed', 'unknown': 'queued'}[data['status']]
            outbound.provider_message_id = data['message_id']
            outbound.error = '' if data['status'] == 'sent' else (
                'گوگل ارسال را انجام نداد یا تلگرام درخواست را رد کرد؛ مقصد و دسترسی ربات را بررسی کنید.' if data['status'] == 'failed' else UNKNOWN_ERROR)
            outbound.save(update_fields=['status', 'provider_message_id', 'error', 'updated_at'])
        return Response({'ok': True})
