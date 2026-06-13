# products/serializers.py
from rest_framework import serializers
from django.conf import settings
from .models import (
    Product, ProductCategory, ProductImage, ProductSpecification,
    ProductStandard, SpecificationAttribute, SpecificationValue,
    ProductAttributeOption, Offer, PricingTier, DeliveryLocation, ProductDocument, Seller
)


# -------------------------
# Category
# -------------------------
class ProductCategorySerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()
    level = serializers.IntegerField(read_only=True)
    full_path = serializers.SerializerMethodField()
    resolved_product_kind = serializers.SerializerMethodField()
    merged_spec_defaults = serializers.SerializerMethodField()
    merged_required_spec_fields = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    active_product_count = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = (
            "id",
            "name",
            "parent",
            "hscode",
            "code",
            "product_kind",
            "resolved_product_kind",
            "spec_defaults",
            "merged_spec_defaults",
            "required_spec_fields",
            "merged_required_spec_fields",
            "sort_order",
            "is_active",
            "level",
            "children_count",
            "product_count",
            "active_product_count",
            "full_path",
        )
        # parent: وقتی write انجام می‌شود باید id ارسال شود؛ برای نمایش فقط id برمی‌گردد.
        extra_kwargs = {
            "parent": {"required": False, "allow_null": True}
        }

    def get_full_path(self, obj):
        return " / ".join(category.name for category in obj.get_ancestors(include_self=True))

    def get_children_count(self, obj):
        return obj.get_children().count()

    def get_product_count(self, obj):
        categories = obj.get_descendants(include_self=True)
        return Product.objects.filter(category__in=categories).count()

    def get_active_product_count(self, obj):
        categories = obj.get_descendants(include_self=True)
        return Product.objects.filter(category__in=categories, is_active=True).count()

    def get_resolved_product_kind(self, obj):
        return obj.resolved_product_kind()

    def get_merged_spec_defaults(self, obj):
        return obj.merged_spec_defaults()

    def get_merged_required_spec_fields(self, obj):
        return obj.merged_required_spec_fields()


# -------------------------
# Seller
# -------------------------
class SellerSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(source="user", read_only=True)

    class Meta:
        model = Seller
        fields = ("id", "user_id", "company_name", "business_type", "location", "is_verified", "created_at")


# -------------------------
# Standards & Attributes
# -------------------------
class ProductStandardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductStandard
        fields = ("id", "name", "description")


class SpecificationAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecificationAttribute
        fields = ("id", "name", "unit")


class ProductAttributeOptionSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    active_product_count = serializers.SerializerMethodField()
    parent_label = serializers.SerializerMethodField()
    category_label = serializers.SerializerMethodField()

    class Meta:
        model = ProductAttributeOption
        fields = (
            "id",
            "group",
            "value",
            "label",
            "product_kind",
            "category",
            "category_label",
            "parent",
            "parent_label",
            "sort_order",
            "is_active",
            "product_count",
            "active_product_count",
        )

    SPEC_FIELD_BY_GROUP = {
        "manufacturing_process": "manufacturing_process",
        "surface_finish": "surface_finish",
        "steel_grade": "steel_grade",
        "factory": "factory",
        "cut_type": "cut_type",
    }

    def _product_queryset_for_option(self, obj):
        spec_field = self.SPEC_FIELD_BY_GROUP.get(obj.group)
        if spec_field:
            return Product.objects.filter(**{f"specifications__{spec_field}__iexact": obj.value}).distinct()
        if obj.group == "province":
            return Product.objects.filter(offers__delivery_options__province__iexact=obj.label).distinct()
        if obj.group == "city":
            return Product.objects.filter(offers__delivery_options__city__iexact=obj.label).distinct()
        if obj.group == "delivery_place":
            return Product.objects.filter(offers__delivery_options__address__iexact=obj.label).distinct()
        return Product.objects.none()

    def get_product_count(self, obj):
        return self._product_queryset_for_option(obj).count()

    def get_active_product_count(self, obj):
        return self._product_queryset_for_option(obj).filter(is_active=True).count()

    def get_parent_label(self, obj):
        return obj.parent.label if obj.parent else ""

    def get_category_label(self, obj):
        return obj.category.name if obj.category else ""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        group = attrs.get("group", getattr(self.instance, "group", ""))
        product_kind = attrs.get("product_kind", getattr(self.instance, "product_kind", ""))
        parent = attrs.get("parent", getattr(self.instance, "parent", None))

        def require_parent(expected_group, message):
            if not parent:
                raise serializers.ValidationError({"parent": message})
            if parent.group != expected_group:
                raise serializers.ValidationError({"parent": f"والد باید از گروه {expected_group} باشد."})

        if group == "factory":
            require_parent("manufacturing_process", "برای کارخانه باید ورق یا رول را به عنوان والد انتخاب کنید.")
        if group == "city":
            require_parent("province", "برای شهر باید استان را به عنوان والد انتخاب کنید.")
        if group == "steel_grade" and product_kind == "sheet":
            require_parent("surface_finish", "برای گرید ورق باید نوع ورق را به عنوان والد انتخاب کنید.")

        return attrs


