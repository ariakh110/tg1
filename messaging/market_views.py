from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.db.models import Max
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import IsFullAdminUser
from products.models import CommodityExchangeTrade
from .market_channels import PLATFORMS, draft_payload, generate_drafts, publish_draft
from .models import MarketChannelDraft


class MarketChannelDraftsView(APIView):
    permission_classes = [IsFullAdminUser]

    def get(self, request):
        return Response({"today": timezone.localdate().isoformat(),
            "latest_date": CommodityExchangeTrade.objects.aggregate(value=Max("trade_date"))["value"],
            "groups": list(CommodityExchangeTrade.objects.order_by("product_group").values_list("product_group", flat=True).distinct())})

    def post(self, request):
        try:
            date = parse_date(str(request.data.get("date", "")))
        except ValueError:
            date = None
        kind = request.data.get("kind", "item")
        if date is None or date > timezone.localdate() or kind not in {"item", "summary"}:
            return Response({"detail": "تاریخ یا نوع گزارش نامعتبر است."}, status=400)
        try:
            drafts = generate_drafts(date, str(request.data.get("group", "")), kind, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({"date": date.isoformat(), "results": [draft_payload(draft) for draft in drafts]})


class MarketChannelPublishView(APIView):
    permission_classes = [IsFullAdminUser]

    def get(self, request, pk):
        return Response(draft_payload(get_object_or_404(MarketChannelDraft, pk=pk)))

    def post(self, request, pk):
        platforms = request.data.get("platforms")
        if not isinstance(platforms, list) or not platforms or any(item not in PLATFORMS for item in platforms):
            return Response({"detail": "بله یا تلگرام را انتخاب کنید."}, status=400)
        draft = get_object_or_404(MarketChannelDraft, pk=pk)
        try:
            result = publish_draft(draft, list(dict.fromkeys(platforms)), request.user, retry_failed=request.data.get("retry_failed") is True)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(result)


class MarketTelegramConnectionView(APIView):
    permission_classes = [IsFullAdminUser]

    def post(self, request):
        from .models import MessagingSettings
        from .telegram_transport import test_mtproto, TelegramNotSent
        index = request.data.get("index", 0)
        if type(index) is not int:
            return Response({"detail": "شماره پراکسی معتبر نیست."}, status=400)
        try:
            return Response(test_mtproto(MessagingSettings.load(), index))
        except TelegramNotSent as exc:
            return Response({"detail": str(exc)}, status=400)
        except Exception:
            return Response({"detail": "تست اتصال ناموفق بود؛ تنظیمات و نصب وابستگی‌ها را بررسی کنید."}, status=400)


class MarketChannelResolveView(APIView):
    permission_classes = [IsFullAdminUser]

    def post(self, request, pk):
        from django.db import transaction
        from .models import MarketChannelPublication, OutboundMessage
        platform = request.data.get("platform")
        if platform not in PLATFORMS or request.data.get("confirm_not_delivered") is not True:
            return Response({"detail": "ابتدا بررسی کنید که پیام در کانال منتشر نشده باشد و آن را تأیید کنید."}, status=400)
        with transaction.atomic():
            draft = get_object_or_404(MarketChannelDraft.objects.select_for_update(), pk=pk)
            publication = get_object_or_404(MarketChannelPublication.objects.select_related("outbound"), draft=draft, platform=platform)
            outbound = publication.outbound
            # An active request may still be sending. Never release its claim.
            if outbound.status != OutboundMessage.STATUS_QUEUED or not outbound.error:
                return Response({"detail": "فقط ارسال نامشخصِ پایان‌یافته قابل بررسی است."}, status=400)
            outbound.status = OutboundMessage.STATUS_FAILED
            outbound.error = "ادمین پس از بررسی کانال، منتشر نشدن پیام را تأیید کرد؛ تلاش دوباره مجاز است."
            outbound.meta = {**(outbound.meta or {}), "not_delivered_confirmed_by": request.user.pk,
                             "not_delivered_confirmed_at": timezone.now().isoformat()}
            outbound.save()
        return Response(draft_payload(draft))
