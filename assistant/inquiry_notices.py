"""Durable private Bale outbox and per-admin site notices for verified intake."""
from datetime import timedelta
from urllib.parse import urlsplit
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from accounts.permissions import IsAdminOrActiveAdminRole
from messaging.models import MessagingSettings,OutboundMessage
from messaging.providers import telegram
from .models import PurchaseInquiryNotice,PurchaseInquiryNoticeRead

UNITS={'kg':'کیلوگرم','ton':'تن','branch':'شاخه','sheet':'ورق','piece':'عدد','meter':'متر'}


def bale_configured(cfg):
    return cfg.telegram_configured and cfg.telegram_api_base.strip().rstrip('/')=='https://tapi.bale.ai'


def private_targets(cfg):
    return list(dict.fromkeys(str(int(target)) for target in cfg.telegram_chat_ids
        if target.isascii() and target.isdigit() and int(target)>0))


def create_inquiry_notice(inquiry):
    cfg=MessagingSettings.load()
    state='pending' if cfg.notify_on_purchase_inquiry and bale_configured(cfg) and private_targets(cfg) else 'unconfigured' if cfg.notify_on_purchase_inquiry else 'disabled'
    targets={target:{'status':'pending'} for target in private_targets(cfg)} if state=='pending' else {}
    notice,_=PurchaseInquiryNotice.objects.get_or_create(inquiry=inquiry,defaults={'bale_status':state,'bale_deliveries':targets})
    return notice


def notice_message(inquiry,cfg):
    items=inquiry.requested_items or []
    lines=['🆕 استعلام خرید جدید',f'کد پیگیری: KX-Q-{inquiry.pk}',f'نام: {inquiry.contact_name or "—"}',
           f'موبایل: {inquiry.contact_phone}',f'شهر: {inquiry.city or "—"}',f'تعداد اقلام: {len(items) or 1}']
    for item in items[:5]:
        lines.append(f"• {item['category_name'][:60]} | {item['specification'][:150]} | {item['quantity']} {UNITS.get(item['unit'],item['unit'])}")
    if not items:lines.append(f'{inquiry.product} | {inquiry.size} | {inquiry.quantity}')
    if len(items)>5:lines.append(f'و {len(items)-5} قلم دیگر؛ فهرست کامل در پنل.')
    url=urlsplit(cfg.site_base_url)
    origin=f'https://{url.netloc}' if url.scheme=='https' and url.hostname and not url.username and not url.password else 'https://kavehmetal.com'
    lines.append(f'{origin}/admin/dashboard?panel=assistant&tab=inquiries&inquiry={inquiry.pk}')
    return '\n'.join(lines)


def _aggregate(deliveries):
    states=[value['status'] for value in deliveries.values()]
    if any(value in ('pending','sending') for value in states):return 'pending'
    if states and all(value=='sent' for value in states):return 'sent'
    if 'sent' in states:return 'partial'
    return 'unknown' if 'unknown' in states else 'skipped'


def dispatch_inquiry_notices():
    """At most30 events per tick. Sending/unknown attempts are never resent."""
    ids=list(PurchaseInquiryNotice.objects.filter(bale_status='pending').order_by('id').values_list('id',flat=True)[:30])
    for notice_id in ids:
        notice=PurchaseInquiryNotice.objects.get(pk=notice_id)
        for target in list(notice.bale_deliveries):
            with transaction.atomic():
                locked=PurchaseInquiryNotice.objects.select_for_update().get(pk=notice_id)
                attempt=locked.bale_deliveries[target]
                if attempt['status']=='sending':
                    started=parse_datetime(attempt.get('started_at',''))
                    if not started or started<timezone.now()-timedelta(minutes=10):attempt['status']='unknown'
                if attempt['status']!='pending':
                    locked.bale_status=_aggregate(locked.bale_deliveries);locked.save(update_fields=['bale_status','bale_deliveries']);continue
                cfg=MessagingSettings.load()
                if not cfg.notify_on_purchase_inquiry or not bale_configured(cfg) or target not in private_targets(cfg):
                    attempt['status']='skipped';locked.bale_status=_aggregate(locked.bale_deliveries);locked.save(update_fields=['bale_status','bale_deliveries']);continue
                attempt.update(status='sending',started_at=timezone.now().isoformat())
                locked.save(update_fields=['bale_deliveries'])
            text=notice_message(notice.inquiry,cfg)
            try:
                result=telegram.send_message(cfg.telegram_bot_token,target,text,base_url='https://tapi.bale.ai')
                sent=result.ok is True and bool(result.message_id)
                message_id=str(result.message_id) if sent else ''
            except Exception:
                sent=False;message_id=''
            with transaction.atomic():
                locked=PurchaseInquiryNotice.objects.select_for_update().get(pk=notice_id)
                locked.bale_deliveries[target].update(status='sent' if sent else 'unknown',message_id=message_id)
                locked.bale_status=_aggregate(locked.bale_deliveries)
                locked.save(update_fields=['bale_deliveries','bale_status'])
                OutboundMessage.objects.create(channel='telegram',provider='bale',purpose='admin_alert',recipient=target,body=text,
                    status='sent' if sent else 'failed',provider_message_id=message_id,
                    error='' if sent else 'نتیجه ارسال بله تأیید نشد؛ پیش از تلاش تازه مقصد را بررسی کنید.',
                    meta={'purchase_inquiry_id':notice.inquiry_id,'delivery_state':'sent' if sent else 'unknown'})
    return len(ids)


def unread_for(user):
    return PurchaseInquiryNotice.objects.exclude(reads__user=user)


class PurchaseNoticeFeed(APIView):
    permission_classes=[IsAdminOrActiveAdminRole]
    admin_section='assistant'

    def get(self,request):
        unread=unread_for(request.user)
        return Response({'unread_count':unread.count(),'results':[{
            'id':notice.pk,'inquiry_id':notice.inquiry_id,'reference':f'KX-Q-{notice.inquiry_id}',
            'item_count':len(notice.inquiry.requested_items) or 1,'title':'استعلام خرید جدید',
            'created_at':notice.created_at.isoformat(),'bale_status':notice.bale_status
        } for notice in unread.select_related('inquiry').order_by('-id')[:20]]})


class PurchaseNoticeRead(APIView):
    permission_classes=[IsAdminOrActiveAdminRole]
    admin_section='assistant'

    def post(self,request,pk):
        notice=get_object_or_404(PurchaseInquiryNotice,pk=pk)
        PurchaseInquiryNoticeRead.objects.get_or_create(notice=notice,user=request.user)
        return Response({'ok':True,'unread_count':unread_for(request.user).count()})
