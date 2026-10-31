"""Recurring posts: immutable date receipts; no retry after network ambiguity."""
import hashlib
import re
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.permissions import IsAdminOrActiveAdminRole
from core.models import SiteSettings
from products.external_markets import gregorian_to_jalali
from .models import ChannelPostSchedule, ChannelPostRun, MarketChannelDraft, MessagingSettings
from .market_channels import publish_draft, draft_payload

TEHRAN = ZoneInfo('Asia/Tehran')
DAYS = ['دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه', 'شنبه', 'یکشنبه']
TOKENS = {'jalali_date', 'weekday', 'site_name'}


def render(body, now=None):
    local = (now or timezone.now()).astimezone(TEHRAN)
    values = {'jalali_date': gregorian_to_jalali(local.date()).translate(str.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹')),
              'weekday': DAYS[local.weekday()], 'site_name': SiteSettings.load().site_name or 'کاوه‌متال'}
    if set(re.findall(r'{{(.*?)}}', body)) - TOKENS:
        raise serializers.ValidationError({'body': 'فقط متغیرهای تاریخ، روز و نام سایت مجازند.'})
    for key, value in values.items():
        body = body.replace('{{'+key+'}}', value)
    if not body.strip() or len(body) > 4000:
        raise serializers.ValidationError({'body': 'متن نهایی باید بین ۱ تا ۴۰۰۰ نویسه باشد.'})
    return body.strip()


class ScheduleSerializer(serializers.ModelSerializer):
    body = serializers.CharField(max_length=3500, trim_whitespace=True)
    weekdays = serializers.ListField(child=serializers.IntegerField(min_value=0,max_value=6), min_length=1,max_length=7)
    platforms = serializers.ListField(child=serializers.ChoiceField(choices=['bale','telegram']),min_length=1,max_length=2)
    class Meta:
        model = ChannelPostSchedule
        fields = ['id','title','body','send_time','weekdays','platforms','enabled','updated_at']
        read_only_fields = ['id','updated_at']
    def validate(self, attrs):
        render(attrs.get('body', self.instance.body if self.instance else ''))
        for key in ('weekdays','platforms'):
            if key in attrs and len(set(attrs[key])) != len(attrs[key]):
                raise serializers.ValidationError({key:'گزینه تکراری مجاز نیست.'})
        return attrs


def run_payload(run):
    data = draft_payload(run.draft)
    publications = data['publications']
    # Every destination has a visible outcome, including failures before provider calls.
    for platform in run.draft.texts:
        if platform not in publications:
            publications[platform] = run.platform_errors.get(platform) or {
                'status': 'unknown' if run.status == 'unknown' else run.status,
                'error': run.error, 'message_id': ''}
    states = []
    for item in publications.values():
        state = item.get('relay_status') or item['status']
        if state == 'queued' and item.get('error'):
            state = 'unknown'
        states.append(state)
    status = run.status
    if 'unknown' in states:
        status = 'unknown'
    elif 'failed' in states or 'cancelled' in states:
        status = 'failed'
    elif any(state in ('queued','pending','claimed') for state in states):
        status = 'queued'
    elif states and all(state == 'sent' for state in states):
        status = 'sent'
    error = 'نتیجه یک کانال نامشخص است؛ کانال را بررسی کنید. تکرار خودکار انجام نمی‌شود.' if status == 'unknown' else run.error
    return {'id':run.pk,'title':run.draft.title,'date':run.local_date,'status':status,'error':error,
            'publications':publications,'text':run.draft.texts.get('bale') or run.draft.texts.get('telegram','')}


class ChannelPostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrActiveAdminRole]
    admin_section = 'messaging'
    serializer_class = ScheduleSerializer
    queryset = ChannelPostSchedule.objects.all()
    http_method_names = ['get','post','patch','head','options']
    pagination_class = None
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    @action(detail=False,methods=['post'])
    def preview(self, request):
        serializer = self.get_serializer(data=request.data);serializer.is_valid(raise_exception=True)
        return Response({'text':render(serializer.validated_data['body'])})
    @action(detail=False,methods=['get'])
    def history(self, request):
        expire_reserved(timezone.now())
        return Response([run_payload(run) for run in ChannelPostRun.objects.select_related('draft')[:30]])


