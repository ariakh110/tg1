# products/views.py
from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action

from django.db.models import Min

# مدل‌ها
from .models import (
    Product, ProductCategory, ProductImage, ProductSpecification,
    ProductStandard, SpecificationAttribute, SpecificationValue,
    Offer, PricingTier, DeliveryLocation, ProductDocument, Seller
)

# سریالایزرها (باید فایل serializers.py را مطابق نیازت داشته باشی)
from .serializers import (
    ProductListSerializer, ProductDetailSerializer, ProductWriteSerializer,
    ProductCategorySerializer, ProductImageSerializer, ProductSpecificationSerializer,
    ProductStandardSerializer, SpecificationAttributeSerializer, SpecificationValueSerializer,
    OfferReadSerializer, OfferWriteSerializer, PricingTierSerializer, DeliveryLocationSerializer,
    ProductDocumentSerializer, SellerSerializer
)

# فیلترها و مجوزها (permissions)
from .filters import ProductFilter, OfferFilter  
from .permissions import IsAdminOrReadOnly, HasSellerProfile, IsOfferOwner, IsSellerOwnerOrAdmin

# ---------------- Pagination استاندارد برای viewset ها ----------------
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 12                 # تعداد پیش‌فرض در هر صفحه
    page_size_query_param = "page_size"
    max_page_size = 100


# ---------------- ProductCategoryViewSet ----------------
class ProductCategoryViewSet(viewsets.ModelViewSet):
    """
    مدیریت دسته‌بندی‌ها (درختی با mptt).
    - فقط admin می‌تواند دسته جدید بسازد/ویرایش کند (IsAdminOrReadOnly).
    - همه می‌توانند لیست/مشاهده کنند.
    """
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["parent", "hscode"]
    search_fields = ["name", "hscode"]
    ordering_fields = ["name"]


# ---------------- ProductViewSet ----------------
class ProductViewSet(viewsets.ModelViewSet):
    """
    عملیات CRUD روی محصولات:
    - queryset با select_related/prefetch_related برای کارایی بهتر
    - همچنین annotate برای min_price تا فرانت سریع‌تر کمترین قیمت محصول را دریافت کند
    - برای خواندن عمومی است؛ نوشتن فقط برای admin (IsAdminOrReadOnly)
    """
    queryset = Product.objects.select_related("category").prefetch_related(
        "images", "documents", "offers", "dynamic_specs"
    ).annotate(min_price=Min('offers__pricing_tiers__unit_price'))  # حداقل قیمت از بین offers -> pricing_tiers
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter    
    search_fields = ["name", "short_description", "description", "slug"]
    ordering_fields = ["created_at", "updated_at", "name", "min_price"]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """
        از serializerهای مجزا برای list / retrieve / write استفاده می‌کنیم
        - list: کم‌حجم (ProductListSerializer) شامل min_price ، thumbnail
        - retrieve: جزئیات کامل (ProductDetailSerializer)
        - create/update: ProductWriteSerializer
        """
        if self.action == "list":
            return ProductListSerializer
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductWriteSerializer

    @action(detail=True, methods=["get"], url_path="offers")
    def product_offers(self, request, pk=None):
        """
        endpoint مبتی بر محصول:
        GET /api/products/{pk}/offers/
        برگشت لیست offers که برای این محصول ثبت شده‌اند.
        """
        product = self.get_object()
        offers = product.offers.select_related("seller").prefetch_related("pricing_tiers", "delivery_options").all()
        serializer = OfferReadSerializer(offers, many=True, context={"request": request})
        return Response(serializer.data)


# ---------------- ProductSpecificationViewSet ----------------
class ProductSpecificationViewSet(viewsets.ModelViewSet):
    """
    مشخصات فنی محصول (OneToOne یا رکوردهای مربوطه).
    نوشتن فقط برای Admin در اینجا (قابل تغییر بر اساس نیاز).
    """
    queryset = ProductSpecification.objects.select_related("product", "standard")
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = ProductSpecificationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["product", "steel_grade", "material_type"]
    search_fields = ["steel_grade", "material_type"]


# ---------------- SpecificationAttribute & SpecificationValue ----------------
class SpecificationAttributeViewSet(viewsets.ModelViewSet):
    """
    تعریف ویژگی‌های قابل افزودن برای محصولات (مثلاً 'ضخامت', 'نوع سطح' و ...).
    """
    queryset = SpecificationAttribute.objects.all()
    serializer_class = SpecificationAttributeSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["name"]


class SpecificationValueViewSet(viewsets.ModelViewSet):
    """
    مقادیر داینامیک هر محصول برای attributeها.
    """
    queryset = SpecificationValue.objects.select_related("product", "attribute")
    serializer_class = SpecificationValueSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["product", "attribute"]
    search_fields = ["value"]


