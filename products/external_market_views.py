from datetime import timedelta
from decimal import Decimal

from django.db.models import Max, Sum, Q, F, Count
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrActiveAdminRole

from .external_markets import (
    MarketSyncError,
    global_metals_config,
    import_global_metals_csv,
    sync_global_metals,
    trade_display_name,
    trade_specifications,
    visible_global_metals,
)
from .models import (
    CommodityExchangeTrade,
    GlobalMetalInstrument,
    GlobalMetalObservation,
    MarketDataSyncState,
)


def _value(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _sync_payload(key):
    state = MarketDataSyncState.objects.filter(key=key).first()
    if not state:
        return {"status": "never", "finished_at": None, "record_count": 0, "error": ""}
    return {
        "status": state.status,
        "finished_at": _value(state.finished_at),
        "record_count": state.record_count,
        "error": state.error_message if state.status == MarketDataSyncState.Status.ERROR else "",
    }


def _pagination(request, default=30):
    try:
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", default))))
    except (TypeError, ValueError) as exc:
        raise ValueError("page و page_size باید عدد صحیح باشند.") from exc
    return page, page_size


def _trade_payload(item):
    return {
        "id": item.id,
        "source_report_id": item.source_report_id,
        "symbol": item.symbol,
        "goods_name": item.goods_name,
        "display_name": trade_display_name(item),
        "specifications": trade_specifications(item.raw),
        "product_group": item.product_group,
        "producer_name": item.producer_name,
        "hall": item.hall,
        "contract_type": item.contract_type,
        "base_price": _value(item.base_price),
        "min_price": _value(item.min_price),
        "weighted_price": _value(item.weighted_price),
        "max_price": _value(item.max_price),
        "offered_volume": _value(item.offered_volume),
        "demand_volume": _value(item.demand_volume),
        "traded_volume": _value(item.traded_volume),
        "transaction_value_thousand_rial": _value(item.transaction_value_thousand_rial),
        "currency": item.currency,
        "unit": item.unit,
        "trade_date": item.trade_date.isoformat(),
        "trade_date_jalali": item.trade_date_jalali,
        "delivery_date_jalali": item.delivery_date_jalali,
        "source_url": item.source_url,
    }


class CommodityExchangeSummaryAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        latest_date = CommodityExchangeTrade.objects.aggregate(value=Max("trade_date"))["value"]
        latest = CommodityExchangeTrade.objects.none()
        if latest_date:
            latest = CommodityExchangeTrade.objects.filter(trade_date=latest_date)
        totals = latest.aggregate(
            offered_volume=Sum("offered_volume"),
            demand_volume=Sum("demand_volume"),
            traded_volume=Sum("traded_volume"),
            transaction_value_thousand_rial=Sum("transaction_value_thousand_rial"),
        )
        groups = list(
            latest.values("product_group")
            .annotate(
                trade_count=Sum("traded_volume"),
                offered_volume=Sum("offered_volume"),
                demand_volume=Sum("demand_volume"),
                value=Sum("transaction_value_thousand_rial"),
            )
            .order_by("-value")
        )
        for group in groups:
            for key, value in list(group.items()):
                group[key] = _value(value)
        hierarchy = {}
        for item in latest.values("product_group", "producer_name", "symbol", "goods_name").annotate(records=Count("id")):
            producers = hierarchy.setdefault(item["product_group"], {})
            producer = item["producer_name"] or "تولیدکننده نامشخص"
            producers.setdefault(producer, []).append({
                "name": item["goods_name"], "symbol": item["symbol"], "producer_name": item["producer_name"],
                "group": item["product_group"], "value": item["records"],
            })
        is_stale = bool(latest_date and latest_date < timezone.localdate() - timedelta(days=5))
        return Response(
            {
                "latest_trade_date": _value(latest_date),
                "latest_trade_date_jalali": latest.values_list("trade_date_jalali", flat=True).first(),
                "records": latest.count(),
                "symbols": latest.values("symbol").distinct().count(),
                "totals": {key: _value(value) for key, value in totals.items()},
                "groups": groups,
                "hierarchy": [{"name": name, "group": name, "children": [
                    {"name": producer, "group": name, "children": children}
                    for producer, children in producers.items()
                ]} for name, producers in hierarchy.items()],
                "is_stale": is_stale,
                "source": {"name": "بورس کالای ایران", "url": "https://www.ime.co.ir/deals_statistics.html"},
                "sync": _sync_payload("ime"),
            }
        )


class CommodityExchangeTradeListAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            page, page_size = _pagination(request)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        queryset = CommodityExchangeTrade.objects.all()
        search = (request.query_params.get("search") or "").strip()
        for term in search.split():
            queryset = queryset.filter(
                Q(goods_name__icontains=term)
                | Q(symbol__icontains=term)
                | Q(producer_name__icontains=term)
                | Q(raw__icontains=term)
            )
        for field in ("product_group", "producer_name", "symbol"):
            value = (request.query_params.get(field) or "").strip()
            if value:
                queryset = queryset.filter(**{field: value})
        if request.query_params.get("date_from"):
            queryset = queryset.filter(trade_date__gte=request.query_params["date_from"])
        if request.query_params.get("date_to"):
            queryset = queryset.filter(trade_date__lte=request.query_params["date_to"])
        ordering = request.query_params.get("ordering", "-trade_date")
        sort_fields = {"goods_name", "symbol", "producer_name", "base_price", "weighted_price",
                       "offered_volume", "demand_volume", "traded_volume", "trade_date"}
        field = ordering.lstrip("-")
        if field not in sort_fields:
            return Response({"detail": "ستون مرتب‌سازی نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
        expression = F(field).desc(nulls_last=True) if ordering.startswith("-") else F(field).asc(nulls_last=True)
        queryset = queryset.order_by(expression, "-source_report_id")
        count = queryset.count()
        start = (page - 1) * page_size
        return Response(
            {
                "count": count,
                "page": page,
                "page_size": page_size,
                "results": [_trade_payload(item) for item in queryset[start : start + page_size]],
            }
        )


class CommodityExchangeHistoryAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, symbol):
        range_name = request.query_params.get("range", "30d")
        ranges = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}
        if range_name not in ranges:
            return Response({"detail": "range نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
        start = timezone.localdate() - timedelta(days=ranges[range_name] - 1)
        rows = CommodityExchangeTrade.objects.filter(symbol=symbol, trade_date__gte=start).order_by("trade_date", "source_report_id")
        producer = request.query_params.get("producer_name")
        if producer:
            rows = rows.filter(producer_name=producer)
        # Aggregate executions within a day; never mix units or substitute a base quote for a trade price.
        buckets = {}
        for row in rows:
            key = (row.trade_date, row.currency, row.unit)
            bucket = buckets.setdefault(key, {"date": row.trade_date.isoformat(), "date_jalali": row.trade_date_jalali,
                "currency": row.currency, "unit": row.unit, "offered_volume": Decimal(0),
                "demand_volume": Decimal(0), "traded_volume": Decimal(0), "weighted_sum": Decimal(0),
                "weight": Decimal(0), "base_sum": Decimal(0), "base_count": 0})
            for field in ("offered_volume", "demand_volume", "traded_volume"):
                bucket[field] += getattr(row, field) or Decimal(0)
            if row.weighted_price is not None and row.traded_volume and row.traded_volume > 0:
                bucket["weighted_sum"] += row.weighted_price * row.traded_volume
                bucket["weight"] += row.traded_volume
            if row.base_price is not None:
                bucket["base_sum"] += row.base_price
                bucket["base_count"] += 1
        points = []
        for bucket in buckets.values():
            weighted = bucket["weighted_sum"] / bucket["weight"] if bucket["weight"] else None
            base = bucket["base_sum"] / bucket["base_count"] if bucket["base_count"] else None
            points.append({**{k: _value(bucket[k]) for k in ("date", "date_jalali", "currency", "unit", "offered_volume", "demand_volume", "traded_volume")},
                           "price": _value(weighted), "base_price": _value(base), "price_kind": "weighted"})
        return Response({"symbol": symbol, "range": range_name, "points": points})


def _observation_payload(instrument, latest, previous):
    change = None
    percent_change = None
    if previous and previous.price:
        change = latest.price - previous.price
        percent_change = change * Decimal("100") / previous.price
    return {
        "code": instrument.code,
        "name_fa": instrument.name_fa,
        "name_en": instrument.name_en,
        "exchange": instrument.exchange,
        "currency": instrument.currency,
        "unit": instrument.unit,
        "price": _value(latest.price),
        "change": _value(change),
        "percent_change": str(percent_change.quantize(Decimal("0.01"))) if percent_change is not None else None,
        "observed_at": latest.observed_at.isoformat(),
        "provider": latest.provider,
        "source_url": latest.source_url,
        "is_stale": latest.observed_at < timezone.now() - timedelta(hours=48),
    }


class GlobalMetalSummaryAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        provider_config = global_metals_config()
        rows = []
        exchange = (request.query_params.get("exchange") or "").strip()
        instruments = visible_global_metals()
        if exchange:
            instruments = instruments.filter(exchange=exchange)
        for instrument in instruments:
            latest = instrument.observations.order_by("-observed_on", "-observed_at").first()
            observations = []
            if latest:
                previous = instrument.observations.filter(provider=latest.provider, observed_on__lt=latest.observed_on).order_by("-observed_on", "-observed_at").first()
                observations = [latest, previous]
            if observations:
                rows.append(_observation_payload(instrument, observations[0], observations[1] if len(observations) > 1 else None))
        return Response(
            {
                "provider_enabled": provider_config["enabled"],
                "provider_configured": provider_config["enabled"] and bool(provider_config["api_key"]),
                "instruments": rows,
                "exchanges": list(
                    visible_global_metals()
                    .values_list("exchange", flat=True)
                    .distinct()
                ),
                "sync": _sync_payload("metals_dev"),
            }
        )


class GlobalMetalHistoryAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, code):
        range_name = request.query_params.get("range", "30d")
        ranges = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}
        if range_name not in ranges:
            return Response({"detail": "range نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            instrument = visible_global_metals().get(code=code)
        except GlobalMetalInstrument.DoesNotExist:
            return Response({"detail": "فلز موردنظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        start = timezone.localdate() - timedelta(days=ranges[range_name] - 1)
        latest = instrument.observations.order_by("-observed_on", "-observed_at").first()
        points = instrument.observations.filter(observed_on__gte=start)
        points = points.filter(provider=latest.provider) if latest else points.none()
        points = points.order_by("observed_on", "observed_at")[:500]
        return Response(
            {
                "instrument": {
                    "code": instrument.code,
                    "name_fa": instrument.name_fa,
                    "name_en": instrument.name_en,
                    "exchange": instrument.exchange,
                    "currency": instrument.currency,
                    "unit": instrument.unit,
                },
                "range": range_name,
                "points": [
                    {
                        "date": item.observed_on.isoformat(),
                        "price": _value(item.price),
                        "provider": item.provider,
                        "source_url": item.source_url,
                    }
                    for item in points
                ],
            }
        )


class GlobalMetalCSVImportAPIView(APIView):
    permission_classes = [IsAdminOrActiveAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"file": "فایل CSV الزامی است."}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > 2 * 1024 * 1024:
            return Response({"file": "حداکثر حجم فایل ۲ مگابایت است."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            count = import_global_metals_csv(upload.read())
        except (MarketSyncError, UnicodeDecodeError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"imported": count}, status=status.HTTP_201_CREATED)


class GlobalMetalSyncAPIView(APIView):
    permission_classes = [IsAdminOrActiveAdminRole]

    def post(self, request):
        try:
            count = sync_global_metals(force=True)
        except MarketSyncError as exc:
            return Response(
                {"detail": str(exc), "sync": _sync_payload("metals_dev")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sync = _sync_payload("metals_dev")
        if sync["status"] == MarketDataSyncState.Status.ERROR:
            return Response({"detail": sync["error"], "sync": sync}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"synchronized": count, "sync": sync})