def expire_reserved(now):
    ChannelPostRun.objects.filter(status='reserved',created_at__lt=now-timedelta(minutes=10)).update(
        status='unknown',error='اجرای قبلی متوقف شده؛ کانال را بررسی کنید. ارسال خودکار تکرار نمی‌شود.')


def due(schedule, local):
    minute = local.hour*60+local.minute
    target = schedule.send_time.hour*60+schedule.send_time.minute
    return schedule.enabled and local.weekday() in schedule.weekdays and 0 <= minute-target <= 30


def reserve(schedule_id, now):
    local = now.astimezone(TEHRAN)
    try:
        with transaction.atomic():
            cfg = MessagingSettings.objects.select_for_update().get(pk=MessagingSettings.load().pk)
            schedule = ChannelPostSchedule.objects.select_for_update().get(pk=schedule_id)
            if not cfg.channel_posts_enabled or not due(schedule,local) or ChannelPostRun.objects.filter(schedule=schedule,local_date=local.date()).exists():
                return None
            render_error = ''
            try:
                text = render(schedule.body,now)
            except serializers.ValidationError:
                # A site-name update may invalidate an earlier valid template. Record
                # the unsent source template and continue with other schedules.
                text = schedule.body
                render_error = 'متن نهایی پس از جایگزینی متغیرها معتبر نیست؛ قالب را پیش از نوبت بعدی اصلاح کنید.'
            draft = MarketChannelDraft.objects.create(
                fingerprint=hashlib.sha256(f'channel-post:{schedule.pk}:{local.date()}'.encode()).hexdigest(),
                report_date=local.date(),kind='recurring',product_group='',title=schedule.title,
                texts={p:text for p in schedule.platforms},targets={p:getattr(cfg,f'market_{p}_channel_id') for p in schedule.platforms},
                created_by=schedule.created_by)
            return ChannelPostRun.objects.create(schedule=schedule,local_date=local.date(),draft=draft,
                status='failed' if render_error else 'reserved',error=render_error,
                platform_errors={p:{'status':'failed','error':render_error,'message_id':''} for p in schedule.platforms} if render_error else {})
    except IntegrityError:
        return None  # Unique date key remains the final concurrent reservation guard.


def dispatch_due(now=None):
    now = now or timezone.now()
    expire_reserved(now)
    if not MessagingSettings.load().channel_posts_enabled:
        return {'processed':0}
    processed = 0
    # Bounded work: additional due rows are picked up on the next minute, never old days.
    for pk in ChannelPostSchedule.objects.filter(enabled=True).values_list('pk',flat=True):
        run = reserve(pk,now)
        if run is None:
            continue
        if run.status != 'failed':
            for platform in run.draft.texts:
                try:
                    # Validate and dispatch independently: a broken destination must
                    # never suppress a healthy channel's daily post.
                    publish_draft(run.draft,[platform],run.schedule.created_by)
                except (ValueError, serializers.ValidationError):
                    run.platform_errors[platform] = {'status':'failed','message_id':'',
                        'error':'تنظیمات این کانال کامل یا معتبر نیست؛ قبل از نوبت بعدی اصلاح کنید.'}
                except Exception:
                    run.platform_errors[platform] = {'status':'unknown','message_id':'',
                        'error':'نتیجه این کانال مشخص نیست؛ کانال را بررسی کنید. تکرار خودکار انجام نمی‌شود.'}
            summary = run_payload(run)
            run.status = summary['status']
            run.error = summary['error'] or ('یک کانال ارسال نشد؛ جزئیات مقصدها را بررسی کنید.' if run.status == 'failed' else '')
            run.save(update_fields=['status','error','platform_errors'])
        processed += 1
        if processed >= 5:
            break
    return {'processed':processed}
