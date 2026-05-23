# products/views.py
from rest_framework import viewsets, permissions, filters, status, generics
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from django.db import transaction
from django.db.models import Min, Q
from django.http import HttpResponse
from accounts.permissions import IsAdminOrActiveAdminRole

# مدل‌ها
from .models import (
    Product, ProductAuditLog, ProductCategory, ProductImage, ProductSpecification,
    ProductStandard, SpecificationAttribute, SpecificationValue,
    ProductAttributeOption, Offer, PricingTier, DeliveryLocation, ProductDocument, Seller
)

# سریالایزرها (باید فایل serializers.py را مطابق نیازت داشته باشی)
from .serializers import (
    ProductListSerializer, ProductDetailSerializer, ProductWriteSerializer,
    ProductCategorySerializer, ProductImageSerializer, ProductSpecificationSerializer,
    ProductStandardSerializer, SpecificationAttributeSerializer, ProductAttributeOptionSerializer,
    SpecificationValueSerializer,
    OfferReadSerializer, OfferWriteSerializer, PricingTierSerializer, DeliveryLocationSerializer,
    ProductDocumentSerializer, SellerSerializer
)

# فیلترها و مجوزها (permissions)
from .filters import ProductFilter, ProductAttributeOptionFilter, OfferFilter  
from .permissions import (
    HasSellerProfile,
    IsAdminOrReadOnly,
    IsOfferOwner,
    IsProductAssetOwnerOrAdmin,
    IsSellerOwnerOrAdmin,
)
from .admin_import import bulk_upsert_products, read_price_file, upsert_product_row

# ---------------- Pagination استاندارد برای viewset ها ----------------
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 12                 # تعداد پیش‌فرض در هر صفحه
    page_size_query_param = "page_size"
    max_page_size = 100


def log_product_activity(product, action, actor, payload=None):
    ProductAuditLog.objects.create(
        product=product if getattr(product, "pk", None) else None,
        product_name=getattr(product, "name", "") or str(product),
        action=action,
        actor_user=actor if getattr(actor, "is_authenticated", False) else None,
        payload=payload or {},
    )


def log_catalog_activity(name, action, actor, payload=None):
    ProductAuditLog.objects.create(
        product=None,
        product_name=name,
        action=action,
        actor_user=actor if getattr(actor, "is_authenticated", False) else None,
        payload=payload or {},
    )


def request_has_admin_access(request, view=None):
    return IsAdminOrActiveAdminRole().has_permission(request, view)


class IsAdminRoleOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request_has_admin_access(request, view)


