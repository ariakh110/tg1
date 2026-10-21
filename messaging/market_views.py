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
