from django.contrib import admin

from .models import Customer, CustomerActivity, CustomerTransaction


class CustomerTransactionInline(admin.TabularInline):
    model = CustomerTransaction
    extra = 0
    fields = ("kind", "amount", "description", "occurred_at", "created_at")
    readonly_fields = ("created_at",)


class CustomerActivityInline(admin.TabularInline):
    model = CustomerActivity
    extra = 0
    fields = ("kind", "body", "occurred_at", "follow_up_at", "follow_up_note", "follow_up_done")
    readonly_fields = ("created_at",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "company", "city", "stage", "source", "balance_display", "is_active", "updated_at")
    list_filter = ("stage", "source", "is_active", "province", "city")
    search_fields = ("name", "phone", "company")
    inlines = [CustomerActivityInline, CustomerTransactionInline]

    @admin.display(description="مانده (تومان)")
    def balance_display(self, obj):
        return f"{obj.balance:,}"


@admin.register(CustomerTransaction)
class CustomerTransactionAdmin(admin.ModelAdmin):
    list_display = ("customer", "kind", "amount", "description", "occurred_at", "created_at")
    list_filter = ("kind",)
    search_fields = ("customer__name", "customer__phone", "description")
    autocomplete_fields = ("customer",)


@admin.register(CustomerActivity)
class CustomerActivityAdmin(admin.ModelAdmin):
    list_display = ("customer", "kind", "occurred_at", "follow_up_at", "follow_up_done", "created_at")
    list_filter = ("kind", "follow_up_done")
    search_fields = ("customer__name", "customer__phone", "body", "follow_up_note")
    autocomplete_fields = ("customer",)
