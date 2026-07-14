from django.contrib import admin

from .models import (
    BaleUserBinding,
    MessagingContactGroup,
    MessagingContactGroupMember,
    MessagingSettings,
    OutboundMessage,
)


@admin.register(MessagingSettings)
class MessagingSettingsAdmin(admin.ModelAdmin):
    list_display = ("__str__", "provider", "sms_enabled", "updated_at")


@admin.register(BaleUserBinding)
class BaleUserBindingAdmin(admin.ModelAdmin):
    list_display = ("bale_user_id", "user", "display_name", "is_active", "verified_by", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("bale_user_id", "display_name", "user__username", "user__email")
    autocomplete_fields = ("user", "verified_by")


class MessagingContactGroupMemberInline(admin.TabularInline):
    model = MessagingContactGroupMember
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(MessagingContactGroup)
class MessagingContactGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "kavenegar_tag", "is_active", "updated_at")
    list_filter = ("source", "is_active")
    search_fields = ("name", "description", "kavenegar_tag")
    inlines = (MessagingContactGroupMemberInline,)


@admin.register(OutboundMessage)
class OutboundMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "channel", "recipient", "purpose", "status", "cost", "customer")
    list_filter = ("channel", "status", "purpose")
    search_fields = ("recipient", "body", "provider_message_id")
    readonly_fields = tuple(f.name for f in OutboundMessage._meta.fields)
