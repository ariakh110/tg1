from rest_framework import serializers

from .models import AssistantConversation, AssistantKnowledge, AssistantMessage, AssistantSettings


class AssistantKnowledgeSerializer(serializers.ModelSerializer):
    display_title = serializers.CharField(read_only=True)
    needs_embedding = serializers.BooleanField(read_only=True)
    is_embedded = serializers.SerializerMethodField()

    class Meta:
        model = AssistantKnowledge
        fields = (
            "id", "kind", "topic", "title", "question", "answer", "body", "tags",
            "is_active", "sort_order", "display_title", "needs_embedding", "is_embedded",
            "created_at", "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def get_is_embedded(self, obj):
        return bool(obj.embedding) and obj.embedded_hash == obj.content_hash()


class AssistantSettingsSerializer(serializers.ModelSerializer):
    api_key_configured = serializers.SerializerMethodField()

    class Meta:
        model = AssistantSettings
        fields = (
            "is_enabled", "assistant_name", "greeting", "persona", "sales_workflow",
            "openai_base_url", "chat_model", "embedding_model", "temperature",
            "max_context_chunks", "max_tool_iterations", "lead_capture_enabled",
            "handoff_phone", "handoff_note", "api_key_configured", "updated_at",
        )
        read_only_fields = ("updated_at",)

    def get_api_key_configured(self, obj):
        return bool(obj.api_key)


class PublicAssistantConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantSettings
        fields = ("is_enabled", "assistant_name", "greeting", "lead_capture_enabled", "handoff_phone")


class AssistantMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantMessage
        fields = ("id", "role", "content", "tool_name", "tool_payload", "created_at")


class AssistantConversationSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(source="messages.count", read_only=True)

    class Meta:
        model = AssistantConversation
        fields = (
            "id", "session_key", "status", "lead_name", "lead_phone", "lead_interest",
            "message_count", "created_at", "updated_at",
        )


class AssistantConversationDetailSerializer(AssistantConversationSerializer):
    messages = AssistantMessageSerializer(many=True, read_only=True)

    class Meta(AssistantConversationSerializer.Meta):
        fields = AssistantConversationSerializer.Meta.fields + ("messages",)
