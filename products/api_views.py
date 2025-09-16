from django.db.models import Min
from rest_framework import viewsets
from rest_framework.response import Response

from .models import Product, Offer, PricingTier
from .serializers import ProductSummarySerializer  # فقط برای الهام، اینجا خلاصه می‌سازیم

class ProductSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all().prefetch_related("offers", "images")
    serializer_class = ProductSummarySerializer  # ✅ این مهمه

    # اجازه بده کاربر بتونه مرتب‌سازی کنه
    ordering_fields = ["id", "name", "min_price"]  
    ordering = ["id"]

    
    def get_queryset(self):
        return Product.objects.annotate(
            min_price=Min("offers__pricing_tiers__unit_price")
        ).prefetch_related("offers", "images")

