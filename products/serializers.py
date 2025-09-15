# products/serializers.py
from rest_framework import serializers
from django.conf import settings
from .models import (
    Product, ProductCategory, ProductImage, ProductSpecification,
    ProductStandard, SpecificationAttribute, SpecificationValue,
    Offer, PricingTier, DeliveryLocation, ProductDocument, Seller
)


# -------------------------
# Category
# -------------------------
class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ("id", "name", "parent", "hscode")
        # parent: وقتی write انجام می‌شود باید id ارسال شود؛ برای نمایش فقط id برمی‌گردد.
        extra_kwargs = {
            "parent": {"required": False, "allow_null": True}
        }


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

    class Meta:
        model = ProductSpecification
        fields = (
            "id",
            "product",
            "material_type",
            "steel_grade",
            "standard",
            "standard_id",
            "thickness_mm",
            "width_mm",
            "length_mm",
            "weight_kg_per_unit",
            "surface_finish",
            "manufacturing_process",
        )
        read_only_fields = ("product",)


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
        fields = ("id", "offer", "tier_name", "unit_price", "minimum_quantity", "maximum_quantity", "is_negotiable")
        read_only_fields = ("offer",)  # اگر بخوای API جدا برای PricingTier بذاریم، offer لازم است؛ در Offer nested creation انجام نمی‌شود فعلاً.


class DeliveryLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryLocation
        fields = ("id", "offer", "incoterm", "country", "city", "port")
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
            "created_at",
            "updated_at",
            "specification",
            "images",
            "documents",
            "offers",
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
        fields = ("id", "name", "slug", "short_description", "description", "category", "is_active", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}


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