class SpecificationValueSerializer(serializers.ModelSerializer):
    # نمایش attribute به صورت nested کوچک
    attribute = SpecificationAttributeSerializer(read_only=True)
    attribute_id = serializers.PrimaryKeyRelatedField(source="attribute", queryset=SpecificationAttribute.objects.all(), write_only=True)

    class Meta:
        model = SpecificationValue
        fields = ("id", "product", "attribute", "attribute_id", "value")
        read_only_fields = ("product",)  # product را از مسیر parent یا view باید تعیین کرد (یا فرستادن product_id مجاز است)


# -------------------------
# ProductSpecification (one-to-one)
# -------------------------
class ProductSpecificationSerializer(serializers.ModelSerializer):
    standard = ProductStandardSerializer(read_only=True)
    standard_id = serializers.PrimaryKeyRelatedField(source="standard", queryset=ProductStandard.objects.all(), write_only=True, allow_null=True, required=False)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    steel_grade_label = serializers.SerializerMethodField()
    surface_finish_label = serializers.SerializerMethodField()
    manufacturing_process_label = serializers.SerializerMethodField()
    factory_label = serializers.SerializerMethodField()
    cut_type_label = serializers.SerializerMethodField()

    class Meta:
        model = ProductSpecification
        fields = (
            "id",
            "product",
            "material_type",
            "steel_grade",
            "standard",
            "height_mm",
            "standard_id",
            "thickness_mm",
            "width_mm",
            "length_mm",
            "weight_kg_per_unit",
            "surface_finish",
            "manufacturing_process",
            "factory",
            "cut_type",
            "sales_mode",
            "head_tail_policy",
            "steel_grade_label",
            "surface_finish_label",
            "manufacturing_process_label",
            "factory_label",
            "cut_type_label",
            "diameter_mm",
        )

    def _option_label(self, obj, group, value):
        if value in (None, ""):
            return ""
        option = ProductAttributeOption.objects.filter(
            group=group,
            value=value,
            is_active=True,
        ).first()
        return option.label if option else str(value)

    def get_steel_grade_label(self, obj):
        return self._option_label(obj, "steel_grade", obj.steel_grade)

    def get_surface_finish_label(self, obj):
        return self._option_label(obj, "surface_finish", obj.surface_finish)

    def get_manufacturing_process_label(self, obj):
        return self._option_label(obj, "manufacturing_process", obj.manufacturing_process)

    def get_factory_label(self, obj):
        return self._option_label(obj, "factory", obj.factory)

    def get_cut_type_label(self, obj):
        return self._option_label(obj, "cut_type", obj.cut_type)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        product = attrs.get("product") or getattr(self.instance, "product", None)
        category = getattr(product, "category", None)
        if not category:
            return attrs

        def current_value(field):
            if field in attrs:
                return attrs.get(field)
            if self.instance is not None:
                return getattr(self.instance, field, None)
            return None

        defaults = category.merged_spec_defaults()
        for field, value in defaults.items():
            if field in self.fields and current_value(field) in (None, "") and value not in (None, ""):
                attrs[field] = value

        required_fields = category.merged_required_spec_fields()
        missing = [
            field
            for field in required_fields
            if field in self.fields and current_value(field) in (None, "")
        ]
        if missing:
            raise serializers.ValidationError(
                {field: "این مشخصه برای این دسته‌بندی الزامی است." for field in missing}
            )

        if attrs.get("steel_grade"):
            attrs["steel_grade"] = str(attrs["steel_grade"]).upper().replace(" ", "")
        product_kind = category.resolved_product_kind()

        def ensure_option(field, group, *, parent_field=None, parent_group=None):
            value = current_value(field)
            if value in (None, ""):
                return
            queryset = ProductAttributeOption.objects.filter(group=group, is_active=True)
            if product_kind:
                queryset = queryset.filter(product_kind__in=["", product_kind])
            if not queryset.exists():
                return
            if parent_field and parent_group:
                parent_value = current_value(parent_field)
                if parent_value not in (None, ""):
                    parent_queryset = ProductAttributeOption.objects.filter(
                        group=parent_group,
                        value=parent_value,
                        is_active=True,
                    )
                    if product_kind:
                        parent_queryset = parent_queryset.filter(product_kind__in=["", product_kind])
                    parent_option = parent_queryset.first()
                    if parent_option:
                        scoped_queryset = queryset.filter(parent=parent_option)
                        if scoped_queryset.exists():
                            if not scoped_queryset.filter(value=value).exists():
                                raise serializers.ValidationError(
                                    {field: "این گزینه برای انتخاب قبلی مجاز نیست."}
                                )
                            return
            if not queryset.filter(value=value).exists():
                raise serializers.ValidationError({field: "این گزینه در مدیریت تعریف نشده است."})

        for field, group in (
            ("surface_finish", "surface_finish"),
            ("manufacturing_process", "manufacturing_process"),
            ("factory", "factory"),
            ("cut_type", "cut_type"),
        ):
            ensure_option(field, group)
        ensure_option(
            "steel_grade",
            "steel_grade",
            parent_field="surface_finish" if product_kind == "sheet" else None,
            parent_group="surface_finish" if product_kind == "sheet" else None,
        )

        if product_kind == "sheet":
            process = (current_value("manufacturing_process") or "").strip().lower()
            sales_mode = (current_value("sales_mode") or "").strip()
            if not sales_mode:
                attrs["sales_mode"] = "coil_full" if process == "coil" else "sheet"
            elif process == "coil" and sales_mode == "sheet":
                raise serializers.ValidationError({"sales_mode": "برای رول باید یکی از حالت‌های فروش رول انتخاب شود."})
            elif process != "coil" and sales_mode in {"coil_full", "coil_cuttable", "coil_must_cut"}:
                raise serializers.ValidationError({"sales_mode": "حالت فروش رول فقط برای فرایند رول مجاز است."})
            sheet_required = ["manufacturing_process", "surface_finish", "factory", "thickness_mm", "width_mm"]
            if process == "sheet":
                sheet_required.extend(["length_mm", "cut_type"])
            missing_sheet = [
                field
                for field in sheet_required
                if field in self.fields and current_value(field) in (None, "")
            ]
            if missing_sheet:
                raise serializers.ValidationError(
                    {field: "این مشخصه برای ورق/رول الزامی است." for field in missing_sheet}
                )
            if process == "coil":
                attrs["length_mm"] = None
        return attrs


