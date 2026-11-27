from django.db.models import Min, Q
from rest_framework import viewsets, filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from .market_hierarchy import MarketTaxonomy
from .models import Product, ProductSpecification
from .serializers import ProductSummarySerializer  # فقط برای الهام، اینجا خلاصه می‌سازیم
from .filters import ProductFilter
from accounts.permissions import IsAdminOrActiveAdminRole


class SummaryPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 1000


class ProductSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all().prefetch_related("offers", "images")
    serializer_class = ProductSummarySerializer  # ✅ این مهمه
    pagination_class = SummaryPagination

    # enable filtering via django-filter and DRF SearchFilter
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = ProductFilter
    # fields to be searched by ?search=...
    search_fields = ["name", "short_description", "description", "slug", "category__name"]

    # allow ordering by these fields
    ordering_fields = ["id", "name", "min_price"]
    ordering = ["id"]

    def get_queryset(self):
        queryset = (
            Product.objects.annotate(
                min_price=Min("offers__pricing_tiers__unit_price")
            )
            .select_related("category", "specifications")
            .prefetch_related("offers", "images", "offers__delivery_options")
        )
        if not IsAdminOrActiveAdminRole().has_permission(self.request, self):
            queryset = queryset.filter(is_active=True)
        return queryset



    @action(detail=False, methods=["get"])
    def ticker(self, request):
        products = list(
            Product.objects.filter(is_active=True)
            .annotate(
                min_price=Min(
                    "offers__pricing_tiers__unit_price",
                    filter=Q(offers__is_active=True, offers__pricing_tiers__unit_price__gt=0),
                )
            )
            .filter(min_price__gt=0)
            .select_related("specifications")
            .order_by("-updated_at", "-pk")[:16]
        )
        if not products:
            return Response([])
        taxonomy = MarketTaxonomy()
        rows = []
        for product in products:
            try:
                spec = product.specifications
            except ProductSpecification.DoesNotExist:
                spec = None
            groups = taxonomy.describe(product, spec)
            size = next(
                (value for value in (
                    getattr(spec, "thickness_mm", None),
                    getattr(spec, "diameter_mm", None),
                    getattr(spec, "height_mm", None),
                    getattr(spec, "width_mm", None),
                ) if value is not None and value > 0),
                None,
            )
            rows.append({
                "id": product.pk,
                "name": product.name,
                "min_price": product.min_price,
                "factory": groups["factory"],
                "factory_label": groups["factory_label"],
                "product_kind": groups["product_kind_label"],
                "subtype": groups["subtype_label"],
                "size_mm": size,
            })
        return Response(rows)
