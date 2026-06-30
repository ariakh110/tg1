from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrActiveAdminRole
from customers.models import Customer

from . import service
from .models import MessagingSettings, OutboundMessage
from .serializers import MessagingSettingsSerializer, OutboundMessageSerializer

MAX_BODY_LEN = 900  # سقفِ کاوه‌نگار برای کلِ متنِ پیامک

# نگاشتِ کدِ عددیِ وضعیتِ کاوه‌نگار به وضعیتِ داخلیِ ما (جدولِ وضعیتِ پیامک‌ها).
KAVENEGAR_STATUS_MAP = {
    1: OutboundMessage.STATUS_QUEUED,    # در صف ارسال
    2: OutboundMessage.STATUS_QUEUED,    # زمان‌بندی‌شده
    4: OutboundMessage.STATUS_SENT,      # ارسال به مخابرات
    5: OutboundMessage.STATUS_SENT,      # ارسال به مخابرات
    6: OutboundMessage.STATUS_FAILED,    # خطا در ارسال
    10: OutboundMessage.STATUS_DELIVERED,  # رسیده به گیرنده
    11: OutboundMessage.STATUS_FAILED,   # نرسیده به گیرنده
    13: OutboundMessage.STATUS_FAILED,   # لغو شده
    14: OutboundMessage.STATUS_FAILED,   # بلاک‌شده
    100: OutboundMessage.STATUS_FAILED,  # شناسهٔ نامعتبر
}


class MessagingSettingsView(APIView):
    """خواندن/به‌روزرسانیِ تنظیماتِ پیام‌رسانی (فقط ادمین)."""

    permission_classes = [IsAdminOrActiveAdminRole]
    admin_section = "messaging"

    def get(self, request):
        return Response(MessagingSettingsSerializer(MessagingSettings.load()).data)

    def patch(self, request):
        cfg = MessagingSettings.load()
        serializer = MessagingSettingsSerializer(cfg, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MessagingSettingsSerializer(cfg).data)