# -------------------------
# Images & Documents
# -------------------------
class ProductImageSerializer(serializers.ModelSerializer):
    # برگرداندن URL کامل تصویر در صورت وجود request
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "product", "image", "image_url", "is_featured")
        read_only_fields = ("image_url",)
        extra_kwargs = {
            "image": {"required": True}
        }

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image:
            try:
                url = obj.image.url
            except ValueError:
                return None
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class ProductDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductDocument
        fields = ("id", "product", "title", "file", "file_url")
        read_only_fields = ("file_url",)

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file:
            try:
                url = obj.file.url
            except ValueError:
                return None
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


# -------------------------
# PricingTier & DeliveryLocation (for Offer)
# -------------------------
class PricingTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingTier
        fields = (
            "id",
            "offer",
            "tier_name",
            "unit_price",
            "price_basis",
            "minimum_quantity",
            "maximum_quantity",
            "condition_label",
            "dimension_width_mm",
            "dimension_length_mm",
            "is_negotiable",
        )
        read_only_fields = ("offer",)  # اگر بخوای API جدا برای PricingTier بذاریم، offer لازم است؛ در Offer nested creation انجام نمی‌شود فعلاً.


class DeliveryLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryLocation
        fields = ("id", "offer", "incoterm", "country", "province", "city", "port", "address")
        read_only_fields = ("offer",)


