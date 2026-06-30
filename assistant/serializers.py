from rest_framework import serializers

from .models import (
    AssistantConversation,
    AssistantInquiry,
    AssistantKnowledge,
    AssistantMessage,
    AssistantSettings,
)


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
    # کلیدِ اختصاصیِ این دستیار — فقط نوشتنی (هرگز در پاسخِ GET برنمی‌گردد).
    openai_api_key = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=True
    )

    class Meta:
        model = AssistantSettings
        fields = (
            "is_enabled", "assistant_name", "greeting", "persona", "sales_workflow",
            "openai_api_key", "openai_base_url", "chat_model", "embedding_model", "temperature",
            "max_context_chunks", "max_tool_iterations", "lead_capture_enabled", "lead_capture_mode",
            "handoff_phone", "handoff_note", "api_key_configured", "updated_at",
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


class AssistantInquirySerializer(serializers.ModelSerializer):
    summary = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    matched_product_title = serializers.SerializerMethodField()
    matched_product_url = serializers.SerializerMethodField()

    class Meta:
        model = AssistantInquiry
        fields = (
            "id", "product", "size", "grade", "factory", "quantity", "city", "note",
            "raw_text", "matched_product", "matched_product_title", "matched_product_url",
            "matched_price", "contact_name", "contact_phone", "status", "status_display",
            "summary", "created_at", "updated_at",
        )
        read_only_fields = (
            "product", "size", "grade", "factory", "quantity", "city", "note", "raw_text",
            "matched_product", "matched_price", "created_at", "updated_at",
        )

    def get_matched_product_title(self, obj):
        return obj.matched_product.name if obj.matched_product_id else ""

    def get_matched_product_url(self, obj):
        return f"/products/{obj.matched_product_id}" if obj.matched_product_id else ""