# ---------------- ProductCategoryViewSet ----------------
class ProductCategoryViewSet(viewsets.ModelViewSet):
    """
    مدیریت دسته‌بندی‌ها (درختی با mptt).
    - فقط admin می‌تواند دسته جدید بسازد/ویرایش کند (IsAdminOrReadOnly).
    - همه می‌توانند لیست/مشاهده کنند.
    """
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAdminRoleOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["parent", "hscode", "code", "product_kind", "is_active"]
    search_fields = ["name", "hscode", "code"]
    ordering_fields = ["sort_order", "name"]
    ordering = ["tree_id", "lft"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if request_has_admin_access(self.request, self):
            return queryset
        return queryset.filter(is_active=True)

    def perform_create(self, serializer):
        category = serializer.save()
        log_catalog_activity(
            category.name,
            "PRODUCT_CATEGORY_CREATED",
            self.request.user,
            {"category_id": category.id, "code": category.code, "parent_id": category.parent_id},
        )

    def perform_update(self, serializer):
        old_is_active = serializer.instance.is_active
        fields = list(serializer.validated_data.keys())
        category = serializer.save()
        action = "PRODUCT_CATEGORY_UPDATED"
        if "is_active" in fields and old_is_active != category.is_active:
            action = "PRODUCT_CATEGORY_ACTIVATED" if category.is_active else "PRODUCT_CATEGORY_DEACTIVATED"
        log_catalog_activity(
            category.name,
            action,
            self.request.user,
            {"category_id": category.id, "code": category.code, "fields": fields},
        )

    def _set_active_state(self, request, pk, is_active):
        category = self.get_object()
        previous = category.is_active
        if previous != is_active:
            category.is_active = is_active
            category.save(update_fields=["is_active"])
        action = "PRODUCT_CATEGORY_ACTIVATED" if is_active else "PRODUCT_CATEGORY_DEACTIVATED"
        log_catalog_activity(
            category.name,
            action,
            request.user,
            {
                "category_id": category.id,
                "code": category.code,
                "previous_is_active": previous,
                "is_active": category.is_active,
            },
        )
        serializer = self.get_serializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="deactivate",
        permission_classes=[IsAdminOrActiveAdminRole],
    )
    def deactivate(self, request, pk=None):
        return self._set_active_state(request, pk, False)

    @action(
        detail=True,
        methods=["post"],
        url_path="activate",
        permission_classes=[IsAdminOrActiveAdminRole],
    )
    def activate(self, request, pk=None):
        return self._set_active_state(request, pk, True)

    @action(detail=False, methods=["get"], url_path="active-with-products")
    def active_with_products(self, request):
        """
        دسته‌بندی‌های قابل انتخاب در لیست قیمت.
        ریشه‌هایی مثل «ورق» با وجود محصول فعال نمایش داده می‌شوند؛ زیرشاخه‌هایی مثل
        «ورق سیاه» فقط وقتی نمایش داده می‌شوند که محصول فعال منطبق با همان نوع داشته باشند.
        """
        active_products = Product.objects.filter(is_active=True, category__isnull=False)
        include_ids = set()
        roots = ProductCategory.objects.filter(parent__isnull=True, is_active=True).order_by("tree_id", "lft")

        def apply_spec_defaults(queryset, defaults):
            for field, value in (defaults or {}).items():
                if value in ("", None):
                    continue
                if hasattr(ProductSpecification, field):
                    queryset = queryset.filter(**{f"specifications__{field}__iexact": value})
            return queryset

        for root in roots:
            root_categories = root.get_descendants(include_self=True)
            root_products = active_products.filter(category__in=root_categories)
            if not root_products.exists():
                continue

            include_ids.add(root.id)
            for child in root.get_children().filter(is_active=True).order_by("sort_order", "name"):
                child_categories = child.get_descendants(include_self=True)
                direct_products = active_products.filter(category__in=child_categories)
                ancestor_products = active_products.filter(category__in=child.get_ancestors())
                matching_ancestor_products = apply_spec_defaults(
                    ancestor_products,
                    child.merged_spec_defaults(),
                )
                if direct_products.exists() or matching_ancestor_products.exists():
                    include_ids.add(child.id)

        queryset = ProductCategory.objects.filter(id__in=include_ids, is_active=True).order_by("tree_id", "lft")
        serializer = self.get_serializer(queryset, many=True)
        return Response({"count": queryset.count(), "results": serializer.data})


