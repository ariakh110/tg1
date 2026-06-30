from rest_framework import serializers

from .models import MessagingSettings, OutboundMessage


class MessagingSettingsSerializer(serializers.ModelSerializer):
    api_key_configured = serializers.SerializerMethodField()
    is_configured = serializers.BooleanField(read_only=True)
    telegram_configured = serializers.BooleanField(read_only=True)
    telegram_token_configured = serializers.SerializerMethodField()
    # کلیدها — فقط نوشتنی (هرگز در پاسخِ GET برنمی‌گردند).
    kavenegar_api_key = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=True
    )
    telegram_bot_token = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=True
    )

    class Meta:
        model = MessagingSettings
        fields = (
            "sms_enabled", "provider", "kavenegar_api_key", "sender",
            "default_template", "purchase_template", "daily_send_cap",
            "telegram_enabled", "telegram_bot_token", "telegram_admin_chat_id", "telegram_api_base",
            "bale_webhook_enabled", "bale_admin_user_ids", "site_base_url",
            "admin_alert_phone", "notify_on_signup", "notify_on_order", "notify_on_chat_lead",
            "api_key_configured", "is_configured",
            "telegram_configured", "telegram_token_configured",
            "webhook_secret", "updated_at",
        )
        read_only_fields = ("webhook_secret", "updated_at")

    def get_api_key_configured(self, obj):
        return bool((obj.kavenegar_api_key or "").strip())

    def get_telegram_token_configured(self, obj):
        return bool((obj.telegram_bot_token or "").strip())

    def update(self, instance, validated_data):
        # کلیدهای خالی ⇒ مقدارِ فعلی دست‌نخورده بماند (تصادفی پاک نشود).
        for secret_field in ("kavenegar_api_key", "telegram_bot_token"):
            value = validated_data.pop(secret_field, None)
            if value is not None and value.strip():
                setattr(instance, secret_field, value.strip())
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