# ---------------- ProductImageViewSet ----------------
class ProductImageViewSet(viewsets.ModelViewSet):
    """
    مدیریت تصاویر محصولات.
    تغییرات کلیدی:
    - لیست/مشاهده: همه
    - ایجاد: نیاز به seller (یا admin)
    - ویرایش/حذف: فقط مالک محصول یا admin
    """
    queryset = ProductImage.objects.select_related("product")
    serializer_class = ProductImageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product", "is_featured"]

    def get_permissions(self):
        # کنترل مجوزها بر اساس action فعلی
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        if self.action == "create":
            # upload image: seller باید باشد یا admin
            return [permissions.IsAuthenticated(), HasSellerProfile()]
        # update/delete: تنها مالک (یا admin) بتواند
        return [permissions.IsAuthenticated(), IsOfferOwner()]

    def perform_create(self, serializer):
        """
        هنگام ایجاد تصویر، مطمئن می‌شویم کاربر صاحب محصول است.
        (در مدل ما Product ممکن است seller داشته باشد؛ اگر ندارد این چک نادیده گرفته می‌شود)
        """
        product = serializer.validated_data.get("product")
        user = self.request.user
        if product and hasattr(product, "seller"):
            if not (user.is_staff or user.is_superuser or (hasattr(user, "seller_profile") and user.seller_profile == product.seller)):
                raise PermissionError("You are not the owner of the product.")
        serializer.save()


# ---------------- ProductDocumentViewSet ----------------
class ProductDocumentViewSet(viewsets.ModelViewSet):
    """
    مدیریت اسناد فنی (PDF, CAD, ...).
    قواعد مشابه تصاویر اعمال شده است.
    """
    queryset = ProductDocument.objects.select_related("product")
    serializer_class = ProductDocumentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        if self.action == "create":
            return [permissions.IsAuthenticated(), HasSellerProfile()]
        return [permissions.IsAuthenticated(), IsOfferOwner()]


# ---------------- OfferViewSet ----------------
class OfferViewSet(viewsets.ModelViewSet):
    """
    مدیریت پیشنهاد فروش (Offer) که یک فروشنده برای یک محصول ثبت می‌کند.
    - list/retrieve: عمومی (AllowAny)
    - create: کاربر لاگین‌شده با seller_profile
    - update/destroy: فقط مالک (IsOfferOwner) یا admin
    همچنین perform_create خودکار seller را از request.user می‌گیرد تا کسی نتواند seller را جعل کند.
    """
    queryset = Offer.objects.select_related("product", "seller").prefetch_related("pricing_tiers", "delivery_options")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OfferFilter
    search_fields = ["product__name", "seller__company_name"]
    ordering_fields = ["created_at"]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        # برای نمایش از OfferReadSerializer (شامل pricing tiers و delivery options)
        if self.action in ["list", "retrieve"]:
            return OfferReadSerializer
        # برای نوشتن (create/update) از OfferWriteSerializer استفاده شود
        return OfferWriteSerializer

    def get_permissions(self):
        """
        منطق مجوز برای Offer:
        - list/retrieve: AllowAny
        - create: IsAuthenticated + HasSellerProfile
        - update/destroy: IsAuthenticated + IsOfferOwner
        """
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        if self.action == "create":
            return [permissions.IsAuthenticated(), HasSellerProfile()]
        return [permissions.IsAuthenticated(), IsOfferOwner()]

    def perform_create(self, serializer):
        """
        هنگام ایجاد، seller از profile کاربر گرفته می‌شود (و ذخیره می‌شود).
        اگر کاربر seller profile نداشته باشد، HasSellerProfile معمولاً جلوی این مسیر را گرفته،
        اما اینجا هم چک ایمنی انجام می‌دهیم.
        """
        user = self.request.user
        if not hasattr(user, "seller_profile"):
            # اگر دوست داری پیام و نوع خطا را تغییر دهی، اینجا تنظیم کن
            raise PermissionError("User does not have a seller profile.")
        seller = user.seller_profile
        serializer.save(seller=seller)