# ---------------- ProductViewSet ----------------
class ProductViewSet(viewsets.ModelViewSet):
    """
    عملیات CRUD روی محصولات:
    - queryset با select_related/prefetch_related برای کارایی بهتر
    - همچنین annotate برای min_price تا فرانت سریع‌تر کمترین قیمت محصول را دریافت کند
    - برای خواندن عمومی است؛ نوشتن فقط برای admin (IsAdminOrReadOnly)
    """
    queryset = Product.objects.select_related("category").prefetch_related(
        "images",
        "documents",
        "offers__seller",
        "offers__pricing_tiers",
        "offers__delivery_options",
        "dynamic_specs",
    ).annotate(min_price=Min('offers__pricing_tiers__unit_price'))  # حداقل قیمت از بین offers -> pricing_tiers
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter    
    search_fields = [
        "name",
        "short_description",
        "description",
        "slug",
        "category__name",
        "specifications__steel_grade",
        "specifications__material_type",
        "specifications__surface_finish",
        "specifications__manufacturing_process",
        "specifications__factory",
        "specifications__cut_type",
    ]
    ordering_fields = ["created_at", "updated_at", "name", "min_price"]
    ordering = ["-created_at", "id"]
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

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            return queryset.filter(is_active=True)
        return queryset

    def _filtered_admin_queryset(self):
        queryset = self.get_queryset()
        search = (self.request.query_params.get("q") or "").strip()
        raw_is_active = self.request.query_params.get("is_active")
        is_active = "" if raw_is_active is None else str(raw_is_active).strip().lower()
        category_id = (self.request.query_params.get("category") or "").strip()
        category_code = (self.request.query_params.get("category_code") or "").strip()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(slug__icontains=search)
                | Q(short_description__icontains=search)
                | Q(category__name__icontains=search)
                | Q(specifications__steel_grade__icontains=search)
            )
        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=(is_active == "true"))
        category = None
        if category_code:
            category = ProductCategory.objects.filter(code=category_code).first()
        elif category_id:
            category = ProductCategory.objects.filter(pk=category_id).first()
        if category:
            queryset = queryset.filter(category__in=category.get_descendants(include_self=True))
        return queryset.distinct().order_by("-created_at", "id")

    def perform_create(self, serializer):
        product = serializer.save()
        log_product_activity(
            product,
            "PRODUCT_CREATED",
            self.request.user,
            {"source": "product_api"},
        )

    def perform_update(self, serializer):
        fields = list(serializer.validated_data.keys())
        product = serializer.save()
        log_product_activity(
            product,
            "PRODUCT_UPDATED",
            self.request.user,
            {"fields": fields, "source": "product_api"},
        )

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        payload = {
            "product_id": product.id,
            "category_id": product.category_id,
            "is_active": product.is_active,
            "source": "admin_dashboard",
        }
        log_product_activity(product, "PRODUCT_DELETED", request.user, payload)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_permissions(self):
        # allow authenticated sellers to create products (they will then create Offers)
        if self.action == 'create':
            return [permissions.IsAuthenticated(), HasSellerProfile()]
        return [p() for p in self.permission_classes]

    @action(
        detail=False,
        methods=["get"],
        url_path="admin-products",
        permission_classes=[IsAdminOrActiveAdminRole],
    )
    def admin_products(self, request):
        """
        لیست کامل محصولات برای ادمین، شامل محصولات فعال و غیرفعال.
        """
        queryset = self._filtered_admin_queryset()
        page = self.paginate_queryset(queryset)
        serializer = ProductListSerializer(
            page if page is not None else queryset,
            many=True,
            context={"request": request},
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="deactivate",
        permission_classes=[IsAdminOrActiveAdminRole],
    )
    def deactivate(self, request, pk=None):
        product = self.get_object()
        if product.is_active:
            product.is_active = False
            product.save(update_fields=["is_active", "updated_at"])
        log_product_activity(product, "PRODUCT_DEACTIVATED", request.user, {"source": "admin_dashboard"})
        serializer = ProductListSerializer(product, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="activate",
        permission_classes=[IsAdminOrActiveAdminRole],
    )
    def activate(self, request, pk=None):
        product = self.get_object()
        if not product.is_active:
            product.is_active = True
            product.save(update_fields=["is_active", "updated_at"])
        log_product_activity(product, "PRODUCT_ACTIVATED", request.user, {"source": "admin_dashboard"})
        serializer = ProductListSerializer(product, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

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

    @action(
        detail=False,
        methods=["post"],
        url_path="admin-upsert",
        permission_classes=[IsAdminOrActiveAdminRole],
    )
    def admin_upsert(self, request):
        """
        ثبت یا به‌روزرسانی محصول توسط ادمین همراه با مشخصات، قیمت و مبدا بار.
        """
        try:
            with transaction.atomic():
                result = upsert_product_row(
                    request.data,
                    default_seller_id=request.data.get("seller_id") or request.data.get("default_seller_id"),
                    create_missing=True,
                )
                product = Product.objects.get(pk=result["product_id"])
                log_product_activity(
                    product,
                    "PRODUCT_UPSERTED",
                    request.user,
                    {"result": result, "source": "admin_dashboard"},
                )
        except Exception as exc:
            detail = getattr(exc, "detail", None)
            return Response({"detail": detail or str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="admin-bulk-upsert",
        permission_classes=[IsAdminOrActiveAdminRole],
    )
    def admin_bulk_upsert(self, request):
        """
        دریافت CSV/XLSX و ثبت/آپدیت ردیفی محصولات و قیمت‌ها.
        """
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"detail": "فایل CSV یا XLSX ارسال نشده است."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rows = read_price_file(uploaded_file)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if not rows:
            return Response({"detail": "فایل ردیف قابل پردازش ندارد."}, status=status.HTTP_400_BAD_REQUEST)

        create_missing = str(request.data.get("create_missing", "true")).lower() not in {"0", "false", "no"}
        result = bulk_upsert_products(
            rows,
            default_seller_id=request.data.get("default_seller_id") or request.data.get("seller_id"),
            create_missing=create_missing,
        )
        ProductAuditLog.objects.create(
            product=None,
            product_name="Bulk product import",
            action="PRODUCT_BULK_UPSERTED",
            actor_user=request.user if request.user.is_authenticated else None,
            payload={
                "total_rows": result["total_rows"],
                "created_products": result["created_products"],
                "updated_prices": result["updated_prices"],
                "failed_rows": result["failed_rows"],
                "source": "admin_dashboard",
            },
        )
        response_status = status.HTTP_207_MULTI_STATUS if result["failed_rows"] else status.HTTP_200_OK
        return Response(result, status=response_status)

    @action(
        detail=False,
        methods=["get"],
        url_path="admin-import-template",
        permission_classes=[IsAdminOrActiveAdminRole],
    )
    def admin_import_template(self, request):
        """
        دانلود نمونه فایل Excel برای ثبت/آپدیت گروهی محصولات.
        """
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill
            from openpyxl.utils import get_column_letter
        except ImportError:
            return Response({"detail": "openpyxl نصب نیست."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        seller = Seller.objects.order_by("id").first()
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "products"
        headers = [
            "شناسه محصول",
            "نام کالا",
            "کد دسته",
            "شناسه فروشنده",
            "قیمت جدید",
            "آلیاژ",
            "نوع ورق/رول",
            "نوع سطح",
            "کارخانه",
            "نوع برش",
            "ضخامت",
            "عرض",
            "طول",
            "قطر",
            "وضعیت موجودی",
            "استان",
            "شهر",
            "آدرس",
        ]
        sheet.append(headers)
        sheet.append([
            "",
            "ورق سیاه ۳ میل مبارکه",
            "sheet-black-mobarakeh",
            seller.id if seller else "",
            1310000,
            "ST37",
            "sheet",
            "black",
            "mobarakeh",
            "cut",
            3,
            1500,
            6000,
            "",
            "in_stock",
            "اصفهان",
            "مبارکه",
            "کارخانه مبارکه",
        ])
        sheet.append([
            "",
            "میلگرد آجدار ۱۴",
            "rebar-ribbed",
            seller.id if seller else "",
            28500,
            "A3",
            "",
            "",
            "",
            "",
            "",
            12000,
            14,
            "in_stock",
            "تهران",
            "تهران",
            "انبار تهران",
        ])

        header_fill = PatternFill("solid", fgColor="DCEBFF")
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.fill = header_fill
        for index, _header in enumerate(headers, start=1):
            sheet.column_dimensions[get_column_letter(index)].width = 18
        sheet.freeze_panes = "A2"
        sheet.sheet_view.rightToLeft = True

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="kavehmetal-products-template.xlsx"'
        workbook.save(response)
        return response


# ---------------- ProductSpecificationViewSet ----------------
class ProductSpecificationViewSet(viewsets.ModelViewSet):
    """
    مشخصات فنی محصول (OneToOne یا رکوردهای مربوطه).
    نوشتن: admin یا seller صاحب محصول (HasSellerProfile) می‌تواند مشخصات را ایجاد/ویرایش کند.
    خواندن: همه
    """
    queryset = ProductSpecification.objects.select_related("product", "standard")
    serializer_class = ProductSpecificationSerializer
    # allow sellers to create specs for their own products; reads still public
    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        if self.action == "create":
            return [permissions.IsAuthenticated(), HasSellerProfile()]
        return [permissions.IsAuthenticated(), IsSellerOwnerOrAdmin()]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = [
        "product",
        "steel_grade",
        "material_type",
        "surface_finish",
        "manufacturing_process",
        "diameter_mm",
    ]
    search_fields = ["steel_grade", "material_type", "surface_finish", "manufacturing_process"]


# ---------------- SpecificationAttribute & SpecificationValue ----------------
class SpecificationAttributeViewSet(viewsets.ModelViewSet):
    """
    تعریف ویژگی‌های قابل افزودن برای محصولات (مثلاً 'ضخامت', 'نوع سطح' و ...).
    """
    queryset = SpecificationAttribute.objects.all()
    serializer_class = SpecificationAttributeSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["name"]


class ProductAttributeOptionViewSet(viewsets.ModelViewSet):
    """
    گزینه‌های کنترل‌شده برای فرم ثبت محصول:
    مثل گرید فولاد، نوع سطح، فرایند تولید، استان و شهر.
    """
    queryset = ProductAttributeOption.objects.select_related("category", "parent")
    serializer_class = ProductAttributeOptionSerializer
    permission_classes = [IsAdminRoleOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductAttributeOptionFilter
    search_fields = ["label", "value", "group"]
    ordering_fields = ["group", "sort_order", "label"]
    ordering = ["group", "sort_order", "label"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if request_has_admin_access(self.request, self):
            return queryset
        return queryset.filter(is_active=True)

    def perform_create(self, serializer):
        option = serializer.save()
        log_catalog_activity(
            option.label,
            "TAXONOMY_OPTION_CREATED",
            self.request.user,
            {
                "option_id": option.id,
                "group": option.group,
                "value": option.value,
                "product_kind": option.product_kind,
                "parent_id": option.parent_id,
            },
        )

    def perform_update(self, serializer):
        old_is_active = serializer.instance.is_active
        fields = list(serializer.validated_data.keys())
        option = serializer.save()
        action = "TAXONOMY_OPTION_UPDATED"
        if "is_active" in fields and old_is_active != option.is_active:
            action = "TAXONOMY_OPTION_ACTIVATED" if option.is_active else "TAXONOMY_OPTION_DEACTIVATED"
        log_catalog_activity(
            option.label,
            action,
            self.request.user,
            {
                "option_id": option.id,
                "group": option.group,
                "value": option.value,
                "fields": fields,
            },
        )

    def _set_active_state(self, request, pk, is_active):
        option = self.get_object()
        previous = option.is_active
        if previous != is_active:
            option.is_active = is_active
            option.save(update_fields=["is_active"])
        action = "TAXONOMY_OPTION_ACTIVATED" if is_active else "TAXONOMY_OPTION_DEACTIVATED"
        log_catalog_activity(
            option.label,
            action,
            request.user,
            {
                "option_id": option.id,
                "group": option.group,
                "value": option.value,
                "previous_is_active": previous,
                "is_active": option.is_active,
            },
        )
        serializer = self.get_serializer(option)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="deactivate",
        permission_classes=[IsAdminOrActiveAdminRole],
    )
    def deactivate(self, request, pk=None):
        return self._set_active_state(request, pk, False)

    @action(
        detail=True,
        methods=["post"],
        url_path="activate",
        permission_classes=[IsAdminOrActiveAdminRole],
    )
    def activate(self, request, pk=None):
        return self._set_active_state(request, pk, True)


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
        return [permissions.IsAuthenticated(), IsProductAssetOwnerOrAdmin()]

    def perform_create(self, serializer):
        product = serializer.validated_data.get("product")
        user = self.request.user
        seller_profile = getattr(user, "seller_profile", None)
        can_manage = bool(user.is_staff or user.is_superuser)
        if not can_manage:
            can_manage = bool(
                seller_profile
                and Offer.objects.filter(product=product, seller=seller_profile).exists()
            )
        if not can_manage:
            raise PermissionDenied("You are not allowed to upload image for this product.")
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
        return [permissions.IsAuthenticated(), IsProductAssetOwnerOrAdmin()]

    def perform_create(self, serializer):
        product = serializer.validated_data.get("product")
        user = self.request.user
        seller_profile = getattr(user, "seller_profile", None)
        can_manage = bool(user.is_staff or user.is_superuser)
        if not can_manage:
            can_manage = bool(
                seller_profile
                and Offer.objects.filter(product=product, seller=seller_profile).exists()
            )
        if not can_manage:
            raise PermissionDenied("You are not allowed to upload document for this product.")
        serializer.save()


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
            raise PermissionDenied("User does not have a seller profile.")
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
    filterset_fields = ["offer", "incoterm", "country", "province", "city"]
    search_fields = ["country", "province", "city", "port", "address"]
    
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
    Manage seller profile records.
    - list/retrieve: public
    - create: authenticated user (idempotent)
    - update/delete: owner or admin
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
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsSellerOwnerOrAdmin()]

    def create(self, request, *args, **kwargs):
        existing = getattr(request.user, "seller_profile", None)
        if existing:
            serializer = self.get_serializer(existing, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required to create a seller profile.")
        serializer.save(user=user, is_verified=False)

# use in account/urls
class SellerDetailView(generics.RetrieveUpdateAPIView):
    queryset = Seller.objects.all()
    serializer_class = SellerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        if obj.user != self.request.user:
            self.permission_denied(self.request)
        return obj

