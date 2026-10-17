# products/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    ProductViewSet, ProductCategoryViewSet, ProductImageViewSet,
    ProductSpecificationViewSet, ProductStandardViewSet,
    SpecificationAttributeViewSet, ProductAttributeOptionViewSet, SpecificationValueViewSet,
    OfferViewSet, PricingTierViewSet, DeliveryLocationViewSet,
    ProductDocumentViewSet, SellerViewSet
)
from .api_views import ProductSummaryViewSet
from .market_views import MarketProductHistoryAPIView, MarketProductListAPIView, MarketSummaryAPIView
from .external_market_views import (
    CommodityExchangeHistoryAPIView,
    CommodityExchangeSummaryAPIView,
    CommodityExchangeTradeListAPIView,
    GlobalMetalCSVImportAPIView,
    GlobalMetalHistoryAPIView,
    GlobalMetalSummaryAPIView,
)


router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', ProductCategoryViewSet, basename='category')
router.register(r'product-images', ProductImageViewSet, basename='productimage')
router.register(r'product-documents', ProductDocumentViewSet, basename='productdocument')
router.register(r'specifications', ProductSpecificationViewSet, basename='specification')
router.register(r'standards', ProductStandardViewSet, basename='standard')
router.register(r'spec-attributes', SpecificationAttributeViewSet, basename='specattribute')
router.register(r'attribute-options', ProductAttributeOptionViewSet, basename='attributeoption')
router.register(r'spec-values', SpecificationValueViewSet, basename='specvalue')
router.register(r'offers', OfferViewSet, basename='offer')
router.register(r'pricing-tiers', PricingTierViewSet, basename='pricingtier')
router.register(r'delivery-locations', DeliveryLocationViewSet, basename='deliverylocation')
router.register(r'sellers', SellerViewSet, basename='seller')
router.register(r'products-summary', ProductSummaryViewSet, basename='product-summary')
urlpatterns = [
    path('market/summary/', MarketSummaryAPIView.as_view(), name='market-summary'),
    path('market/products/', MarketProductListAPIView.as_view(), name='market-products'),
    path('market/products/<int:product_id>/history/', MarketProductHistoryAPIView.as_view(), name='market-product-history'),
    path('commodity-exchange/summary/', CommodityExchangeSummaryAPIView.as_view(), name='commodity-exchange-summary'),
    path('commodity-exchange/trades/', CommodityExchangeTradeListAPIView.as_view(), name='commodity-exchange-trades'),
    path('commodity-exchange/symbols/<path:symbol>/history/', CommodityExchangeHistoryAPIView.as_view(), name='commodity-exchange-history'),
    path('global-metals/summary/', GlobalMetalSummaryAPIView.as_view(), name='global-metals-summary'),
    path('global-metals/instruments/<slug:code>/history/', GlobalMetalHistoryAPIView.as_view(), name='global-metals-history'),
    path('admin/global-metals/import/', GlobalMetalCSVImportAPIView.as_view(), name='global-metals-import'),
    path('', include(router.urls)),
]
