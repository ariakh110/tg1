import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from products.models import ProductCategory


class OrderType(models.TextChoices):
    BUY = "BUY", "BUY"
    SELL = "SELL", "SELL"


class OrderStatus(models.TextChoices):
    OPEN = "OPEN", "OPEN"
    OFFER_SELECTED = "OFFER_SELECTED", "OFFER_SELECTED"
    DEPOSIT_PENDING = "DEPOSIT_PENDING", "DEPOSIT_PENDING"
    DEPOSIT_PAID = "DEPOSIT_PAID", "DEPOSIT_PAID"
    PROVIDER_CONFIRMED = "PROVIDER_CONFIRMED", "PROVIDER_CONFIRMED"
    PAYMENT_IN_PROGRESS = "PAYMENT_IN_PROGRESS", "PAYMENT_IN_PROGRESS"
    READY_FOR_PICKUP = "READY_FOR_PICKUP", "READY_FOR_PICKUP"
    LOADING = "LOADING", "LOADING"
    LOADED_AWAITING_WEIGHT = "LOADED_AWAITING_WEIGHT", "LOADED_AWAITING_WEIGHT"
    AWAITING_FINAL_PAYMENT = "AWAITING_FINAL_PAYMENT", "AWAITING_FINAL_PAYMENT"
    READY_FOR_DELIVERY = "READY_FOR_DELIVERY", "READY_FOR_DELIVERY"
    IN_TRANSIT = "IN_TRANSIT", "IN_TRANSIT"
    DELIVERED = "DELIVERED", "DELIVERED"
    COMPLETED = "COMPLETED", "COMPLETED"
    CANCELLED = "CANCELLED", "CANCELLED"


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=10, choices=OrderType.choices)
    status = models.CharField(max_length=32, choices=OrderStatus.choices, default=OrderStatus.OPEN)

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="buyer_orders",
    )
    assigned_provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="provider_orders",
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    product_type = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    dimensions = models.CharField(max_length=100, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quantity_unit = models.CharField(max_length=20, blank=True)
    approx_weight_kg = models.IntegerField(null=True, blank=True)

    origin = models.JSONField(null=True, blank=True)
    destination = models.JSONField(null=True, blank=True)
    origin_city = models.CharField(max_length=100, blank=True)
    destination_city = models.CharField(max_length=100, blank=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    deadline_at = models.DateTimeField(null=True, blank=True)

    selected_offer = models.ForeignKey(
        "OrderOffer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="selected_for_orders",
    )
    price_agreed_amount = models.BigIntegerField(null=True, blank=True)
    price_agreed_currency = models.CharField(max_length=10, default="IRR")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def owner(self):
        if self.type == OrderType.BUY:
            return self.buyer
        if self.type == OrderType.SELL:
            return self.assigned_provider
        return None

    def __str__(self):
        return f"{self.type} - {self.title}"


class OfferStatus(models.TextChoices):
    PENDING = "PENDING", "PENDING"
    ACCEPTED = "ACCEPTED", "ACCEPTED"
    DECLINED = "DECLINED", "DECLINED"
    WITHDRAWN = "WITHDRAWN", "WITHDRAWN"


class OrderOffer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="offers")
    offered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="order_offers"
    )
    price_total_amount = models.BigIntegerField()
    price_total_currency = models.CharField(max_length=10, default="IRR")
    price_unit_amount = models.BigIntegerField(null=True, blank=True)
    price_unit_currency = models.CharField(max_length=10, default="IRR")
    deposit_percent = models.IntegerField(null=True, blank=True)
    lead_time_days = models.IntegerField(null=True, blank=True)
    terms = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=OfferStatus.choices, default=OfferStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Offer({self.order_id}) - {self.offered_by_id}"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=32, null=True, blank=True)
    to_status = models.CharField(max_length=32)
    event = models.CharField(max_length=50)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    meta = models.JSONField(null=True, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order_id} {self.from_status}->{self.to_status}"


class OrderRequestType(models.TextChoices):
    BUY = "BUY", "BUY"
    SELL = "SELL", "SELL"


class OrderRequestStatus(models.TextChoices):
    DRAFT = "DRAFT", "DRAFT"
    ACTIVE = "ACTIVE", "ACTIVE"
    PENDING_WAREHOUSE = "PENDING_WAREHOUSE", "PENDING_WAREHOUSE"
    APPROVED = "APPROVED", "APPROVED"
    REJECTED = "REJECTED", "REJECTED"
    DEACTIVATED = "DEACTIVATED", "DEACTIVATED"
    COMPLETED = "COMPLETED", "COMPLETED"


class OrderRequestQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def public_feed(self):
        return self.active().filter(
            Q(type=OrderRequestType.BUY, status__in=[OrderRequestStatus.ACTIVE, OrderRequestStatus.APPROVED])
            | Q(type=OrderRequestType.SELL, status=OrderRequestStatus.APPROVED)
        )


class ActiveOrderRequestManager(models.Manager):
    def get_queryset(self):
        return OrderRequestQuerySet(self.model, using=self._db).active()

    def public_feed(self):
        return self.get_queryset().public_feed()


class OrderRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="order_requests"
    )
    type = models.CharField(max_length=10, choices=OrderRequestType.choices)
    status = models.CharField(
        max_length=32,
        choices=OrderRequestStatus.choices,
        default=OrderRequestStatus.DRAFT,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)

    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_requests",
    )
    product_title = models.CharField(max_length=255, blank=True)
    grade = models.CharField(max_length=64, blank=True)
    dimensions = models.CharField(max_length=128, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quantity_unit = models.CharField(max_length=20, blank=True)
    target_price_amount = models.BigIntegerField(null=True, blank=True)
    target_price_currency = models.CharField(max_length=10, default="IRR")

    loading_city = models.CharField(max_length=100, blank=True)
    unloading_city = models.CharField(max_length=100, blank=True)
    loading_location = models.TextField(blank=True)
    unloading_location = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_order_requests",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    warehouse_reject_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveOrderRequestManager()
    all_objects = OrderRequestQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["status", "type", "created_at"]),
        ]

    def __str__(self):
        return f"OrderRequest({self.type})-{self.id}"


class OrderRequestStatusHistory(models.Model):
    order_request = models.ForeignKey(
        OrderRequest, on_delete=models.CASCADE, related_name="status_history"
    )
    from_status = models.CharField(max_length=32, null=True, blank=True)
    to_status = models.CharField(max_length=32)
    event = models.CharField(max_length=64)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    meta = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-at",)

    def __str__(self):
        return f"{self.order_request_id} {self.from_status}->{self.to_status}"


class OrderRequestDocument(models.Model):
    order_request = models.ForeignKey(
        OrderRequest, on_delete=models.CASCADE, related_name="documents"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="order_request_docs/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at",)

    def __str__(self):
        return f"OrderRequestDocument({self.order_request_id})-{self.name}"


class OrderRequestAuditLog(models.Model):
    order_request = models.ForeignKey(
        OrderRequest, on_delete=models.CASCADE, related_name="audit_logs"
    )
    action = models.CharField(max_length=64)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"OrderRequestAuditLog({self.order_request_id})-{self.action}"


class OrderRequestNotification(models.Model):
    order_request = models.ForeignKey(
        OrderRequest, on_delete=models.CASCADE, related_name="notifications"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="order_request_notifications"
    )
    event = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"OrderRequestNotification({self.order_request_id})-{self.event}"
