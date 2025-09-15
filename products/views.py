# products/views.py
from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action

from django.db.models import Min

from .models import (
    Product, ProductCategory, ProductImage, ProductSpecification,
    ProductStandard, SpecificationAttribute, SpecificationValue,
    Offer, PricingTier, DeliveryLocation, ProductDocument, Seller
)
from .serializers import (
    ProductListSerializer, ProductDetailSerializer, ProductWriteSerializer,
    ProductCategorySerializer, ProductImageSerializer, ProductSpecificationSerializer,
    ProductStandardSerializer, SpecificationAttributeSerializer, SpecificationValueSerializer,
    OfferReadSerializer, OfferWriteSerializer, PricingTierSerializer, DeliveryLocationSerializer,
    ProductDocumentSerializer, SellerSerializer
)

from .filters import ProductFilter, OfferFilter  

# Pagination
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 100


# ---------- ProductCategory ----------
class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["parent", "hscode"]
    search_fields = ["name", "hscode"]
    ordering_fields = ["name"]


# ---------- Product ----------
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").prefetch_related("images", "documents", "offers", "dynamic_specs") \
        .annotate(min_price=Min('offers__pricing_tiers__unit_price'))
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter    
    search_fields = ["name", "short_description", "description", "slug"]
    ordering_fields = ["created_at", "updated_at", "name"]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductWriteSerializer

    # convenience endpoint: /api/products/{pk}/offers/
    # returns offers for this product
    @action(detail=True, methods=["get"], url_path="offers")
    def product_offers(self, request, pk=None):
        product = self.get_object()
        offers = product.offers.select_related("seller").prefetch_related("pricing_tiers", "delivery_options").all()
        serializer = OfferReadSerializer(offers, many=True, context={"request": request})
        return Response(serializer.data)


# ---------- ProductSpecification ----------
class ProductSpecificationViewSet(viewsets.ModelViewSet):
    queryset = ProductSpecification.objects.select_related("product", "standard")
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = ProductSpecificationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["product", "steel_grade", "material_type"]
    search_fields = ["steel_grade", "material_type"]


# ---------- SpecificationAttribute & Value ----------
class SpecificationAttributeViewSet(viewsets.ModelViewSet):
    queryset = SpecificationAttribute.objects.all()
    serializer_class = SpecificationAttributeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    search_fields = ["name"]


class SpecificationValueViewSet(viewsets.ModelViewSet):
    queryset = SpecificationValue.objects.select_related("product", "attribute")
    serializer_class = SpecificationValueSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["product", "attribute"]
    search_fields = ["value"]


# ---------- ProductImage ----------
class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.select_related("product")
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product", "is_featured"]

    # override create to accept product id in request data
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


# ---------- ProductDocument ----------
class ProductDocumentViewSet(viewsets.ModelViewSet):
    queryset = ProductDocument.objects.select_related("product")
    serializer_class = ProductDocumentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product"]


# ---------- Offer ----------
class OfferViewSet(viewsets.ModelViewSet):
    queryset = Offer.objects.select_related("product", "seller").prefetch_related("pricing_tiers", "delivery_options")
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OfferFilter
    search_fields = ["product__name", "seller__company_name"]
    ordering_fields = ["created_at"]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return OfferReadSerializer
        return OfferWriteSerializer

    # when creating/updating, OfferWriteSerializer expects product and seller as PKs
    # no additional override needed here


# ---------- PricingTier ----------
class PricingTierViewSet(viewsets.ModelViewSet):
    queryset = PricingTier.objects.select_related("offer", "offer__product")
    serializer_class = PricingTierSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["offer", "offer__product"]

    def create(self, request, *args, **kwargs):
        """
        PricingTier serializer marks 'offer' as read-only in the shared serializer.
        To create, client may supply 'offer' in payload (offer id) or we can accept it via URL/query.
        We'll support payload['offer'] or payload['offer_id'].
        """
        offer_id = request.data.get("offer") or request.data.get("offer_id")
        if not offer_id:
            return Response({"detail": "offer (id) is required."}, status=status.HTTP_400_BAD_REQUEST)
        offer = get_object_or_404(Offer, pk=offer_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # pass offer explicitly to save (even if field set read_only)
        instance = serializer.save(offer=offer)
        headers = self.get_success_headers(serializer.data)
        read_serializer = PricingTierSerializer(instance, context={"request": request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


# ---------- DeliveryLocation ----------
class DeliveryLocationViewSet(viewsets.ModelViewSet):
    queryset = DeliveryLocation.objects.select_related("offer")
    serializer_class = DeliveryLocationSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["offer", "incoterm", "country"]
    search_fields = ["country", "city", "port"]

    def create(self, request, *args, **kwargs):
        offer_id = request.data.get("offer") or request.data.get("offer_id")
        if not offer_id:
            return Response({"detail": "offer (id) is required."}, status=status.HTTP_400_BAD_REQUEST)
        offer = get_object_or_404(Offer, pk=offer_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(offer=offer)
        read_serializer = DeliveryLocationSerializer(instance, context={"request": request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


# ---------- ProductStandard ----------
class ProductStandardViewSet(viewsets.ModelViewSet):
    queryset = ProductStandard.objects.all()
    serializer_class = ProductStandardSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
# # ---------- SellerViewSet ---------- 
class SellerViewSet(viewsets.ModelViewSet):
    queryset = Seller.objects.all()
    serializer_class = SellerSerializer
    filterset_fields = ['is_verified', 'business_type']
    search_fields = ['company_name', 'location']
    ordering_fields = ['created_at']