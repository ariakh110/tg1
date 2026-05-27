from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from accounts.models import RoleCode
from accounts.services import user_has_role
from products.models import Product

from .models import (
    StoreBuyerAddress,
    StoreBuyerInvoiceProfile,
    StoreOrder,
    StoreOrderItem,
    StoreOrderNotification,
    StoreQuoteConfirmationStatus,
    StoreOrderStatus,
    StoreOrderStatusHistory,
    StoreRiskStatus,
    StorePayment,
    StorePaymentStatus,
    StoreQuantityUnit,
)
from .services import (
    create_store_order,
    confirm_store_order_quote,
    generate_payment_link,
    is_order_price_expired,
    is_order_payment_overdue,
    paid_amount_for_order,
    risk_blockers_for_order,
    record_final_weights,
    reject_store_order_quote,
    remaining_amount_for_order,
    send_payment_link,
    submit_admin_quote,
    set_order_status,
    validate_order_transition,
)


def request_user_is_admin(request):
    user = getattr(request, "user", None)
    return user_has_role(user, RoleCode.ADMIN, require_active=True)


class StoreBuyerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreBuyerAddress
        fields = (
            "id",
            "title",
            "province",
            "city",
            "address",
            "phone",
            "is_default",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        required = ("province", "city", "address")
        for field in required:
            value = attrs.get(field, getattr(self.instance, field, ""))
            if not str(value or "").strip():
                raise serializers.ValidationError({field: "این فیلد الزامی است."})
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        if validated_data.get("is_default"):
            StoreBuyerAddress.objects.filter(buyer=user, is_default=True).update(is_default=False)
        return StoreBuyerAddress.objects.create(buyer=user, **validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("is_default"):
            StoreBuyerAddress.objects.filter(buyer=instance.buyer, is_default=True).exclude(pk=instance.pk).update(is_default=False)
        return super().update(instance, validated_data)


class StoreBuyerInvoiceProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreBuyerInvoiceProfile
        fields = (
            "id",
            "title",
            "buyer_type",
            "full_name",
            "national_id",
            "company_name",
            "economic_code",
            "registration_id",
            "phone",
            "postal_code",
            "address",
            "is_default",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        buyer_type = attrs.get("buyer_type", getattr(self.instance, "buyer_type", StoreBuyerInvoiceProfile.BUYER_TYPE_INDIVIDUAL))
        if buyer_type == StoreBuyerInvoiceProfile.BUYER_TYPE_COMPANY:
            for field in ("company_name", "economic_code"):
                value = attrs.get(field, getattr(self.instance, field, ""))
                if not str(value or "").strip():
                    raise serializers.ValidationError({field: "این فیلد برای فاکتور حقوقی الزامی است."})
        else:
            for field in ("full_name", "national_id"):
                value = attrs.get(field, getattr(self.instance, field, ""))
                if not str(value or "").strip():
                    raise serializers.ValidationError({field: "این فیلد برای فاکتور حقیقی الزامی است."})
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        if validated_data.get("is_default"):
            StoreBuyerInvoiceProfile.objects.filter(buyer=user, is_default=True).update(is_default=False)
        return StoreBuyerInvoiceProfile.objects.create(buyer=user, **validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("is_default"):
            StoreBuyerInvoiceProfile.objects.filter(buyer=instance.buyer, is_default=True).exclude(pk=instance.pk).update(is_default=False)
        return super().update(instance, validated_data)


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
            "price_basis",
            "selected_condition_label",
            "total_price_amount",
            "final_price_amount",
            "weight_adjustment_amount",
            "currency",
            "product_snapshot",
            "specification_snapshot",
            "delivery_snapshot",
            "selection_details",
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
    is_price_expired = serializers.SerializerMethodField()
    risk_blockers = serializers.SerializerMethodField()
    admin_notes = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()

    def get_is_payment_overdue(self, obj):
        return is_order_payment_overdue(obj)

    def get_is_price_expired(self, obj):
        return is_order_price_expired(obj)

    def get_risk_blockers(self, obj):
        return risk_blockers_for_order(obj)

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
            "risk_status",
            "contact_name",
            "contact_phone",
            "destination_province",
            "destination_city",
            "destination_address",
            "delivery_notes",
            "driver_name",
            "driver_phone",
            "vehicle_type",
            "vehicle_plate",
            "logistics_note",
            "subtotal_amount",
            "total_amount",
            "settlement_term_days",
            "settlement_term_fee_amount",
            "weight_adjustment_amount",
            "paid_amount",
            "remaining_amount",
            "currency",
            "price_valid_until",
            "source_price_checked_at",
            "market_price_checked_at",
            "stock_verified_at",
            "proforma_confirmed_at",
            "loading_permission_at",
            "payment_due_at",
            "payment_link_url",
            "payment_link_created_at",
            "payment_link_sent_at",
            "payment_link_sent_to",
            "quote_confirmation_status",
            "quote_rejection_reason",
            "quote_rejection_note",
            "quote_confirmed_at",
            "quote_rejected_at",
            "is_payment_overdue",
            "is_price_expired",
            "risk_blockers",
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request_user_is_admin(request):
            return data
        if instance.quote_confirmation_status != StoreQuoteConfirmationStatus.AWAITING_BUYER:
            return data

        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        quote = metadata.get("quote") if isinstance(metadata.get("quote"), dict) else {}
        loading_points = quote.get("loading_points") if isinstance(quote.get("loading_points"), list) else []
        masked_points = []
        for point in loading_points:
            masked_points.append(
                {
                    "item_id": point.get("item_id"),
                    "freight_amount": point.get("freight_amount", 0),
                    "source_hidden": True,
                    "label": "مبدا بار پس از تایید فاکتور اعلام می‌شود.",
                }
            )
        if quote:
            quote["source_hidden"] = True
            quote["loading_points"] = masked_points
            metadata["quote"] = quote
            data["metadata"] = metadata

        for item in data.get("items") or []:
            delivery = item.get("delivery_snapshot")
            if isinstance(delivery, dict):
                item["delivery_snapshot"] = {
                    "source_hidden": True,
                    "label": "مبدا بار پس از تایید فاکتور اعلام می‌شود.",
                }
            details = item.get("selection_details")
            if isinstance(details, dict) and isinstance(details.get("quote_loading_point"), dict):
                details["quote_loading_point"] = {
                    "item_id": details["quote_loading_point"].get("item_id"),
                    "source_hidden": True,
                    "label": "مبدا بار پس از تایید فاکتور اعلام می‌شود.",
                }
        return data


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
    selection_details = serializers.JSONField(required=False)

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Product is inactive or does not exist.")
        return value

    def validate(self, attrs):
        quantity_unit = attrs.get("quantity_unit") or StoreQuantityUnit.TON
        quantity = attrs.get("quantity")
        if quantity_unit == StoreQuantityUnit.SHEET and (
            quantity is None or quantity < Decimal("1") or quantity != quantity.to_integral_value()
        ):
            raise serializers.ValidationError({"quantity": "Sheet count must be a whole number greater than or equal to 1."})
        return attrs


class StoreOrderCreateSerializer(serializers.ModelSerializer):
    items = StoreOrderCreateItemSerializer(many=True)
    settlement_term_days = serializers.IntegerField(required=False, min_value=1, max_value=7, default=1)
    destination_profile_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    invoice_profile_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    destination_profile = serializers.JSONField(required=False, write_only=True)
    invoice_profile = serializers.JSONField(required=False, write_only=True)
    save_destination_profile = serializers.BooleanField(required=False, default=False, write_only=True)
    save_invoice_profile = serializers.BooleanField(required=False, default=False, write_only=True)

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
            "destination_profile_id",
            "invoice_profile_id",
            "destination_profile",
            "invoice_profile",
            "save_destination_profile",
            "save_invoice_profile",
            "items",
        )
        read_only_fields = ("id",)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        destination_profile_id = validated_data.pop("destination_profile_id", None)
        invoice_profile_id = validated_data.pop("invoice_profile_id", None)
        destination_payload = validated_data.pop("destination_profile", None) or {}
        invoice_payload = validated_data.pop("invoice_profile", None) or {}
        save_destination = validated_data.pop("save_destination_profile", False)
        save_invoice = validated_data.pop("save_invoice_profile", False)

        metadata = dict(validated_data.get("metadata") or {})

        if destination_profile_id:
            try:
                address = StoreBuyerAddress.objects.get(pk=destination_profile_id, buyer=user)
            except StoreBuyerAddress.DoesNotExist as exc:
                raise serializers.ValidationError({"destination_profile_id": "مقصد انتخاب‌شده پیدا نشد."}) from exc
            destination_payload = {
                "id": address.id,
                "title": address.title,
                "province": address.province,
                "city": address.city,
                "address": address.address,
                "phone": address.phone,
            }
        elif destination_payload:
            destination_serializer = StoreBuyerAddressSerializer(
                data={
                    "title": destination_payload.get("title", ""),
                    "province": destination_payload.get("province", ""),
                    "city": destination_payload.get("city", ""),
                    "address": destination_payload.get("address", ""),
                    "phone": destination_payload.get("phone", ""),
                    "is_default": bool(destination_payload.get("is_default", False)),
                },
                context=self.context,
            )
            destination_serializer.is_valid(raise_exception=True)
            if save_destination:
                address = destination_serializer.save()
                destination_payload["id"] = address.id
            else:
                destination_payload = destination_serializer.validated_data

        if invoice_profile_id:
            try:
                profile = StoreBuyerInvoiceProfile.objects.get(pk=invoice_profile_id, buyer=user)
            except StoreBuyerInvoiceProfile.DoesNotExist as exc:
                raise serializers.ValidationError({"invoice_profile_id": "پروفایل فاکتور انتخاب‌شده پیدا نشد."}) from exc
            invoice_payload = StoreBuyerInvoiceProfileSerializer(profile).data
        elif invoice_payload:
            invoice_serializer = StoreBuyerInvoiceProfileSerializer(
                data={
                    "title": invoice_payload.get("title", ""),
                    "buyer_type": invoice_payload.get("buyer_type", StoreBuyerInvoiceProfile.BUYER_TYPE_INDIVIDUAL),
                    "full_name": invoice_payload.get("full_name", ""),
                    "national_id": invoice_payload.get("national_id", ""),
                    "company_name": invoice_payload.get("company_name", ""),
                    "economic_code": invoice_payload.get("economic_code", ""),
                    "registration_id": invoice_payload.get("registration_id", ""),
                    "phone": invoice_payload.get("phone", ""),
                    "postal_code": invoice_payload.get("postal_code", ""),
                    "address": invoice_payload.get("address", ""),
                    "is_default": bool(invoice_payload.get("is_default", False)),
                },
                context=self.context,
            )
            invoice_serializer.is_valid(raise_exception=True)
            if save_invoice:
                profile = invoice_serializer.save()
                invoice_payload = StoreBuyerInvoiceProfileSerializer(profile).data
            else:
                invoice_payload = invoice_serializer.validated_data

        if destination_payload:
            validated_data["destination_province"] = destination_payload.get("province", "")
            validated_data["destination_city"] = destination_payload.get("city", "")
            validated_data["destination_address"] = destination_payload.get("address", "")
            if destination_payload.get("phone") and not validated_data.get("contact_phone"):
                validated_data["contact_phone"] = destination_payload.get("phone", "")
            metadata["destination_profile"] = dict(destination_payload)

        if invoice_payload:
            metadata["invoice_profile"] = dict(invoice_payload)

        validated_data["metadata"] = metadata
        try:
            return create_store_order(user, validated_data)
        except ValueError as exc:
            raise serializers.ValidationError({"items": str(exc)})


class StoreOrderTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=StoreOrderStatus.choices)
    event = serializers.CharField(required=False, allow_blank=True)
    meta = serializers.JSONField(required=False)

    def validate_status(self, value):
        order = self.context["order"]
        try:
            validate_order_transition(order, value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))
        return value

    def save(self, **kwargs):
        order = self.context["order"]
        actor = self.context["request"].user
        to_status = self.validated_data["status"]
        event = self.validated_data.get("event") or f"STORE_ORDER_{to_status}"
        meta = self.validated_data.get("meta") or {}
        return set_order_status(order, to_status, event, actor, meta=meta)


class StoreAdminQuoteItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    unit_price_amount = serializers.IntegerField(min_value=0)
    price_basis = serializers.ChoiceField(choices=("kg", "ton", "sheet"), required=False, default="kg")
    estimated_weight_kg = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"), required=False)
    total_price_amount = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    force_total_price = serializers.BooleanField(required=False, default=False)


class StoreAdminQuoteSerializer(serializers.Serializer):
    items = StoreAdminQuoteItemSerializer(many=True)
    price_valid_until = serializers.DateTimeField(required=False, allow_null=True)
    payment_due_at = serializers.DateTimeField(required=False, allow_null=True)
    loading_points = serializers.ListField(child=serializers.DictField(), required=False, allow_empty=True)
    multi_loading = serializers.BooleanField(required=False, default=False)
    freight_amount = serializers.IntegerField(required=False, min_value=0, default=0)
    freight_note = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one quote item is required.")
        return value

    def save(self, **kwargs):
        order = self.context["order"]
        request = self.context["request"]
        return submit_admin_quote(
            order,
            self.validated_data["items"],
            actor=request.user,
            price_valid_until=self.validated_data.get("price_valid_until"),
            payment_due_at=self.validated_data.get("payment_due_at"),
            loading_points=self.validated_data.get("loading_points") or [],
            multi_loading=self.validated_data.get("multi_loading", False),
            freight_amount=self.validated_data.get("freight_amount") or 0,
            freight_note=self.validated_data.get("freight_note", ""),
        )


class StoreQuoteConfirmSerializer(serializers.Serializer):
    def save(self, **kwargs):
        order = self.context["order"]
        request = self.context["request"]
        return confirm_store_order_quote(order, actor=request.user)


class StoreQuoteRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=120)
    note = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not (attrs.get("reason") or "").strip() and not (attrs.get("note") or "").strip():
            raise serializers.ValidationError({"reason": "Rejection reason or note is required."})
        return attrs

    def save(self, **kwargs):
        order = self.context["order"]
        request = self.context["request"]
        return reject_store_order_quote(
            order,
            self.validated_data.get("reason", ""),
            actor=request.user,
            note=self.validated_data.get("note", ""),
        )


