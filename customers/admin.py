from django.contrib import admin

from .models import Customer, CustomerTransaction


class CustomerTransactionInline(admin.TabularInline):
    model = CustomerTransaction
    extra = 0
    fields = ("kind", "amount", "description", "occurred_at", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "company", "city", "balance_display", "is_active", "updated_at")
    list_filter = ("is_active", "province", "city")
    search_fields = ("name", "phone", "company")
    inlines = [CustomerTransactionInline]

    @admin.display(description="مانده (تومان)")
    def balance_display(self, obj):
        return f"{obj.balance:,}"


@admin.register(CustomerTransaction)
class CustomerTransactionAdmin(admin.ModelAdmin):
    list_display = ("customer", "kind", "amount", "description", "occurred_at", "created_at")
    list_filter = ("kind",)
    search_fields = ("customer__name", "customer__phone", "description")
    autocomplete_fields = ("customer",)
