# products/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    ProductViewSet, ProductCategoryViewSet, ProductImageViewSet,
    ProductSpecificationViewSet, ProductStandardViewSet,
    SpecificationAttributeViewSet, SpecificationValueViewSet,
    OfferViewSet, PricingTierViewSet, DeliveryLocationViewSet,
    ProductDocumentViewSet, SellerViewSet
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', ProductCategoryViewSet, basename='category')
router.register(r'product-images', ProductImageViewSet, basename='productimage')
router.register(r'product-documents', ProductDocumentViewSet, basename='productdocument')
router.register(r'specifications', ProductSpecificationViewSet, basename='specification')
router.register(r'standards', ProductStandardViewSet, basename='standard')
router.register(r'spec-attributes', SpecificationAttributeViewSet, basename='specattribute')
router.register(r'spec-values', SpecificationValueViewSet, basename='specvalue')
router.register(r'offers', OfferViewSet, basename='offer')
router.register(r'pricing-tiers', PricingTierViewSet, basename='pricingtier')
router.register(r'delivery-locations', DeliveryLocationViewSet, basename='deliverylocation')
router.register(r'sellers', SellerViewSet, basename='seller')

urlpatterns = [
    path('', include(router.urls)),
]
