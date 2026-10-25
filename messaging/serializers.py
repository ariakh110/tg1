import re
import hashlib

from rest_framework import serializers

from accounts.admin_sections import ALL, effective_admin_sections

from .models import (
    BaleUserBinding,
    MessagingContactGroup,
    MessagingContactGroupMember,
    MessagingSettings,
    OutboundMessage,
)


class MessagingSettingsSerializer(serializers.ModelSerializer):
    market_google_relay_key = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=64)
    market_google_relay_configured = serializers.SerializerMethodField()
    market_telegram_bot_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    market_telegram_api_hash = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=32)
    market_telegram_api_hash_configured = serializers.SerializerMethodField()
    market_bale_bot_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    market_telegram_configured = serializers.SerializerMethodField()
    market_bale_configured = serializers.SerializerMethodField()
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
    safir_access_key = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=True
    )
    safir_configured = serializers.BooleanField(read_only=True)
    safir_key_configured = serializers.SerializerMethodField()

    class Meta:
        model = MessagingSettings
        fields = (
            "sms_enabled", "provider", "kavenegar_api_key", "sender",
            "default_template", "purchase_template", "daily_send_cap",
            "telegram_enabled", "telegram_bot_token", "telegram_admin_chat_id", "telegram_api_base",
            "bale_webhook_enabled", "bale_admin_user_ids", "site_base_url",
            "safir_enabled", "safir_access_key", "safir_bot_id",
            "admin_alert_phone", "notify_on_signup", "notify_on_order", "notify_on_chat_lead",
            "api_key_configured", "is_configured",
            "telegram_configured", "telegram_token_configured",
            "safir_configured", "safir_key_configured",
            "webhook_secret", "updated_at",
            "market_telegram_bot_token", "market_telegram_channel_id", "market_telegram_channel_url", "market_telegram_api_base",
            "market_bale_bot_token", "market_bale_channel_id", "market_bale_channel_url",
            "market_telegram_transport", "market_telegram_api_id", "market_telegram_api_hash", "market_telegram_api_hash_configured", "market_telegram_proxies",
            "market_contact_phone", "market_vat_percent", "market_telegram_configured", "market_bale_configured",
            "market_google_relay_key", "market_google_relay_configured", "market_google_relay_last_poll_at",
        )
        read_only_fields = ("webhook_secret", "updated_at", "market_google_relay_last_poll_at")

    def get_market_google_relay_configured(self, obj):
        return bool(obj.market_google_relay_key_hash)

    def validate_market_google_relay_key(self, value):
        if value and not re.fullmatch(r'[a-f0-9]{64}', value):
            raise serializers.ValidationError('کلید اتصال باید ۶۴ نویسه هگز کوچک باشد؛ از دکمه ساخت کلید استفاده کنید.')
        return value

    def get_api_key_configured(self, obj):
        return bool((obj.kavenegar_api_key or "").strip())

    def get_telegram_token_configured(self, obj):
        return bool((obj.telegram_bot_token or "").strip())

    def get_safir_key_configured(self, obj):
        return bool((obj.safir_access_key or "").strip())

    def update(self, instance, validated_data):
        relay_key = validated_data.pop('market_google_relay_key', '')
        if relay_key:
            instance.market_google_relay_key_hash = hashlib.sha256(relay_key.encode()).hexdigest()
        # کلیدهای خالی ⇒ مقدارِ فعلی دست‌نخورده بماند (تصادفی پاک نشود).
        for secret_field in ("kavenegar_api_key", "telegram_bot_token", "safir_access_key", "market_telegram_bot_token", "market_bale_bot_token", "market_telegram_api_hash"):
            value = validated_data.pop(secret_field, None)
            if value is not None and value.strip():
                setattr(instance, secret_field, value.strip())
        return super().update(instance, validated_data)

    def get_market_telegram_configured(self, obj):
        if obj.market_telegram_transport == 'google':
            return bool(obj.market_google_relay_key_hash and obj.market_telegram_channel_id)
        return bool(obj.market_telegram_bot_token and obj.market_telegram_channel_id)

    def get_market_telegram_api_hash_configured(self, obj):
        return bool(obj.market_telegram_api_hash)

    def validate_market_telegram_api_hash(self, value):
        if value and not re.fullmatch(r"[a-fA-F0-9]{32}", value):
            raise serializers.ValidationError("API Hash باید ۳۲ رقم هگز باشد.")
        return value

    def validate_market_telegram_api_id(self, value):
        if value is not None and not 0 < value <= 2147483647:
            raise serializers.ValidationError("API ID باید عدد مثبت معتبر باشد.")
        return value

    def validate_market_telegram_proxies(self, value):
        from .telegram_transport import validate_proxies
        try:
            return validate_proxies(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from None

    def get_market_bale_configured(self, obj):
        return bool(obj.market_bale_bot_token and obj.market_bale_channel_id)

    def validate_market_vat_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("درصد مالیات باید بین صفر و صد باشد.")
        return value

    def validate_market_telegram_api_base(self, value):
        from urllib.parse import urlsplit
        parsed = urlsplit(value)
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise serializers.ValidationError("آدرس API باید HTTPS و بدون رمز یا پارامتر باشد.")
        return value.rstrip("/")


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


class MessagingContactGroupMemberSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")

    class Meta:
        model = MessagingContactGroupMember
        fields = ("id", "customer", "customer_name", "phone", "name", "created_at")
        read_only_fields = fields


class MessagingContactGroupSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    member_count = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MessagingContactGroup
        fields = (
            "id",
            "name",
            "source",
            "source_display",
            "kavenegar_tag",
            "description",
            "is_active",
            "member_count",
            "created_by_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "source_display", "member_count", "created_by_name", "created_at", "updated_at")

    def get_member_count(self, obj):
        annotated = getattr(obj, "_member_count", None)
        return annotated if annotated is not None else obj.members.count()

    def get_created_by_name(self, obj):
        user = obj.created_by
        if not user:
            return ""
        return (user.get_full_name() or "").strip() or user.get_username()

    def validate_kavenegar_tag(self, value):
        value = str(value or "").strip()
        if value and not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", value):
            raise serializers.ValidationError("تگ کاوه‌نگار فقط می‌تواند شامل حروف انگلیسی، عدد، خط تیره و زیرخط باشد.")
        return value


class MessagingContactGroupDetailSerializer(MessagingContactGroupSerializer):
    members = MessagingContactGroupMemberSerializer(many=True, read_only=True)

    class Meta(MessagingContactGroupSerializer.Meta):
        fields = MessagingContactGroupSerializer.Meta.fields + ("members",)


class BaleUserBindingSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    user_display_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BaleUserBinding
        fields = (
            "id",
            "user",
            "username",
            "user_display_name",
            "bale_user_id",
            "display_name",
            "is_active",
            "verified_by_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "username",
            "user_display_name",
            "verified_by_name",
            "created_at",
            "updated_at",
        )

    def get_user_display_name(self, obj):
        return (obj.user.get_full_name() or "").strip() or obj.user.get_username()

    def get_verified_by_name(self, obj):
        user = obj.verified_by
        if not user:
            return ""
        return (user.get_full_name() or "").strip() or user.get_username()

    def validate_bale_user_id(self, value):
        normalized = str(value or "").strip()
        if not normalized or len(normalized) > 40 or not normalized.isascii() or not normalized.isdigit():
            raise serializers.ValidationError("شناسه کاربر بله معتبر نیست.")
        return normalized

    def validate_user(self, user):
        if not user.is_active:
            raise serializers.ValidationError("کاربر سایت غیرفعال است.")
        sections = effective_admin_sections(user)
        if sections != ALL and not ({"crm", "crm-funnel"} & sections):
            raise serializers.ValidationError("کاربر سایت دسترسی فعال CRM ندارد.")
        return user
