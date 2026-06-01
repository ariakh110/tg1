import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.db.models import Q


class OfflinePaymentStatus(models.TextChoices):
    PENDING_RECEIPT = "pending_receipt", "در انتظار بارگذاری فیش"
    PENDING_REVIEW = "pending_review", "در انتظار بررسی"
    APPROVED = "approved", "تایید شده"
    REJECTED = "rejected", "رد شده"
    EXPIRED = "expired", "منقضی شده"
    LOCKED = "locked", "قفل شده"


class ReceiptAttemptStatus(models.TextChoices):
    PENDING = "pending", "در انتظار بررسی"
    APPROVED = "approved", "تایید شده"
    REJECTED = "rejected", "رد شده"


class NotificationStatus(models.TextChoices):
    SENT = "sent", "ارسال شده"
    FAILED = "failed", "ناموفق"
    SKIPPED = "skipped", "ارسال نشده"


def receipt_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"receipts/{instance.payment.created_at:%Y/%m}/{uuid.uuid4().hex}{extension}"


class OfflinePayment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_order = models.ForeignKey(
        "sales.StoreOrder",
        on_delete=models.CASCADE,
        related_name="offline_payments",
        null=True,
        blank=True,
    )
    marketplace_order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="offline_payments",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="offline_payments",
    )
    amount = models.BigIntegerField()
    currency = models.CharField(max_length=10, default="IRR")
    status = models.CharField(
        max_length=24,
        choices=OfflinePaymentStatus.choices,
        default=OfflinePaymentStatus.PENDING_RECEIPT,
        db_index=True,
    )
    rejection_count = models.PositiveSmallIntegerField(default=0)
    admin_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_offline_payments",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    payment_deadline = models.DateTimeField(db_index=True)
    target_iban_id = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(store_order__isnull=False, marketplace_order__isnull=True)
                    | Q(store_order__isnull=True, marketplace_order__isnull=False)
                ),
                name="offline_payment_exactly_one_source",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "status", "created_at"]),
            models.Index(fields=["status", "payment_deadline"]),
        ]

    @property
    def source_type(self):
        return "store_order" if self.store_order_id else "marketplace_order"

    @property
    def source_id(self):
        return self.store_order_id or self.marketplace_order_id


class OfflinePaymentReceipt(models.Model):
    payment = models.ForeignKey(OfflinePayment, on_delete=models.CASCADE, related_name="receipts")
    file = models.FileField(upload_to=receipt_upload_path)
    reference_number = models.CharField(max_length=30)
    note = models.TextField(blank=True)
    status = models.CharField(
        max_length=16,
        choices=ReceiptAttemptStatus.choices,
        default=ReceiptAttemptStatus.PENDING,
    )
    admin_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_offline_payment_receipts",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)


class OfflinePaymentAuditLog(models.Model):
    payment = models.ForeignKey(OfflinePayment, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=64)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)


class OfflinePaymentNotification(models.Model):
    payment = models.ForeignKey(OfflinePayment, on_delete=models.CASCADE, related_name="notifications")
    event = models.CharField(max_length=64)
    recipient = models.EmailField(blank=True)
    status = models.CharField(max_length=16, choices=NotificationStatus.choices)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
