import uuid
from pathlib import Path

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


class StorePaymentMethod(models.TextChoices):
    PAYMENT_LINK = "payment_link", "Payment link"
    SATNA_OFFLINE = "satna_offline", "Offline Satna"


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


class StoreDeliveryRequestStatus(models.TextChoices):
    PUBLISHED = "PUBLISHED", "Published"
    ASSIGNED = "ASSIGNED", "Assigned"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class StoreDeliveryOfferStatus(models.TextChoices):
    OFFERED = "OFFERED", "Offered"
    ACCEPTED = "ACCEPTED", "Accepted"
    DECLINED = "DECLINED", "Declined"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class StoreDeliveryAssignmentStatus(models.TextChoices):
    ACCEPTED = "ACCEPTED", "Accepted"
    ARRIVED_FOR_LOADING = "ARRIVED_FOR_LOADING", "Arrived for loading"
    LOADED = "LOADED", "Loaded"
    IN_TRANSIT = "IN_TRANSIT", "In transit"
    DELIVERED = "DELIVERED", "Delivered"
    PROOF_SUBMITTED = "PROOF_SUBMITTED", "Proof submitted"
    CANCELLED = "CANCELLED", "Cancelled"


class StoreDeliveryDocumentType(models.TextChoices):
    BILL_OF_LADING = "bill_of_lading", "Bill of lading"
    WEIGHBRIDGE = "weighbridge", "Weighbridge receipt"
    DELIVERY_RECEIPT = "delivery_receipt", "Delivery receipt"
    LOAD_PHOTO = "load_photo", "Load photo"
    OTHER = "other", "Other"


def weighbridge_slip_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"weighbridge_slips/{instance.order.created_at:%Y/%m}/{uuid.uuid4().hex}{extension}"


def delivery_document_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"delivery_docs/{instance.assignment_id}/{uuid.uuid4().hex}{extension}"


class StoreBuyerAddress(models.Model):
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_addresses",
    )
    title = models.CharField(max_length=120, blank=True)
    province = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=40, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-is_default", "-updated_at")
        indexes = [models.Index(fields=["buyer", "is_default"])]

    def __str__(self):
        return self.title or f"{self.province} - {self.city}"


class StoreBuyerInvoiceProfile(models.Model):
    BUYER_TYPE_INDIVIDUAL = "individual"
    BUYER_TYPE_COMPANY = "company"
    BUYER_TYPE_CHOICES = [
        (BUYER_TYPE_INDIVIDUAL, "Individual"),
        (BUYER_TYPE_COMPANY, "Company"),
    ]

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_invoice_profiles",
    )
    title = models.CharField(max_length=120, blank=True)
    buyer_type = models.CharField(max_length=20, choices=BUYER_TYPE_CHOICES, default=BUYER_TYPE_INDIVIDUAL)
    full_name = models.CharField(max_length=160, blank=True)
    national_id = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    economic_code = models.CharField(max_length=40, blank=True)
    registration_id = models.CharField(max_length=40, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-is_default", "-updated_at")
        indexes = [models.Index(fields=["buyer", "buyer_type", "is_default"])]

    def __str__(self):
        if self.buyer_type == self.BUYER_TYPE_COMPANY:
            return self.company_name or self.title or "Company invoice profile"
        return self.full_name or self.title or "Individual invoice profile"


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
    payment_method = models.CharField(
        max_length=24,
        choices=StorePaymentMethod.choices,
        default=StorePaymentMethod.PAYMENT_LINK,
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
    driver_name = models.CharField(max_length=160, blank=True)
    driver_phone = models.CharField(max_length=40, blank=True)
    vehicle_type = models.CharField(max_length=100, blank=True)
    vehicle_plate = models.CharField(max_length=80, blank=True)
    logistics_note = models.TextField(blank=True)
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


class StoreOrderLoadingVehicle(models.Model):
    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name="loading_vehicles")
    sequence = models.PositiveSmallIntegerField(default=1)
    driver_name = models.CharField(max_length=160)
    driver_phone = models.CharField(max_length=40, blank=True)
    vehicle_type = models.CharField(max_length=100, blank=True)
    vehicle_plate = models.CharField(max_length=80)
    planned_weight_kg = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    loaded_weight_kg = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_store_loading_vehicles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sequence", "id")
        indexes = [
            models.Index(fields=["order", "is_active", "sequence"]),
        ]

    def __str__(self):
        return f"{self.order_id} vehicle {self.sequence} - {self.driver_name}"


class StoreOrderWeighbridgeSlip(models.Model):
    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name="weighbridge_slips")
    loading_vehicle = models.ForeignKey(
        StoreOrderLoadingVehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weighbridge_slips",
    )
    file = models.FileField(upload_to=weighbridge_slip_upload_path)
    slip_number = models.CharField(max_length=80, blank=True)
    weight_kg = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    note = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_store_weighbridge_slips",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=["order", "created_at"]),
        ]

    def __str__(self):
        return f"{self.order_id} weighbridge slip {self.id}"


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


class StoreDeliveryRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name="delivery_requests")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_delivery_requests",
    )
    status = models.CharField(
        max_length=24,
        choices=StoreDeliveryRequestStatus.choices,
        default=StoreDeliveryRequestStatus.PUBLISHED,
        db_index=True,
    )
    total_weight_kg = models.DecimalField(max_digits=12, decimal_places=3)
    required_driver_count = models.PositiveSmallIntegerField(default=1)
    accepted_driver_count = models.PositiveSmallIntegerField(default=0)
    per_driver_weight_limit_kg = models.DecimalField(max_digits=12, decimal_places=3, default=25000)
    vehicle_type = models.CharField(max_length=100, blank=True)
    pickup_window_start = models.DateTimeField(null=True, blank=True)
    pickup_window_end = models.DateTimeField(null=True, blank=True)
    dispatch_deadline = models.DateTimeField(null=True, blank=True)
    pickup_notes = models.TextField(blank=True)
    dispatcher_notes = models.TextField(blank=True)
    shipment_snapshot = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["order", "status", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"DeliveryRequest({self.order_id}) {self.status}"


class StoreDeliveryOffer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(StoreDeliveryRequest, on_delete=models.CASCADE, related_name="offers")
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_delivery_offers",
    )
    status = models.CharField(
        max_length=16,
        choices=StoreDeliveryOfferStatus.choices,
        default=StoreDeliveryOfferStatus.OFFERED,
        db_index=True,
    )
    response_note = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        unique_together = ("request", "driver")
        indexes = [
            models.Index(fields=["driver", "status", "created_at"]),
            models.Index(fields=["request", "status"]),
        ]

    def __str__(self):
        return f"DeliveryOffer({self.request_id}) {self.driver_id} {self.status}"


class StoreDeliveryAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(StoreDeliveryRequest, on_delete=models.CASCADE, related_name="assignments")
    offer = models.OneToOneField(
        StoreDeliveryOffer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment",
    )
    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name="delivery_assignments")
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_delivery_assignments",
    )
    status = models.CharField(
        max_length=24,
        choices=StoreDeliveryAssignmentStatus.choices,
        default=StoreDeliveryAssignmentStatus.ACCEPTED,
        db_index=True,
    )
    load_sequence = models.PositiveSmallIntegerField(default=1)
    planned_weight_kg = models.DecimalField(max_digits=12, decimal_places=3)
    vehicle_type = models.CharField(max_length=100, blank=True)
    vehicle_plate = models.CharField(max_length=80, blank=True)
    driver_phone = models.CharField(max_length=40, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    arrived_for_loading_at = models.DateTimeField(null=True, blank=True)
    loaded_at = models.DateTimeField(null=True, blank=True)
    in_transit_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    proof_submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("load_sequence", "created_at")
        unique_together = ("request", "driver")
        indexes = [
            models.Index(fields=["driver", "status", "created_at"]),
            models.Index(fields=["order", "status"]),
            models.Index(fields=["request", "status"]),
        ]

    def __str__(self):
        return f"DeliveryAssignment({self.order_id}) {self.driver_id} {self.status}"


class StoreDeliveryEvent(models.Model):
    request = models.ForeignKey(StoreDeliveryRequest, on_delete=models.CASCADE, related_name="events")
    assignment = models.ForeignKey(
        StoreDeliveryAssignment,
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    event = models.CharField(max_length=80)
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.request_id} {self.event}"


class StoreDeliveryDocument(models.Model):
    assignment = models.ForeignKey(StoreDeliveryAssignment, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(
        max_length=32,
        choices=StoreDeliveryDocumentType.choices,
        default=StoreDeliveryDocumentType.OTHER,
    )
    file = models.FileField(upload_to=delivery_document_upload_path)
    note = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_delivery_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"DeliveryDocument({self.assignment_id}) {self.document_type}"
