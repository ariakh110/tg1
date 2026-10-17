from django.contrib import admin
from .models import (
    Product, ProductCategory, ProductImage, ProductSpecification, 
    ProductStandard, SpecificationAttribute, SpecificationValue, 
    ProductAttributeOption, ProductAuditLog, ProductPriceSnapshot, Offer, DeliveryLocation, PricingTier, ProductDocument, Seller,
    CommodityExchangeTrade, GlobalMetalInstrument, GlobalMetalObservation, MarketDataSyncState,
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
    list_display = (
        "name",
        "parent",
        "code",
        "product_kind",
        "icon_key",
        "show_in_navigation",
        "sort_order",
        "is_active",
    )
    search_fields = ("name", "hscode", "code")
    list_filter = ("parent", "product_kind", "show_in_navigation", "is_active")


# ---------- محصول ----------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "category", "availability_status", "is_active", "created_at")
    list_filter = ("is_active", "availability_status", "category")
    search_fields = ("name", "slug", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("-created_at",)
    filter_horizontal = ("related_products",)

    inlines = [ProductImageInline, ProductDocumentInline, ProductSpecificationInline, SpecificationValueInline]


@admin.register(ProductAuditLog)
class ProductAuditLogAdmin(admin.ModelAdmin):
    list_display = ("product_name", "action", "actor_user", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("product_name", "actor_user__username", "payload")
    readonly_fields = ("product", "product_name", "action", "actor_user", "payload", "created_at")


@admin.register(ProductPriceSnapshot)
class ProductPriceSnapshotAdmin(admin.ModelAdmin):
    list_display = ("product", "pricing_basis", "price", "normalized_price_kg", "observed_on", "observed_at")
    list_filter = ("pricing_basis", "observed_on", "source")
    search_fields = ("product__name", "product__slug")
    readonly_fields = ("product", "pricing_basis", "price", "normalized_price_kg", "observed_on", "observed_at", "source")


@admin.register(CommodityExchangeTrade)
class CommodityExchangeTradeAdmin(admin.ModelAdmin):
    list_display = ("trade_date_jalali", "goods_name", "symbol", "producer_name", "weighted_price", "traded_volume", "unit")
    list_filter = ("trade_date", "product_group", "hall", "contract_type")
    search_fields = ("goods_name", "symbol", "producer_name")
    readonly_fields = tuple(field.name for field in CommodityExchangeTrade._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(GlobalMetalInstrument)
class GlobalMetalInstrumentAdmin(admin.ModelAdmin):
    list_display = ("name_fa", "code", "exchange", "currency", "unit", "is_active", "sort_order")
    list_filter = ("exchange", "is_active")
    search_fields = ("name_fa", "name_en", "code")


@admin.register(GlobalMetalObservation)
class GlobalMetalObservationAdmin(admin.ModelAdmin):
    list_display = ("instrument", "provider", "price", "observed_on", "fetched_at")
    list_filter = ("provider", "instrument__exchange", "observed_on")
    search_fields = ("instrument__name_fa", "instrument__name_en", "instrument__code")
    readonly_fields = tuple(field.name for field in GlobalMetalObservation._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(MarketDataSyncState)
class MarketDataSyncStateAdmin(admin.ModelAdmin):
    list_display = ("key", "status", "record_count", "finished_at", "updated_at")
    readonly_fields = tuple(field.name for field in MarketDataSyncState._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ---------- استاندارد ----------
@admin.register(ProductStandard)
class ProductStandardAdmin(admin.ModelAdmin):
    list_display = ("name", "description")


# ---------- ویژگی‌ها ----------
@admin.register(SpecificationAttribute)
class SpecificationAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "unit")


@admin.register(ProductAttributeOption)
class ProductAttributeOptionAdmin(admin.ModelAdmin):
    list_display = ("group", "label", "value", "product_kind", "category", "parent", "sort_order", "is_active")
    list_filter = ("group", "product_kind", "is_active")
    search_fields = ("label", "value", "group")


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
