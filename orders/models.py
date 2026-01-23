import uuid

from django.conf import settings
from django.db import models

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