class StoreOrderAdminUpdateSerializer(serializers.ModelSerializer):
    source_price_checked = serializers.BooleanField(required=False, write_only=True)
    market_price_checked = serializers.BooleanField(required=False, write_only=True)
    stock_verified = serializers.BooleanField(required=False, write_only=True)
    proforma_confirmed = serializers.BooleanField(required=False, write_only=True)
    loading_permission = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = StoreOrder
        fields = (
            "contact_name",
            "contact_phone",
            "destination_province",
            "destination_city",
            "destination_address",
            "delivery_notes",
            "driver_name",
            "driver_phone",
            "vehicle_type",
            "vehicle_plate",
            "logistics_note",
            "risk_status",
            "subtotal_amount",
            "total_amount",
            "settlement_term_days",
            "settlement_term_fee_amount",
            "weight_adjustment_amount",
            "price_valid_until",
            "source_price_checked_at",
            "market_price_checked_at",
            "stock_verified_at",
            "proforma_confirmed_at",
            "loading_permission_at",
            "payment_due_at",
            "admin_notes",
            "metadata",
            "source_price_checked",
            "market_price_checked",
            "stock_verified",
            "proforma_confirmed",
            "loading_permission",
        )

    def update(self, instance, validated_data):
        before = {
            "total_amount": instance.total_amount,
            "payment_due_at": instance.payment_due_at.isoformat() if instance.payment_due_at else None,
            "status": instance.status,
            "risk_status": instance.risk_status,
        }
        now = timezone.now()
        checkbox_map = {
            "source_price_checked": "source_price_checked_at",
            "market_price_checked": "market_price_checked_at",
            "stock_verified": "stock_verified_at",
            "proforma_confirmed": "proforma_confirmed_at",
            "loading_permission": "loading_permission_at",
        }
        for checkbox, field in checkbox_map.items():
            if checkbox in validated_data:
                validated_data[field] = now if validated_data.pop(checkbox) else None
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

    def validate(self, attrs):
        order = self.context["order"]
        if is_order_price_expired(order):
            raise serializers.ValidationError({"detail": "price_validity_expired"})
        return attrs

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
