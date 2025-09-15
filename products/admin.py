from django.contrib import admin
from .models import (
    Product, ProductCategory, ProductImage, ProductSpecification, 
    ProductStandard, SpecificationAttribute, SpecificationValue, 
    Offer, DeliveryLocation, PricingTier, ProductDocument, Seller
)

# ---------- Inline ها ----------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductDocumentInline(admin.TabularInline):
    model = ProductDocument
    extra = 1


class ProductSpecificationInline(admin.StackedInline):
    model = ProductSpecification
    extra = 0


class SpecificationValueInline(admin.TabularInline):
    model = SpecificationValue
    extra = 1


class PricingTierInline(admin.TabularInline):
    model = PricingTier
    extra = 1


class DeliveryLocationInline(admin.TabularInline):
    model = DeliveryLocation
    extra = 1


# ---------- دسته‌بندی ----------
@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "hscode")
    search_fields = ("name", "hscode")
    list_filter = ("parent",)


# ---------- محصول ----------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "category", "is_active", "created_at")
    list_filter = ("is_active", "category")
    search_fields = ("name", "slug", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("-created_at",)

    inlines = [ProductImageInline, ProductDocumentInline, ProductSpecificationInline, SpecificationValueInline]


# ---------- استاندارد ----------
@admin.register(ProductStandard)
class ProductStandardAdmin(admin.ModelAdmin):
    list_display = ("name", "description")


# ---------- ویژگی‌ها ----------
@admin.register(SpecificationAttribute)
class SpecificationAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "unit")


# ---------- پیشنهاد فروش ----------
@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("product", "seller", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("product__name", "seller__company_name")

    inlines = [PricingTierInline, DeliveryLocationInline]


# ---------- فروشنده ----------
@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ("company_name", "business_type", "location", "is_verified", "created_at")
    search_fields = ("company_name", "location")
    list_filter = ("is_verified", "business_type", "created_at")
