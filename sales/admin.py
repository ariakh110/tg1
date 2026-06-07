from django.contrib import admin

from .models import (
    FreightRateSettings,
    StoreBuyerAddress,
    StoreBuyerInvoiceProfile,
    StoreOrder,
    StoreOrderItem,
    StoreOrderNotification,
    StoreOrderStatusHistory,
    StorePayment,
)


class StoreOrderItemInline(admin.TabularInline):
    model = StoreOrderItem
    extra = 0
    readonly_fields = (
        "product_name",
        "seller_name",
        "estimated_weight_kg",
        "price_weight_kg",
        "final_weight_kg",
        "unit_price_amount",
        "total_price_amount",
        "final_price_amount",
        "weight_adjustment_amount",
        "product_snapshot",
        "specification_snapshot",
        "delivery_snapshot",
    )


@admin.register(StoreOrder)
class StoreOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "buyer",
        "status",
        "payment_status",
        "risk_status",
        "subtotal_amount",
        "settlement_term_fee_amount",
        "weight_adjustment_amount",
        "total_amount",
        "price_valid_until",
        "payment_due_at",
        "created_at",
    )
    list_filter = ("status", "payment_status", "risk_status", "price_valid_until", "payment_due_at", "created_at")
    search_fields = ("id", "buyer__username", "contact_name", "contact_phone")
    inlines = [StoreOrderItemInline]


@admin.register(StoreOrderStatusHistory)
class StoreOrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "from_status", "to_status", "event", "actor_user", "at")
    list_filter = ("to_status", "event")
    search_fields = ("order__id", "actor_user__username")


@admin.register(StorePayment)
class StorePaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "amount", "currency", "status", "provider", "provider_reference", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("order__id", "provider_reference")


@admin.register(StoreOrderNotification)
class StoreOrderNotificationAdmin(admin.ModelAdmin):
    list_display = ("order", "channel", "recipient", "event", "status", "created_at")
    list_filter = ("channel", "status", "event")
    search_fields = ("order__id", "recipient", "event")


@admin.register(StoreBuyerAddress)
class StoreBuyerAddressAdmin(admin.ModelAdmin):
    list_display = ("buyer", "title", "province", "city", "phone", "is_default", "updated_at")
    list_filter = ("province", "city", "is_default")
    search_fields = ("buyer__username", "title", "province", "city", "phone")


@admin.register(StoreBuyerInvoiceProfile)
class StoreBuyerInvoiceProfileAdmin(admin.ModelAdmin):
    list_display = ("buyer", "buyer_type", "title", "full_name", "company_name", "phone", "is_default", "updated_at")
    list_filter = ("buyer_type", "is_default")
    search_fields = ("buyer__username", "full_name", "national_id", "company_name", "economic_code", "phone")


@admin.register(FreightRateSettings)
class FreightRateSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "year_label",
        "base_rate_toman",
        "default_vehicle_coefficient",
        "admin_fee_percent",
        "minimum_amount_toman",
        "updated_by",
        "updated_at",
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not FreightRateSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
