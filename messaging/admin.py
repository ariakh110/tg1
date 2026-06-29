from django.contrib import admin

from .models import MessagingSettings, OutboundMessage


@admin.register(MessagingSettings)
class MessagingSettingsAdmin(admin.ModelAdmin):
    list_display = ("__str__", "provider", "sms_enabled", "updated_at")


@admin.register(OutboundMessage)
class OutboundMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "channel", "recipient", "purpose", "status", "cost", "customer")
    list_filter = ("channel", "status", "purpose")
    search_fields = ("recipient", "body", "provider_message_id")
    readonly_fields = tuple(f.name for f in OutboundMessage._meta.fields)