class MessagingSendView(APIView):
    """ارسالِ یک پیامک به یک مشتری (customer_id) یا یک شماره (recipient) — فقط ادمین."""

    permission_classes = [IsAdminOrActiveAdminRole]
    admin_section = "messaging"

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        message = str(data.get("message", "")).strip()[:MAX_BODY_LEN]
        if not message:
            return Response({"detail": "متنِ پیام خالی است."}, status=status.HTTP_400_BAD_REQUEST)

        customer = None
        recipient = str(data.get("recipient", "")).strip()
        customer_id = data.get("customer_id")
        if customer_id:
            customer = Customer.objects.filter(pk=customer_id).first()
            if not customer:
                return Response({"detail": "مشتری یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
            recipient = customer.phone
        if not recipient:
            return Response({"detail": "گیرنده (customer_id یا recipient) لازم است."}, status=status.HTTP_400_BAD_REQUEST)

        channel = str(data.get("channel", OutboundMessage.CHANNEL_SMS)).strip() or OutboundMessage.CHANNEL_SMS
        if channel == OutboundMessage.CHANNEL_BALE:
            msg = service.send_bale(recipient, message, customer=customer, created_by=request.user)
        else:
            msg = service.send_sms(recipient, message, customer=customer, created_by=request.user)
        return Response(OutboundMessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class MessagingBulkSendView(APIView):
    """ارسالِ یک متن به یک سگمنت از مشتریان: با customer_ids یا فیلترِ stage/source/is_active — فقط ادمین."""

    permission_classes = [IsAdminOrActiveAdminRole]
    admin_section = "messaging"

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        message = str(data.get("message", "")).strip()[:MAX_BODY_LEN]
        if not message:
            return Response({"detail": "متنِ پیام خالی است."}, status=status.HTTP_400_BAD_REQUEST)

        ids = data.get("customer_ids") or []
        if ids:
            qs = Customer.objects.filter(pk__in=ids)
        else:
            qs = Customer.objects.filter(is_active=True)
            for f in ("stage", "source"):
                if data.get(f):
                    qs = qs.filter(**{f: data[f]})
        qs = qs.exclude(phone="")
        if not qs.exists():
            return Response({"detail": "هیچ مشتریِ منطبقی یافت نشد."}, status=status.HTTP_400_BAD_REQUEST)

        channel = str(data.get("channel", OutboundMessage.CHANNEL_SMS)).strip() or OutboundMessage.CHANNEL_SMS
        summary = service.send_bulk(qs, message, channel=channel, created_by=request.user)
        summary.pop("messages", None)  # خلاصه برگردان، نه همهٔ ردیف‌ها
        return Response(summary, status=status.HTTP_201_CREATED)


class MessagingNotifyStepView(APIView):
    """ارسالِ پیامکِ یک مرحله از خرید به مشتری (فروشِ مستقیم) — فقط ادمین."""

    permission_classes = [IsAdminOrActiveAdminRole]
    admin_section = "messaging"

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        customer = Customer.objects.filter(pk=data.get("customer_id")).first()
        if not customer:
            return Response({"detail": "مشتری یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        step = str(data.get("step", "")).strip()
        if step not in service.PURCHASE_STEPS:
            return Response(
                {"detail": "مرحلهٔ نامعتبر.", "valid_steps": list(service.PURCHASE_STEPS.keys())},
                status=status.HTTP_400_BAD_REQUEST,
            )
        amount = data.get("amount")
        msg = service.notify_purchase_step(
            customer, step, order_no=str(data.get("order_no", "")).strip(),
            amount=int(amount) if amount not in (None, "") else None,
            created_by=request.user,
        )
        return Response(OutboundMessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class MessagingTestAlertView(APIView):
    """ارسالِ یک پیامِ آزمایشی به کانال‌های اطلاع‌رسانیِ ادمین (تلگرام/پیامک) — فقط ادمین.

    برای راستی‌آزماییِ اتصالِ ربات/شماره پس از وارد‌کردنِ توکن و آیدی.
    """

    permission_classes = [IsAdminOrActiveAdminRole]
    admin_section = "messaging"

    def post(self, request):
        messages = service.notify_admin(
            "🔔 پیامِ آزمایشی",
            ["این یک پیامِ آزمایشی از پنلِ کاوکس است.", "اگر این را می‌بینی، اطلاع‌رسانی فعال است."],
        )
        return Response(
            {
                "sent": [OutboundMessageSerializer(m).data for m in messages],
                "summary": [f"{m.get_channel_display()} → {m.recipient or '—'}: {m.get_status_display()}" for m in messages],
            },
            status=status.HTTP_201_CREATED,
        )


class _KavenegarWebhook(APIView):
    """پایهٔ وب‌هوک‌های ورودیِ کاوه‌نگار: عمومی (بدونِ لاگین/CSRF)، با کلیدِ مخفی در مسیر."""

    permission_classes = [AllowAny]
    authentication_classes = []  # بدونِ session/CSRF؛ اعتبارسنجی با کلیدِ مخفیِ مسیر

    def _params(self, request):
        data = {}
        if isinstance(getattr(request, "data", None), dict):
            data.update(request.data)
        data.update(request.query_params.dict())
        return data

    def _authorized(self, secret):
        cfg = MessagingSettings.load()
        return bool(cfg.webhook_secret) and secret == cfg.webhook_secret


class KavenegarStatusWebhook(_KavenegarWebhook):
    """دریافتِ رسیدِ وضعیتِ پیامک (Status Callback) و به‌روزرسانیِ لاگ بر اساسِ messageid."""

    def get(self, request, secret):
        return self.post(request, secret)

    def post(self, request, secret):
        if not self._authorized(secret):
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
        p = self._params(request)
        mid = str(p.get("messageid") or p.get("messageId") or "").strip()
        raw_status = p.get("status")
        if mid and raw_status not in (None, ""):
            try:
                mapped = KAVENEGAR_STATUS_MAP.get(int(raw_status))
            except (TypeError, ValueError):
                mapped = None
            if mapped:
                OutboundMessage.objects.filter(provider_message_id=mid).update(status=mapped)
        return Response({"ok": True})


class KavenegarIncomingWebhook(_KavenegarWebhook):
    """دریافتِ پیامکِ ورودیِ مشتری (Receive Callback) و ثبت روی تایم‌لاینِ مشتریِ متناظر."""

    def get(self, request, secret):
        return self.post(request, secret)

    def post(self, request, secret):
        if not self._authorized(secret):
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
        p = self._params(request)
        sender = str(p.get("from") or "").strip()
        text = str(p.get("message") or "").strip()
        if sender and text:
            service.log_incoming_sms(sender, text, raw=p)
        return Response({"ok": True})


class BaleSetWebhookView(APIView):
    """ثبتِ آدرسِ وب‌هوکِ بله روی بک‌اند (تا ربات دوطرفه آپدیت‌ها را بگیرد) — فقط ادمین."""

    permission_classes = [IsAdminOrActiveAdminRole]
    admin_section = "messaging"

    def post(self, request):
        from .providers import telegram

        cfg = MessagingSettings.load()
        if not (cfg.telegram_bot_token or "").strip():
            return Response({"detail": "اول توکنِ ربات را ذخیره کن."}, status=status.HTTP_400_BAD_REQUEST)
        secret = cfg.webhook_secret
        url = (request.data.get("url") if isinstance(request.data, dict) else "") or ""
        url = url.strip() or f"https://{request.get_host()}/api/messaging/bale/webhook/{secret}/"
        result = telegram.set_webhook(cfg.telegram_bot_token, url, base_url=cfg.telegram_api_base)
        info = telegram.get_webhook_info(cfg.telegram_bot_token, base_url=cfg.telegram_api_base)
        return Response(
            {"ok": result.ok, "url": url, "error": result.error, "info": info.raw},
            status=status.HTTP_200_OK if result.ok else status.HTTP_400_BAD_REQUEST,
        )


class BaleWebhookView(APIView):
    """دریافتِ آپدیت‌های ربات بله (عمومی؛ کلیدِ مخفی در مسیر). همیشه ۲۰۰ برمی‌گرداند."""

    permission_classes = [AllowAny]
    authentication_classes = []  # بدونِ session/CSRF؛ اعتبارسنجی با کلیدِ مخفیِ مسیر

    def post(self, request, secret):
        cfg = MessagingSettings.load()
        if not cfg.webhook_secret or secret != cfg.webhook_secret:
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
        update = request.data if isinstance(request.data, dict) else {}
        from .bale_bot import handle_update

        handle_update(update)
        return Response({"ok": True})


class OutboundMessageViewSet(viewsets.ReadOnlyModelViewSet):
    """لاگِ پیام‌های ارسالی (فقط ادمین) — تازه‌ترین اول، با فیلتر."""

    queryset = OutboundMessage.objects.select_related("customer").all()
    serializer_class = OutboundMessageSerializer
    permission_classes = [IsAdminOrActiveAdminRole]
    admin_section = "messaging"
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["channel", "status", "purpose", "customer"]
