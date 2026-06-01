from django.urls import reverse
from rest_framework import serializers

from orders.models import Order
from sales.models import StoreOrder

from .models import OfflinePayment, OfflinePaymentAuditLog, OfflinePaymentReceipt
from .services import (
    bank_accounts,
    expire_if_due,
    initiate_marketplace_order_payment,
    initiate_store_order_payment,
    primary_bank_account,
    review_payment,
    unlock_payment,
    upload_receipt,
)


class BankAccountSerializer(serializers.Serializer):
    id = serializers.CharField()
    bank_name = serializers.CharField()
    iban = serializers.CharField()
    account_holder = serializers.CharField()
    is_primary = serializers.BooleanField()


class OfflinePaymentReceiptSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = OfflinePaymentReceipt
        fields = (
            "id",
            "reference_number",
            "note",
            "status",
            "admin_note",
            "reviewed_at",
            "created_at",
            "file_url",
        )

    def get_file_url(self, obj):
        request = self.context.get("request")
        url = reverse("offline-payment-receipt-file", kwargs={"pk": obj.payment_id})
        return request.build_absolute_uri(url) if request else url


class OfflinePaymentAuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor_user.username", read_only=True)

    class Meta:
        model = OfflinePaymentAuditLog
        fields = ("id", "action", "actor_username", "ip_address", "payload", "created_at")


class OfflinePaymentSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    source_type = serializers.CharField(read_only=True)
    source_id = serializers.CharField(read_only=True)
    source_title = serializers.SerializerMethodField()
    bank_account = serializers.SerializerMethodField()
    latest_receipt = serializers.SerializerMethodField()
    receipts = OfflinePaymentReceiptSerializer(many=True, read_only=True)
    audit_logs = OfflinePaymentAuditLogSerializer(many=True, read_only=True)
    can_upload = serializers.SerializerMethodField()

    class Meta:
        model = OfflinePayment
        fields = (
            "id",
            "source_type",
            "source_id",
            "source_title",
            "user_username",
            "amount",
            "currency",
            "status",
            "rejection_count",
            "admin_note",
            "payment_deadline",
            "target_iban_id",
            "bank_account",
            "latest_receipt",
            "receipts",
            "audit_logs",
            "can_upload",
            "reviewed_at",
            "created_at",
            "updated_at",
        )

    def get_source_title(self, obj):
        if obj.store_order_id:
            first_item = obj.store_order.items.first()
            return first_item.product_name if first_item else f"سفارش مستقیم {obj.store_order_id}"
        return obj.marketplace_order.title

    def get_bank_account(self, obj):
        account = next((row for row in bank_accounts() if row["id"] == obj.target_iban_id), None)
        return account or {"id": obj.target_iban_id, "bank_name": "", "iban": "", "account_holder": ""}

    def get_latest_receipt(self, obj):
        receipt = obj.receipts.first()
        return OfflinePaymentReceiptSerializer(receipt, context=self.context).data if receipt else None

    def get_can_upload(self, obj):
        expire_if_due(obj)
        return obj.status in {"pending_receipt", "rejected"}


class OfflinePaymentInitiateSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=["store_order", "marketplace_order"])
    source_id = serializers.UUIDField()

    def create(self, validated_data):
        request = self.context["request"]
        if validated_data["source_type"] == "store_order":
            try:
                order = StoreOrder.objects.get(pk=validated_data["source_id"])
            except StoreOrder.DoesNotExist as exc:
                raise serializers.ValidationError({"source_id": "سفارش مستقیم پیدا نشد."}) from exc
            return initiate_store_order_payment(order, request.user, request)
        try:
            order = Order.objects.get(pk=validated_data["source_id"])
        except Order.DoesNotExist as exc:
            raise serializers.ValidationError({"source_id": "سفارش بازار پیدا نشد."}) from exc
        return initiate_marketplace_order_payment(order, request.user, request)


class ReceiptUploadSerializer(serializers.Serializer):
    receipt_file = serializers.FileField()
    reference_number = serializers.CharField(max_length=30)
    note = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        return upload_receipt(
            self.context["payment"],
            self.context["request"].user,
            validated_data["receipt_file"],
            validated_data["reference_number"],
            validated_data.get("note", ""),
            self.context["request"],
        )


class ReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    admin_note = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        return review_payment(
            self.context["payment"],
            self.context["request"].user,
            validated_data["decision"],
            validated_data.get("admin_note", ""),
            self.context["request"],
        )


class UnlockSerializer(serializers.Serializer):
    admin_note = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        return unlock_payment(
            self.context["payment"],
            self.context["request"].user,
            validated_data.get("admin_note", ""),
            self.context["request"],
        )