# ---------------- PricingTierViewSet ----------------
class PricingTierViewSet(viewsets.ModelViewSet):
    """
    رده‌های قیمت‌گذاری برای یک Offer (قیمت حجمی).
    - list/retrieve: عمومی
    - create: فقط ownerِ Offer یا admin
    - در create: می‌توان offer id را در payload یا offer_id فرستاد
    """
    queryset = PricingTier.objects.select_related("offer", "offer__product")
    serializer_class = PricingTierSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["offer", "offer__product"]
    
    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsOfferOwner()]

    def create(self, request, *args, **kwargs):
        """
        create را override کردیم تا:
        - از payload مقدار offer_id گرفته شود
        - مالکیت offer را چک کنیم (کاربر نباید برای offer دیگران tier بسازد)
        """
        offer_id = request.data.get("offer") or request.data.get("offer_id")
        if not offer_id:
            return Response({"detail": "offer (id) is required."}, status=status.HTTP_400_BAD_REQUEST)
        offer = get_object_or_404(Offer, pk=offer_id)
        
        # مالکیت را بررسی می‌کنیم
        user = request.user
        if not (user.is_staff or user.is_superuser or (hasattr(user, "seller_profile") and offer.seller == user.seller_profile)):
            return Response({"detail": "You are not the owner of this offer."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(offer=offer)  # offer را صریحاً پاس می‌دهیم
        headers = self.get_success_headers(serializer.data)
        read_serializer = PricingTierSerializer(instance, context={"request": request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


# ---------------- DeliveryLocationViewSet ----------------
class DeliveryLocationViewSet(viewsets.ModelViewSet):
    """
    گزینه‌های تحویل (incoterms, country, port) وابسته به Offer.
    منطق مجوز و create شبیه PricingTier است.
    """
    queryset = DeliveryLocation.objects.select_related("offer")
    serializer_class = DeliveryLocationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["offer", "incoterm", "country"]
    search_fields = ["country", "city", "port"]
    
    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsOfferOwner()]

    def create(self, request, *args, **kwargs):
        offer_id = request.data.get("offer") or request.data.get("offer_id")
        if not offer_id:
            return Response({"detail": "offer (id) is required."}, status=status.HTTP_400_BAD_REQUEST)
        offer = get_object_or_404(Offer, pk=offer_id)
        user = request.user
        if not (user.is_staff or user.is_superuser or (hasattr(user, "seller_profile") and offer.seller == user.seller_profile)):
            return Response({"detail": "You are not the owner of this offer."}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(offer=offer)
        read_serializer = DeliveryLocationSerializer(instance, context={"request": request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


# ---------------- ProductStandardViewSet ----------------
class ProductStandardViewSet(viewsets.ModelViewSet):
    """
    استانداردهای بین‌المللی (DIN, ASTM, EN ...).
    تغییرات این مدل معمولاً توسط admin انجام می‌شود.
    """
    queryset = ProductStandard.objects.all()
    serializer_class = ProductStandardSerializer
    permission_classes = [IsAdminOrReadOnly]
    

# ---------------- SellerViewSet ----------------
class SellerViewSet(viewsets.ModelViewSet):
    """
    مدیریت پروفایل فروشندگان (Seller model).
    رفتار مجوزی:
    - list/retrieve: عمومی (AllowAny) — همه می‌توانند صفحهٔ شرکت‌ها را ببینند
    - create: نیاز به کاربر لاگین‌شده و دارای seller-role یا seller_profile (HasSellerProfile)
    - update/delete: فقط صاحب Seller (IsSellerOwnerOrAdmin) یا admin
    """
    queryset = Seller.objects.all()
    serializer_class = SellerSerializer
    filterset_fields = ['is_verified', 'business_type']
    search_fields = ['company_name', 'location']
    ordering_fields = ['created_at']

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        if self.action == "create":
            # برای ساخت صفحهٔ شرکت، کاربر باید لاگین کرده و HasSellerProfile را داشته باشد
            return [permissions.IsAuthenticated(), HasSellerProfile()]
        # ویرایش/حذف: فقط صاحب صفحه یا admin
        return [permissions.IsAuthenticated(), IsSellerOwnerOrAdmin()]

    def perform_create(self, serializer):
        """
        هنگام ایجاد Seller، اطمینان حاصل کن که فیلد user از request.user پر شده است.
        اگر به هر دلیلی request.user وجود نداشته باشد، خطای مناسبی برمی‌گردانیم.
        """
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            # اجازه نمی‌دهیم seller بدون کاربر ایجاد شود؛ این حالت عادی نباید رخ دهد
            raise PermissionError("Authentication required to create a seller.")
        # If the user already has a Seller, avoid creating a duplicate.
        # Use get_or_create to be race-safe for concurrent requests.
        from django.db import IntegrityError, transaction

        validated = getattr(serializer, 'validated_data', {})

        try:
            # Attempt atomic get_or_create using fields from validated_data
            defaults = {
                'company_name': validated.get('company_name'),
                'business_type': validated.get('business_type'),
                'location': validated.get('location'),
                'is_verified': validated.get('is_verified', False),
            }
            with transaction.atomic():
                seller_obj, created = Seller.objects.get_or_create(user=user, defaults=defaults)

                # If created is True, we should ensure any additional fields validated
                # are saved (get_or_create already saved defaults).
                # Attach the instance to the serializer so the view returns serialized data.
                serializer.instance = seller_obj
                return
        except IntegrityError:
            # In rare race conditions, another transaction may have created the Seller
            # between our check and create. Try to fetch the existing Seller and attach it.
            try:
                seller_obj = Seller.objects.get(user=user)
                serializer.instance = seller_obj
                return
            except Seller.DoesNotExist:
                # If we still can't find it, re-raise so the error surfaces for investigation
                raise