# -------------------------
# Offer
# -------------------------
class OfferReadSerializer(serializers.ModelSerializer):
    # nested read serializers
    pricing_tiers = PricingTierSerializer(many=True, read_only=True)
    delivery_options = DeliveryLocationSerializer(many=True, read_only=True)
    seller = SellerSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(source="product", queryset=Product.objects.all(), write_only=True)

    class Meta:
        model = Offer
        fields = ("id", "product", "product_id", "seller", "is_active", "created_at", "pricing_tiers", "delivery_options")
        read_only_fields = ("created_at", "product")


class OfferWriteSerializer(serializers.ModelSerializer):
    # برای ایجاد/به‌روزرسانی: seller و product به صورت id ارسال می‌شوند
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    seller = serializers.PrimaryKeyRelatedField(queryset=Seller.objects.all())

    class Meta:
        model = Offer
        fields = ("id", "product", "seller", "is_active", "created_at")
        read_only_fields = ("created_at",)


# -------------------------
# Product (main serializer)
# -------------------------
class ProductListSerializer(serializers.ModelSerializer):
    # نمایش خلاصه محصول (لیست)
    category = ProductCategorySerializer(read_only=True)
    specification = ProductSpecificationSerializer(source="specifications", read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    documents = ProductDocumentSerializer(many=True, read_only=True)
    offers = OfferReadSerializer(many=True, read_only=True)
    min_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "short_description",
            "description",
            "category",
            "is_active",
            "availability_status",
            "purchase_terms",
            "created_at",
            "updated_at",
            "specification",
            "images",
            "documents",
            "offers",
            "min_price",
        )


class ProductDetailSerializer(ProductListSerializer):
    # اگر خواستی فیلدهای بیشتری در جزییات اضافه کن
    pass


# -------------------------
# Simple serializers for CRUD where client supplies IDs
# -------------------------
class ProductWriteSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=ProductCategory.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "short_description",
            "description",
            "category",
            "is_active",
            "availability_status",
            "purchase_terms",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def validate_category(self, value):
        if value is not None and not value.is_active:
            raise serializers.ValidationError("این دسته‌بندی غیرفعال است.")
        return value

    def validate_purchase_terms(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("شروط محصول باید به صورت لیست ارسال شود.")
        normalized = []
        for item in value:
            text = str(item or "").strip()
            if text:
                normalized.append(text[:500])
        return normalized

class ProductSummarySerializer(serializers.ModelSerializer):
    min_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    thumbnail = serializers.SerializerMethodField()
    steel_grade = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "slug", "min_price", "thumbnail", "steel_grade", "city"]

    def get_thumbnail(self, obj):
        first_image = obj.images.first()
        return self.context["request"].build_absolute_uri(first_image.image.url) if first_image else None

    def get_steel_grade(self, obj):
        try:
            return obj.specifications.steel_grade or ""
        except ProductSpecification.DoesNotExist:
            return ""

    def get_city(self, obj):
        for offer in obj.offers.all():
            for delivery in offer.delivery_options.all():
                if delivery.city:
                    return delivery.city
        return ""
# -------------------------
# Utility: small factory mapping for views
# -------------------------
# در viewset ها می‌توانی برای list/create از serializer متفاوت استفاده کنی:
#   def get_serializer_class(self):
#       if self.action in ['list', 'retrieve']:
#           return ProductListSerializer
#       return ProductWriteSerializer
#
# برای Offer:
#   def get_serializer_class(self):
#       if self.action in ['list', 'retrieve']:
#           return OfferReadSerializer
#       return OfferWriteSerializer
#
