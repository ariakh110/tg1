import uuid

from django.conf import settings
from django.db import models


class StoreOrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    QUOTE_REQUESTED = "QUOTE_REQUESTED", "Quote requested"
    PRICE_CONFIRMED = "PRICE_CONFIRMED", "Price confirmed"
    PAYMENT_PENDING = "PAYMENT_PENDING", "Payment pending"
    PAID = "PAID", "Paid"
    FULFILLMENT_PENDING = "FULFILLMENT_PENDING", "Fulfillment pending"
    READY_FOR_PICKUP = "READY_FOR_PICKUP", "Ready for pickup"
    SHIPPED = "SHIPPED", "Shipped"
    DELIVERED = "DELIVERED", "Delivered"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class StorePaymentStatus(models.TextChoices):
    UNPAID = "UNPAID", "Unpaid"
    PENDING = "PENDING", "Pending"
    PAID = "PAID", "Paid"
    FAILED = "FAILED", "Failed"
    REFUNDED = "REFUNDED", "Refunded"


class StoreRiskStatus(models.TextChoices):
    PENDING = "PENDING", "Pending review"
    APPROVED = "APPROVED", "Approved"
    BLOCKED = "BLOCKED", "Blocked"


class StoreQuoteConfirmationStatus(models.TextChoices):
    NOT_REQUIRED = "NOT_REQUIRED", "Not required"
    AWAITING_ADMIN_QUOTE = "AWAITING_ADMIN_QUOTE", "Awaiting admin quote"
    AWAITING_BUYER = "AWAITING_BUYER", "Awaiting buyer confirmation"
    CONFIRMED = "CONFIRMED", "Confirmed"
    REJECTED = "REJECTED", "Rejected"


class StoreNotificationChannel(models.TextChoices):
    SMS = "SMS", "SMS"
    MANUAL = "MANUAL", "Manual"


class StoreNotificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


class StoreQuantityUnit(models.TextChoices):
    TON = "ton", "Ton"
    KG = "kg", "Kilogram"
    SHEET = "sheet", "Sheet count"


class StoreOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="store_orders",
    )
    status = models.CharField(
        max_length=32,
        choices=StoreOrderStatus.choices,
        default=StoreOrderStatus.DRAFT,
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=StorePaymentStatus.choices,
        default=StorePaymentStatus.UNPAID,
        db_index=True,
    )
    risk_status = models.CharField(
        max_length=20,
        choices=StoreRiskStatus.choices,
        default=StoreRiskStatus.PENDING,
        db_index=True,
    )
    contact_name = models.CharField(max_length=160, blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    destination_province = models.CharField(max_length=100, blank=True)
    destination_city = models.CharField(max_length=100, blank=True)
    destination_address = models.TextField(blank=True)
    delivery_notes = models.TextField(blank=True)
    subtotal_amount = models.BigIntegerField(default=0)
    total_amount = models.BigIntegerField(default=0)
    settlement_term_days = models.PositiveSmallIntegerField(default=1)
    settlement_term_fee_amount = models.BigIntegerField(default=0)
    weight_adjustment_amount = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=10, default="IRR")
    price_valid_until = models.DateTimeField(null=True, blank=True, db_index=True)
    source_price_checked_at = models.DateTimeField(null=True, blank=True)
    market_price_checked_at = models.DateTimeField(null=True, blank=True)
    stock_verified_at = models.DateTimeField(null=True, blank=True)
    proforma_confirmed_at = models.DateTimeField(null=True, blank=True)
    loading_permission_at = models.DateTimeField(null=True, blank=True)
    payment_due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    payment_link_token = models.CharField(max_length=96, blank=True, db_index=True)
    payment_link_url = models.URLField(max_length=500, blank=True)
    payment_link_created_at = models.DateTimeField(null=True, blank=True)
    payment_link_sent_at = models.DateTimeField(null=True, blank=True)
    payment_link_sent_to = models.CharField(max_length=80, blank=True)
    quote_confirmation_status = models.CharField(
        max_length=32,
        choices=StoreQuoteConfirmationStatus.choices,
        default=StoreQuoteConfirmationStatus.NOT_REQUIRED,
        db_index=True,
    )
    quote_rejection_reason = models.CharField(max_length=120, blank=True)
    quote_rejection_note = models.TextField(blank=True)
    quote_confirmed_at = models.DateTimeField(null=True, blank=True)
    quote_rejected_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["buyer", "status", "created_at"]),
            models.Index(fields=["payment_status", "created_at"]),
        ]

    def __str__(self):
        return f"StoreOrder({self.id}) {self.status}"


class StoreOrderItem(models.Model):
    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="store_order_items",
    )
    offer = models.ForeignKey(
        "products.Offer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="store_order_items",
    )
    pricing_tier = models.ForeignKey(
        "products.PricingTier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="store_order_items",
    )
    product_name = models.CharField(max_length=255)
    seller_name = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    quantity_unit = models.CharField(max_length=20, choices=StoreQuantityUnit.choices, default=StoreQuantityUnit.TON)
    estimated_weight_kg = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    price_weight_kg = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    final_weight_kg = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    unit_price_amount = models.BigIntegerField(null=True, blank=True)
    price_basis = models.CharField(max_length=20, blank=True, default="ton")
    selected_condition_label = models.CharField(max_length=160, blank=True, default="")
    total_price_amount = models.BigIntegerField(null=True, blank=True)
    final_price_amount = models.BigIntegerField(null=True, blank=True)
    weight_adjustment_amount = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=10, default="IRR")
    product_snapshot = models.JSONField(default=dict, blank=True)
    specification_snapshot = models.JSONField(default=dict, blank=True)
    delivery_snapshot = models.JSONField(default=dict, blank=True)
    selection_details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class StoreOrderStatusHistory(models.Model):
    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=32, null=True, blank=True)
    to_status = models.CharField(max_length=32)
    event = models.CharField(max_length=64)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    meta = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-at",)

    def __str__(self):
        return f"{self.order_id} {self.from_status}->{self.to_status}"


class StorePayment(models.Model):
    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name="payments")
    amount = models.BigIntegerField()
    currency = models.CharField(max_length=10, default="IRR")
    status = models.CharField(
        max_length=20,
        choices=StorePaymentStatus.choices,
        default=StorePaymentStatus.PENDING,
        db_index=True,
    )
    provider = models.CharField(max_length=80, blank=True)
    provider_reference = models.CharField(max_length=160, null=True, blank=True, unique=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"StorePayment({self.order_id}) {self.status}"


class StoreOrderNotification(models.Model):
    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(
        max_length=20,
        choices=StoreNotificationChannel.choices,
        default=StoreNotificationChannel.SMS,
    )
    recipient = models.CharField(max_length=120, blank=True)
    event = models.CharField(max_length=80)
    status = models.CharField(
        max_length=20,
        choices=StoreNotificationStatus.choices,
        default=StoreNotificationStatus.PENDING,
        db_index=True,
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.order_id} {self.channel} {self.status}"
