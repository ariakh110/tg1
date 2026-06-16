from django.contrib import admin

from .models import SeoAssistantSettings, SeoConversation, SeoKnowledge, SeoMessage


@admin.register(SeoAssistantSettings)
class SeoAssistantSettingsAdmin(admin.ModelAdmin):
    list_display = ("assistant_name", "is_enabled", "chat_model", "embedding_model", "openai_base_url", "updated_at")


@admin.register(SeoKnowledge)
class SeoKnowledgeAdmin(admin.ModelAdmin):
    list_display = ("display_title", "layer", "topic", "source", "is_active", "sort_order", "embedded_at", "updated_at")
    list_filter = ("layer", "is_active", "topic")
    search_fields = ("title", "body", "tags", "source")


class SeoMessageInline(admin.TabularInline):
    model = SeoMessage
    extra = 0
    readonly_fields = ("role", "content", "tool_name", "created_at")


@admin.register(SeoConversation)
class SeoConversationAdmin(admin.ModelAdmin):
    list_display = ("session_key", "title", "status", "user", "updated_at")
    list_filter = ("status",)
    search_fields = ("session_key", "title")
    inlines = [SeoMessageInline]
