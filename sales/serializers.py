from decimal import Decimal

from rest_framework import serializers

from accounts.models import RoleCode
from accounts.services import user_has_role
from products.models import Product

from .models import (
    StoreOrder,
    StoreOrderItem,
    StoreOrderNotification,
    StoreOrderStatus,
    StoreOrderStatusHistory,
    StorePayment,
    StorePaymentStatus,
    StoreQuantityUnit,
)
from .services import (
    create_store_order,
    generate_payment_link,
    is_order_payment_overdue,
    paid_amount_for_order,
    record_final_weights,
    remaining_amount_for_order,
    send_payment_link,
    set_order_status,
)


def request_user_is_admin(request):
    user = getattr(request, "user", None)
    return user_has_role(user, RoleCode.ADMIN, require_active=True)


class StoreOrderItemReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreOrderItem
        fields = (
            "id",
            "product",
            "offer",
            "pricing_tier",
            "product_name",
            "seller_name",
            "quantity",
            "quantity_unit",
            "estimated_weight_kg",
            "price_weight_kg",
            "final_weight_kg",
            "unit_price_amount",
            "total_price_amount",
            "final_price_amount",
            "weight_adjustment_amount",
            "currency",
            "product_snapshot",
            "specification_snapshot",
            "delivery_snapshot",
            "created_at",
        )


class StoreOrderStatusHistorySerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor_user.username", read_only=True)

    class Meta:
        model = StoreOrderStatusHistory
        fields = ("from_status", "to_status", "event", "actor_user", "actor_username", "meta", "at")


class StorePaymentSerializer(serializers.ModelSerializer):
    order = serializers.UUIDField(source="order_id", read_only=True)
    order_status = serializers.CharField(source="order.status", read_only=True)
    order_title = serializers.SerializerMethodField()

    def get_order_title(self, obj):
        item = obj.order.items.first()
        return item.product_name if item else str(obj.order_id)

    class Meta:
        model = StorePayment
        fields = (
            "id",
            "order",
            "order_status",
            "order_title",
            "amount",
            "currency",
            "status",
            "provider",
            "provider_reference",
            "raw_payload",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class StoreOrderNotificationSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor_user.username", read_only=True)

    class Meta:
        model = StoreOrderNotification
        fields = (
            "id",
            "channel",
            "recipient",
            "event",
            "status",
            "actor_user",
            "actor_username",
            "payload",
            "error_message",
            "created_at",
        )
        read_only_fields = fields


class StoreOrderReadSerializer(serializers.ModelSerializer):
    buyer_username = serializers.CharField(source="buyer.username", read_only=True)
    items = StoreOrderItemReadSerializer(many=True, read_only=True)
    status_history = StoreOrderStatusHistorySerializer(many=True, read_only=True)
    payments = StorePaymentSerializer(many=True, read_only=True)
    notifications = StoreOrderNotificationSerializer(many=True, read_only=True)
    is_payment_overdue = serializers.SerializerMethodField()
    admin_notes = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()

    def get_is_payment_overdue(self, obj):
        return is_order_payment_overdue(obj)

    def get_admin_notes(self, obj):
        request = self.context.get("request")
        if request_user_is_admin(request):
            return obj.admin_notes
        return ""

    def get_paid_amount(self, obj):
        return paid_amount_for_order(obj)

    def get_remaining_amount(self, obj):
        return remaining_amount_for_order(obj)

    class Meta:
        model = StoreOrder
        fields = (
            "id",
            "buyer",
            "buyer_username",
            "status",
            "payment_status",
            "contact_name",
            "contact_phone",
            "destination_province",
            "destination_city",
            "destination_address",
            "delivery_notes",
            "subtotal_amount",
            "total_amount",
            "settlement_term_days",
            "settlement_term_fee_amount",
            "weight_adjustment_amount",
            "paid_amount",
            "remaining_amount",
            "currency",
            "payment_due_at",
            "payment_link_url",
            "payment_link_created_at",
            "payment_link_sent_at",
            "payment_link_sent_to",
            "is_payment_overdue",
            "admin_notes",
            "metadata",
            "submitted_at",
            "created_at",
            "updated_at",
            "items",
            "status_history",
            "payments",
            "notifications",
        )
        read_only_fields = fields


class StoreOrderCreateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    offer_id = serializers.IntegerField(required=False, allow_null=True)
    pricing_tier_id = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    quantity_unit = serializers.ChoiceField(
        choices=StoreQuantityUnit.choices,
        required=False,
        allow_blank=True,
        default=StoreQuantityUnit.TON,
    )

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Product is inactive or does not exist.")
        return value


class StoreOrderCreateSerializer(serializers.ModelSerializer):
    items = StoreOrderCreateItemSerializer(many=True)
    settlement_term_days = serializers.IntegerField(required=False, min_value=1, max_value=7, default=1)

    class Meta:
        model = StoreOrder
        fields = (
            "id",
            "contact_name",
            "contact_phone",
            "destination_province",
            "destination_city",
            "destination_address",
            "delivery_notes",
            "settlement_term_days",
            "metadata",
            "items",
        )
        read_only_fields = ("id",)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        return create_store_order(user, validated_data)


class StoreOrderTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=StoreOrderStatus.choices)
    event = serializers.CharField(required=False, allow_blank=True)
    meta = serializers.JSONField(required=False)

    def save(self, **kwargs):
        order = self.context["order"]
        actor = self.context["request"].user
        to_status = self.validated_data["status"]
        event = self.validated_data.get("event") or f"STORE_ORDER_{to_status}"
        meta = self.validated_data.get("meta") or {}
        return set_order_status(order, to_status, event, actor, meta=meta)


class StoreOrderAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreOrder
        fields = (
            "contact_name",
            "contact_phone",
            "destination_province",
            "destination_city",
            "destination_address",
            "delivery_notes",
            "subtotal_amount",
            "total_amount",
            "settlement_term_days",
            "settlement_term_fee_amount",
            "weight_adjustment_amount",
            "payment_due_at",
            "admin_notes",
            "metadata",
        )

    def update(self, instance, validated_data):
        before = {
            "total_amount": instance.total_amount,
            "payment_due_at": instance.payment_due_at.isoformat() if instance.payment_due_at else None,
            "status": instance.status,
        }
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save(update_fields=[*validated_data.keys(), "updated_at"])
        request = self.context["request"]
        StoreOrderStatusHistory.objects.create(
            order=instance,
            from_status=instance.status,
            to_status=instance.status,
            event="STORE_ORDER_ADMIN_UPDATED",
            actor_user=request.user,
            meta={"before": before, "updated_fields": sorted(validated_data.keys())},
        )
        return instance


class StorePaymentLinkSerializer(serializers.Serializer):
    payment_due_at = serializers.DateTimeField(required=False, allow_null=True)

    def save(self, **kwargs):
        order = self.context["order"]
        request = self.context["request"]
        return generate_payment_link(
            order,
            actor=request.user,
            due_at=self.validated_data.get("payment_due_at"),
        )


class StorePaymentLinkSendSerializer(serializers.Serializer):
    recipient = serializers.CharField(required=False, allow_blank=True)
    payment_due_at = serializers.DateTimeField(required=False, allow_null=True)

    def save(self, **kwargs):
        order = self.context["order"]
        request = self.context["request"]
        return send_payment_link(
            order,
            actor=request.user,
            recipient=self.validated_data.get("recipient"),
            due_at=self.validated_data.get("payment_due_at"),
        )


class StoreFinalWeightItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    final_weight_kg = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))


class StoreFinalWeightSerializer(serializers.Serializer):
    items = StoreFinalWeightItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value

    def save(self, **kwargs):
        order = self.context["order"]
        request = self.context["request"]
        return record_final_weights(order, self.validated_data["items"], actor=request.user)


class StorePaymentConfirmSerializer(serializers.Serializer):
    amount = serializers.IntegerField(required=False, min_value=0)
    provider = serializers.CharField(required=False, allow_blank=True)
    provider_reference = serializers.CharField(required=False, allow_blank=True)
    raw_payload = serializers.JSONField(required=False)

    def save(self, **kwargs):
        order = self.context["order"]
        actor = self.context["request"].user
        amount = self.validated_data.get("amount") or remaining_amount_for_order(order) or order.total_amount
        payment = StorePayment.objects.create(
            order=order,
            amount=amount,
            currency=order.currency,
            status=StorePaymentStatus.PAID,
            provider=self.validated_data.get("provider", "manual"),
            provider_reference=self.validated_data.get("provider_reference") or None,
            raw_payload=self.validated_data.get("raw_payload") or {},
        )
        if remaining_amount_for_order(order) <= 0:
            order.payment_status = StorePaymentStatus.PAID
            order.save(update_fields=["payment_status", "updated_at"])
            set_order_status(
                order,
                StoreOrderStatus.PAID,
                "STORE_ORDER_PAYMENT_CONFIRMED",
                actor,
                meta={"payment_id": payment.id, "amount": amount},
            )
        else:
            order.payment_status = StorePaymentStatus.PENDING
            order.save(update_fields=["payment_status", "updated_at"])
            StoreOrderStatusHistory.objects.create(
                order=order,
                from_status=order.status,
                to_status=order.status,
                event="STORE_ORDER_PARTIAL_PAYMENT_CONFIRMED",
                actor_user=actor,
                meta={"payment_id": payment.id, "amount": amount, "remaining_amount": remaining_amount_for_order(order)},
            )
        return payment
