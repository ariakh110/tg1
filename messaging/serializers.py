from rest_framework import serializers

from .models import MessagingSettings, OutboundMessage


class MessagingSettingsSerializer(serializers.ModelSerializer):
    api_key_configured = serializers.SerializerMethodField()
    is_configured = serializers.BooleanField(read_only=True)
    # کلیدِ کاوه‌نگار — فقط نوشتنی (هرگز در پاسخِ GET برنمی‌گردد).
    kavenegar_api_key = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=True
    )

    class Meta:
        model = MessagingSettings
        fields = (
            "sms_enabled", "provider", "kavenegar_api_key", "sender",
            "default_template", "purchase_template", "daily_send_cap",
            "api_key_configured", "is_configured", "webhook_secret", "updated_at",
        )
        read_only_fields = ("webhook_secret", "updated_at")

    def get_api_key_configured(self, obj):
        return bool((obj.kavenegar_api_key or "").strip())

    def update(self, instance, validated_data):
        # کلیدِ خالی ⇒ کلیدِ فعلی دست‌نخورده بماند (تصادفی پاک نشود).
        key = validated_data.pop("kavenegar_api_key", None)
        if key is not None and key.strip():
            instance.kavenegar_api_key = key.strip()
        return super().update(instance, validated_data)


class OutboundMessageSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    purpose_display = serializers.CharField(source="get_purpose_display", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")

    class Meta:
        model = OutboundMessage
        fields = (
            "id", "channel", "channel_display", "provider", "customer", "customer_name",
            "recipient", "purpose", "purpose_display", "template", "body",
            "status", "status_display", "provider_message_id", "cost", "error",
            "created_at", "updated_at",
        )
        read_only_fields = fields
