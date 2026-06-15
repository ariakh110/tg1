from django.contrib import admin

from .models import AssistantConversation, AssistantKnowledge, AssistantMessage, AssistantSettings


@admin.register(AssistantSettings)
class AssistantSettingsAdmin(admin.ModelAdmin):
    list_display = ("assistant_name", "is_enabled", "chat_model", "embedding_model", "lead_capture_enabled", "updated_at")


@admin.register(AssistantKnowledge)
class AssistantKnowledgeAdmin(admin.ModelAdmin):
    list_display = ("display_title", "kind", "topic", "is_active", "sort_order", "embedded_at", "updated_at")
    list_filter = ("kind", "topic", "is_active")
    search_fields = ("title", "question", "answer", "body", "tags")


class AssistantMessageInline(admin.TabularInline):
    model = AssistantMessage
    extra = 0
    readonly_fields = ("role", "content", "tool_name", "created_at")


@admin.register(AssistantConversation)
class AssistantConversationAdmin(admin.ModelAdmin):
    list_display = ("session_key", "status", "lead_name", "lead_phone", "updated_at")
    list_filter = ("status",)
    search_fields = ("session_key", "lead_name", "lead_phone", "lead_interest")
    inlines = [AssistantMessageInline]
