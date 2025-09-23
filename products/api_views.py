from django.db.models import Min
from rest_framework import viewsets, filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product
from .serializers import ProductSummarySerializer  # فقط برای الهام، اینجا خلاصه می‌سازیم
from .filters import ProductFilter

class ProductSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all().prefetch_related("offers", "images")
    serializer_class = ProductSummarySerializer  # ✅ این مهمه

    # enable filtering via django-filter and DRF SearchFilter
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_class = ProductFilter
    # fields to be searched by ?search=...
    search_fields = ["name", "short_description", "description", "slug", "category__name"]

    # allow ordering by these fields
    ordering_fields = ["id", "name", "min_price"]
    ordering = ["id"]

    def get_queryset(self):
        return Product.objects.annotate(
            min_price=Min("offers__pricing_tiers__unit_price")
        ).prefetch_related("offers", "images")

