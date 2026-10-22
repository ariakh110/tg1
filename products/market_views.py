from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .market import build_market_rows, build_market_summary, history_start_date
from .models import Product, ProductPriceSnapshot
from .market_hierarchy import filter_market_scope


def serialize_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def serialize_row(row):
    return {key: serialize_value(value) for key, value in row.items()}


class MarketSummaryAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        summary = build_market_summary()
        summary["latest_observed_at"] = serialize_value(summary["latest_observed_at"])
        summary["groups"] = [serialize_row(item) for item in summary["groups"]]
        summary["top_gainers"] = [serialize_row(item) for item in summary["top_gainers"]]
        summary["top_losers"] = [serialize_row(item) for item in summary["top_losers"]]
        summary["tiles"] = [serialize_row(item) for item in summary["tiles"]]
        return Response(summary)


class MarketProductListAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        search = request.query_params.get("search", "")
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(100, max(1, int(request.query_params.get("page_size", 30))))
        except (TypeError, ValueError):
            return Response({"detail": "page و page_size باید عدد صحیح باشند."}, status=status.HTTP_400_BAD_REQUEST)
        rows = filter_market_scope(build_market_rows(search=search), request.query_params)
        start = (page - 1) * page_size
        return Response(
            {
                "count": len(rows),
                "page": page,
                "page_size": page_size,
                "results": [serialize_row(row) for row in rows[start : start + page_size]],
            }
        )


class MarketProductHistoryAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        product = get_object_or_404(Product.objects.filter(is_active=True), pk=product_id)
        range_name = request.query_params.get("range", "30d")
        if range_name not in {"7d", "30d", "90d"}:
            return Response({"detail": "range باید یکی از 7d، 30d یا 90d باشد."}, status=status.HTTP_400_BAD_REQUEST)
        start_date, days = history_start_date(range_name)
        basis = (request.query_params.get("basis") or "").strip()
        queryset = ProductPriceSnapshot.objects.filter(product=product, observed_on__gte=start_date)
        if basis:
            queryset = queryset.filter(pricing_basis=basis)
        else:
            latest = queryset.order_by("-observed_on", "-observed_at").first()
            if latest:
                basis = latest.pricing_basis
                queryset = queryset.filter(pricing_basis=basis)
        points = [
            {
                "date": item.observed_on.isoformat(),
                "price": str(item.price),
                "normalized_price_kg": (
                    str(item.normalized_price_kg) if item.normalized_price_kg is not None else None
                ),
                "observed_at": item.observed_at.isoformat(),
            }
            for item in queryset.order_by("observed_on", "observed_at")[:days]
        ]
        return Response(
            {
                "product": {"id": product.id, "name": product.name, "slug": product.slug},
                "range": range_name,
                "pricing_basis": basis or None,
                "points": points,
            }
        )
