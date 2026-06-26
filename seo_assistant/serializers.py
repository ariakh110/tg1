from rest_framework import serializers

from .models import SeoAssistantSettings, SeoConversation, SeoKnowledge, SeoMessage


class SeoKnowledgeSerializer(serializers.ModelSerializer):
    display_title = serializers.CharField(read_only=True)
    needs_embedding = serializers.BooleanField(read_only=True)
    is_embedded = serializers.SerializerMethodField()

    class Meta:
        model = SeoKnowledge
        fields = (
            "id", "layer", "source", "topic", "title", "body", "tags",
            "is_active", "sort_order", "display_title", "needs_embedding", "is_embedded",
            "created_at", "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def get_is_embedded(self, obj):
        return bool(obj.embedding) and obj.embedded_hash == obj.content_hash()


class SeoAssistantSettingsSerializer(serializers.ModelSerializer):
    api_key_configured = serializers.SerializerMethodField()
    # کلیدِ اختصاصیِ این دستیار — فقط نوشتنی (هرگز در پاسخِ GET برنمی‌گردد).
    openai_api_key = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=True
    )

    class Meta:
        model = SeoAssistantSettings
        fields = (
            "is_enabled", "assistant_name", "greeting", "persona", "site_context",
            "openai_api_key", "openai_base_url", "chat_model", "embedding_model", "temperature",
            "max_context_chunks", "max_tool_iterations", "api_key_configured", "updated_at",
        )
        read_only_fields = ("updated_at",)

    def get_api_key_configured(self, obj):
        return bool(obj.api_key)

    def update(self, instance, validated_data):
        # کلیدِ خالی ⇒ کلیدِ فعلی دست‌نخورده بماند (تصادفی پاک نشود).
        key = validated_data.pop("openai_api_key", None)
        if key is not None and key.strip():
            instance.openai_api_key = key.strip()
        return super().update(instance, validated_data)


class SeoMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeoMessage
        fields = ("id", "role", "content", "tool_name", "tool_payload", "created_at")


class SeoConversationSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(source="messages.count", read_only=True)

    class Meta:
        model = SeoConversation
        fields = ("id", "session_key", "title", "status", "message_count", "created_at", "updated_at")


class SeoConversationDetailSerializer(SeoConversationSerializer):
    messages = SeoMessageSerializer(many=True, read_only=True)

    class Meta(SeoConversationSerializer.Meta):
        fields = SeoConversationSerializer.Meta.fields + ("messages",)
