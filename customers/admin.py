from django.contrib import admin

from .models import (
    CrmOpportunity,
    CrmOpportunityStageHistory,
    CrmSyncEvent,
    Customer,
    CustomerActivity,
    CustomerTransaction,
)


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


class CrmOpportunityInline(admin.TabularInline):
    model = CrmOpportunity
    extra = 0
    fields = ("title", "stage", "source_type", "expected_value_irr", "owner", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "company", "city", "stage", "source", "balance_display", "is_active", "updated_at")
    list_filter = ("stage", "source", "is_active", "province", "city")
    search_fields = ("name", "phone", "company")
    inlines = [CrmOpportunityInline, CustomerActivityInline, CustomerTransactionInline]

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


class CrmOpportunityStageHistoryInline(admin.TabularInline):
    model = CrmOpportunityStageHistory
    extra = 0
    can_delete = False
    fields = ("from_stage", "to_stage", "event", "reason", "actor_user", "created_at")
    readonly_fields = fields


@admin.register(CrmOpportunity)
class CrmOpportunityAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "customer",
        "stage",
        "source_type",
        "expected_value_irr",
        "owner",
        "updated_at",
    )
    list_filter = ("stage", "source_type", "is_active")
    search_fields = ("title", "customer__name", "customer__phone", "source_id")
    autocomplete_fields = ("customer", "owner")
    inlines = [CrmOpportunityStageHistoryInline]


@admin.register(CrmOpportunityStageHistory)
class CrmOpportunityStageHistoryAdmin(admin.ModelAdmin):
    list_display = ("opportunity", "from_stage", "to_stage", "event", "actor_user", "created_at")
    list_filter = ("to_stage", "event")
    search_fields = ("opportunity__title", "event_key", "reason")
    readonly_fields = (
        "opportunity",
        "from_stage",
        "to_stage",
        "event",
        "event_key",
        "reason",
        "actor_user",
        "metadata",
        "created_at",
    )


@admin.register(CrmSyncEvent)
class CrmSyncEventAdmin(admin.ModelAdmin):
    list_display = ("source_type", "source_id", "status", "attempts", "processed_at", "updated_at")
    list_filter = ("source_type", "status")
    search_fields = ("source_id", "event_key", "last_error")
    readonly_fields = (
        "source_type",
        "source_id",
        "event_key",
        "status",
        "attempts",
        "last_error",
        "payload",
        "processed_at",
        "created_at",
        "updated_at",
    )
