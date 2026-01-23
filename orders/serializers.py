from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.models import RoleCode
from accounts.services import user_has_role
from products.models import ProductCategory

from .models import Order, OrderOffer, OrderStatusHistory, OrderType

User = get_user_model()


class MoneyField(serializers.Field):
    def __init__(self, amount_field, currency_field, **kwargs):
        self.amount_field = amount_field
        self.currency_field = currency_field
        super().__init__(**kwargs)

    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        amount = getattr(instance, self.amount_field)
        currency = getattr(instance, self.currency_field)
        if amount is None:
            return None
        return {"amount": amount, "currency": currency}

    def to_internal_value(self, data):
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise serializers.ValidationError("Invalid money payload.")
        amount = data.get("amount")
        currency = data.get("currency", "IRR")
        if amount is None:
            raise serializers.ValidationError("Money amount is required.")
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            raise serializers.ValidationError("Money amount must be an integer.")
        return {
            self.amount_field: amount,
            self.currency_field: currency,
        }


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    actor_user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = ("from_status", "to_status", "event", "actor_user", "at", "meta")


class OrderReadSerializer(serializers.ModelSerializer):
    buyer = UserSummarySerializer(read_only=True)
    assigned_provider = UserSummarySerializer(read_only=True)
    product_type = serializers.PrimaryKeyRelatedField(read_only=True)
    price_agreed = MoneyField("price_agreed_amount", "price_agreed_currency", read_only=True)
    selected_offer_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "type",
            "status",
            "buyer",
            "assigned_provider",
            "title",
            "description",
            "product_type",
            "grade",
            "dimensions",
            "quantity",
            "quantity_unit",
            "approx_weight_kg",
            "origin",
            "destination",
            "origin_city",
            "destination_city",
            "deadline_at",
            "requested_at",
            "selected_offer_id",
            "price_agreed",
            "created_at",
            "updated_at",
        )


class OrderCreateSerializer(serializers.ModelSerializer):
    product_type = serializers.PrimaryKeyRelatedField(
        queryset=ProductCategory.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "type",
            "title",
            "description",
            "product_type",
            "grade",
            "dimensions",
            "quantity",
            "quantity_unit",
            "approx_weight_kg",
            "origin",
            "destination",
            "origin_city",
            "destination_city",
            "deadline_at",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        user = self.context["request"].user
        order_type = attrs.get("type")
        if order_type == OrderType.BUY:
            if not user_has_role(user, RoleCode.BUYER, require_active=True):
                raise serializers.ValidationError("Active BUYER role required.")
        elif order_type == OrderType.SELL:
            if not user_has_role(user, RoleCode.SELLER, require_active=True):
                raise serializers.ValidationError("Active SELLER role required.")
        else:
            raise serializers.ValidationError("Unsupported order type.")
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        order_type = validated_data.get("type")
        if order_type == OrderType.BUY:
            return Order.objects.create(buyer=user, **validated_data)
        if order_type == OrderType.SELL:
            return Order.objects.create(assigned_provider=user, **validated_data)
        return Order.objects.create(**validated_data)


class OrderOfferReadSerializer(serializers.ModelSerializer):
    offered_by = UserSummarySerializer(read_only=True)
    price_total = MoneyField("price_total_amount", "price_total_currency", read_only=True)
    price_unit = MoneyField("price_unit_amount", "price_unit_currency", read_only=True)

    class Meta:
        model = OrderOffer
        fields = (
            "id",
            "order_id",
            "offered_by",
            "price_total",
            "price_unit",
            "deposit_percent",
            "lead_time_days",
            "terms",
            "status",
            "created_at",
            "updated_at",
        )


class OrderOfferCreateSerializer(serializers.ModelSerializer):
    price_total = MoneyField("price_total_amount", "price_total_currency")
    price_unit = MoneyField("price_unit_amount", "price_unit_currency", required=False)

    class Meta:
        model = OrderOffer
        fields = (
            "id",
            "price_total",
            "price_unit",
            "deposit_percent",
            "lead_time_days",
            "terms",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        price_total = validated_data.pop("price_total", {})
        price_unit = validated_data.pop("price_unit", {})
        validated_data.update(price_total)
        if price_unit:
            validated_data.update(price_unit)
        return OrderOffer.objects.create(**validated_data)
