from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
from secrets import token_urlsafe
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from products.models import DeliveryLocation, Offer, PricingTier, Product

from .models import (
    StoreOrder,
    StoreOrderItem,
    StoreOrderNotification,
    StoreOrderStatus,
    StoreOrderStatusHistory,
    StoreNotificationChannel,
    StoreNotificationStatus,
    StorePaymentStatus,
    StorePayment,
    StoreQuantityUnit,
)


TERMINAL_STATUSES = {
    StoreOrderStatus.CANCELLED,
    StoreOrderStatus.EXPIRED,
    StoreOrderStatus.COMPLETED,
}

PAYMENT_ACTIONABLE_STATUSES = {
    StoreOrderStatus.PRICE_CONFIRMED,
    StoreOrderStatus.PAYMENT_PENDING,
}

SETTLEMENT_TERM_FEE_BPS = {
    1: 0,
    2: 50,
    3: 100,
    4: 150,
}

STEEL_WEIGHT_FACTOR = Decimal("7.85") / Decimal("1000000")


def _clean_decimal(value):
    if value is None:
        return None
    return str(value)


def _option_label(value):
    return value or ""


def product_snapshot(product):
    category = product.category
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "category": {
            "id": category.id if category else None,
            "name": category.name if category else "",
            "code": category.code if category else "",
        },
        "availability_status": product.availability_status,
    }


def specification_snapshot(product):
    spec = getattr(product, "specifications", None)
    if not spec:
        return {}
    return {
        "material_type": spec.material_type,
        "steel_grade": spec.steel_grade,
        "surface_finish": spec.surface_finish,
        "manufacturing_process": spec.manufacturing_process,
        "factory": spec.factory,
        "cut_type": spec.cut_type,
        "thickness_mm": _clean_decimal(spec.thickness_mm),
        "width_mm": _clean_decimal(spec.width_mm),
        "length_mm": _clean_decimal(spec.length_mm),
        "height_mm": _clean_decimal(spec.height_mm),
        "diameter_mm": _clean_decimal(spec.diameter_mm),
        "weight_kg_per_unit": _clean_decimal(spec.weight_kg_per_unit),
    }


def delivery_snapshot(delivery):
    if not delivery:
        return {}
    return {
        "incoterm": delivery.incoterm,
        "country": delivery.country,
        "province": delivery.province or "",
        "city": delivery.city or "",
        "port": delivery.port or "",
        "address": delivery.address or "",
    }


def get_available_tier(product, quantity, offer_id=None, pricing_tier_id=None):
    offers = Offer.objects.filter(product=product, is_active=True).select_related("seller")
    if offer_id:
        offers = offers.filter(id=offer_id)
    tiers = PricingTier.objects.filter(offer__in=offers).select_related("offer", "offer__seller")
    if pricing_tier_id:
        tiers = tiers.filter(id=pricing_tier_id)
    quantity = Decimal(str(quantity or 1))
    eligible = []
    for tier in tiers:
        minimum = Decimal(str(tier.minimum_quantity or 0))
        maximum = Decimal(str(tier.maximum_quantity)) if tier.maximum_quantity is not None else None
        if quantity < minimum:
            continue
        if maximum is not None and quantity > maximum:
            continue
        eligible.append(tier)
    if not eligible:
        return None
    return sorted(eligible, key=lambda item: item.unit_price)[0]


def normalize_quantity_unit(value):
    value = (value or StoreQuantityUnit.TON).strip().lower()
    aliases = {
        "tons": StoreQuantityUnit.TON,
        "tonne": StoreQuantityUnit.TON,
        "kilogram": StoreQuantityUnit.KG,
        "kilograms": StoreQuantityUnit.KG,
        "sheet_count": StoreQuantityUnit.SHEET,
        "sheets": StoreQuantityUnit.SHEET,
    }
    value = aliases.get(value, value)
    allowed = {StoreQuantityUnit.TON, StoreQuantityUnit.KG, StoreQuantityUnit.SHEET}
    if value not in allowed:
        raise ValueError("invalid_quantity_unit")
    return value


def product_is_sheet(product):
    spec = getattr(product, "specifications", None)
    if getattr(spec, "material_type", "") == "sheet":
        return True
    category = getattr(product, "category", None)
    if not category:
        return False
    try:
        return category.resolved_product_kind() == "sheet"
    except Exception:
        return False


def estimate_sheet_unit_weight_kg(product):
    spec = getattr(product, "specifications", None)
    if not spec:
        return None
    if spec.weight_kg_per_unit:
        return Decimal(str(spec.weight_kg_per_unit))
    required = (spec.thickness_mm, spec.width_mm, spec.length_mm)
    if not all(required):
        return None
    return (
        Decimal(str(spec.thickness_mm))
        * Decimal(str(spec.width_mm))
        * Decimal(str(spec.length_mm))
        * STEEL_WEIGHT_FACTOR
    ).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def pricing_weight_kg_for_item(product, quantity, quantity_unit):
    quantity = Decimal(str(quantity or 1))
    quantity_unit = normalize_quantity_unit(quantity_unit)
    if quantity_unit == StoreQuantityUnit.TON:
        return (quantity * Decimal("1000")).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if quantity_unit == StoreQuantityUnit.KG:
        return quantity.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if not product_is_sheet(product):
        raise ValueError("sheet_unit_requires_sheet_product")
    unit_weight = estimate_sheet_unit_weight_kg(product)
    if unit_weight is None:
        raise ValueError("sheet_weight_unavailable")
    return (quantity * unit_weight).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def weight_kg_to_ton(weight_kg):
    return (Decimal(str(weight_kg or 0)) / Decimal("1000")).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def money_for_weight(unit_price, weight_kg):
    if unit_price is None or weight_kg is None:
        return None
    amount = Decimal(str(unit_price)) * (Decimal(str(weight_kg)) / Decimal("1000"))
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def settlement_fee_for(subtotal_amount, settlement_term_days):
    days = int(settlement_term_days or 1)
    bps = SETTLEMENT_TERM_FEE_BPS.get(days, SETTLEMENT_TERM_FEE_BPS[max(SETTLEMENT_TERM_FEE_BPS)])
    return int((Decimal(str(subtotal_amount or 0)) * Decimal(str(bps)) / Decimal("10000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def paid_amount_for_order(order):
    return sum(
        payment.amount
        for payment in StorePayment.objects.filter(order=order, status=StorePaymentStatus.PAID)
    )


def remaining_amount_for_order(order):
    return max(int(order.total_amount or 0) - int(paid_amount_for_order(order) or 0), 0)


def get_first_delivery(offer):
    if not offer:
        return None
    return DeliveryLocation.objects.filter(offer=offer).first()


def write_status_history(order, from_status, to_status, event, actor, meta=None):
    StoreOrderStatusHistory.objects.create(
        order=order,
        from_status=from_status,
        to_status=to_status,
        event=event,
        actor_user=actor if getattr(actor, "is_authenticated", False) else None,
        meta=meta or {},
    )


def set_order_status(order, to_status, event, actor, meta=None):
    from_status = order.status
    if from_status == to_status:
        return order
    if from_status in TERMINAL_STATUSES:
        raise ValueError("terminal_order_status")
    order.status = to_status
    if to_status == StoreOrderStatus.PAID:
        order.payment_status = StorePaymentStatus.PAID
    order.save(update_fields=["status", "payment_status", "updated_at"])
    write_status_history(order, from_status, to_status, event, actor, meta=meta)
    return order


def is_order_payment_overdue(order, now=None):
    if not order.payment_due_at or order.payment_status == StorePaymentStatus.PAID:
        return False
    now = now or timezone.now()
    return order.payment_due_at < now


def build_payment_link(order, token=None):
    frontend_base = getattr(settings, "FRONTEND_BASE", "http://localhost:3000").rstrip("/")
    query = urlencode({"order": str(order.id), "token": token or order.payment_link_token})
    return f"{frontend_base}/account/payments?{query}"


@transaction.atomic
def generate_payment_link(order, actor=None, due_at=None):
    if order.payment_status == StorePaymentStatus.PAID or order.status not in PAYMENT_ACTIONABLE_STATUSES:
        raise ValueError("order_is_not_payment_actionable")
    token = order.payment_link_token or token_urlsafe(32)
    order.payment_link_token = token
    order.payment_link_url = build_payment_link(order, token)
    order.payment_link_created_at = timezone.now()
    if due_at is not None:
        order.payment_due_at = due_at
    order.save(
        update_fields=[
            "payment_link_token",
            "payment_link_url",
            "payment_link_created_at",
            "payment_due_at",
            "updated_at",
        ]
    )
    write_status_history(
        order,
        order.status,
        order.status,
        "STORE_ORDER_PAYMENT_LINK_GENERATED",
        actor,
        meta={"payment_link_url": order.payment_link_url, "payment_due_at": order.payment_due_at.isoformat() if order.payment_due_at else None},
    )
    return order


@transaction.atomic
def send_payment_link(order, actor=None, recipient=None, due_at=None):
    if not order.payment_link_url or due_at is not None:
        generate_payment_link(order, actor=actor, due_at=due_at)
        order.refresh_from_db()

    recipient = (recipient or order.contact_phone or "").strip()
    provider_enabled = bool(getattr(settings, "SMS_PROVIDER_ENABLED", False))
    status = StoreNotificationStatus.SENT if provider_enabled else StoreNotificationStatus.SKIPPED
    payload = {
        "payment_link_url": order.payment_link_url,
        "payment_due_at": order.payment_due_at.isoformat() if order.payment_due_at else None,
        "provider_enabled": provider_enabled,
    }
    notification = StoreOrderNotification.objects.create(
        order=order,
        channel=StoreNotificationChannel.SMS,
        recipient=recipient,
        event="STORE_ORDER_PAYMENT_LINK_SENT",
        status=status,
        actor_user=actor if getattr(actor, "is_authenticated", False) else None,
        payload=payload,
        error_message="" if provider_enabled else "sms_provider_not_configured",
    )

    order.payment_link_sent_to = recipient
    if provider_enabled:
        order.payment_link_sent_at = timezone.now()
    order.save(update_fields=["payment_link_sent_to", "payment_link_sent_at", "updated_at"])
    write_status_history(
        order,
        order.status,
        order.status,
        "STORE_ORDER_PAYMENT_LINK_SENT",
        actor,
        meta={"notification_id": notification.id, "status": notification.status, "recipient": recipient},
    )
    return notification


@transaction.atomic
def record_final_weights(order, items_data, actor=None):
    items_by_id = {item.id: item for item in order.items.all()}
    changed = []
    initial_subtotal = sum(int(item.total_price_amount or 0) for item in items_by_id.values())
    final_subtotal = 0

    for item_data in items_data:
        item_id = int(item_data["item_id"])
        if item_id not in items_by_id:
            raise ValueError("order_item_not_found")
        item = items_by_id[item_id]
        final_weight = Decimal(str(item_data["final_weight_kg"]))
        final_price = money_for_weight(item.unit_price_amount, final_weight)
        if final_price is None:
            final_price = item.total_price_amount
        base_price = int(item.total_price_amount or 0)
        item.final_weight_kg = final_weight
        item.final_price_amount = final_price
        item.weight_adjustment_amount = int(final_price or 0) - base_price
        item.save(
            update_fields=[
                "final_weight_kg",
                "final_price_amount",
                "weight_adjustment_amount",
            ]
        )
        changed.append(
            {
                "item_id": item.id,
                "product_name": item.product_name,
                "estimated_weight_kg": str(item.estimated_weight_kg or ""),
                "final_weight_kg": str(final_weight),
                "weight_adjustment_amount": item.weight_adjustment_amount,
            }
        )

    for item in order.items.all():
        final_subtotal += int(item.final_price_amount if item.final_price_amount is not None else item.total_price_amount or 0)

    previous_status = order.status
    order.weight_adjustment_amount = final_subtotal - initial_subtotal
    order.total_amount = int(order.subtotal_amount or 0) + int(order.settlement_term_fee_amount or 0) + order.weight_adjustment_amount
    paid_amount = paid_amount_for_order(order)
    if order.total_amount > paid_amount:
        order.payment_status = StorePaymentStatus.PENDING
        if order.status == StoreOrderStatus.PAID:
            order.status = StoreOrderStatus.PAYMENT_PENDING
    elif paid_amount >= order.total_amount and paid_amount > 0:
        order.payment_status = StorePaymentStatus.PAID
    order.save(
        update_fields=[
            "weight_adjustment_amount",
            "total_amount",
            "payment_status",
            "status",
            "updated_at",
        ]
    )
    write_status_history(
        order,
        previous_status,
        order.status,
        "STORE_ORDER_FINAL_WEIGHT_RECORDED",
        actor,
        meta={
            "items": changed,
            "initial_subtotal": initial_subtotal,
            "final_subtotal": final_subtotal,
            "weight_adjustment_amount": order.weight_adjustment_amount,
            "paid_amount": paid_amount,
            "remaining_amount": remaining_amount_for_order(order),
        },
    )
    if remaining_amount_for_order(order) > 0 and order.status in PAYMENT_ACTIONABLE_STATUSES:
        generate_payment_link(order, actor=actor)
    return order


@transaction.atomic
def create_store_order(user, validated_data):
    items_data = validated_data.pop("items")
    settlement_term_days = int(validated_data.pop("settlement_term_days", 1) or 1)
    order = StoreOrder.objects.create(
        buyer=user,
        status=StoreOrderStatus.SUBMITTED,
        submitted_at=timezone.now(),
        settlement_term_days=settlement_term_days,
        **validated_data,
    )

    subtotal = 0
    needs_quote = False
    created_items = []
    for item_data in items_data:
        product = Product.objects.select_related("category", "specifications").get(
            pk=item_data["product_id"],
            is_active=True,
        )
        quantity = item_data.get("quantity") or Decimal("1")
        quantity_unit = normalize_quantity_unit(item_data.get("quantity_unit"))
        try:
            price_weight_kg = pricing_weight_kg_for_item(product, quantity, quantity_unit)
        except ValueError:
            price_weight_kg = None
        tier = None
        pricing_quantity_ton = weight_kg_to_ton(price_weight_kg) if price_weight_kg is not None else quantity
        if product.availability_status != Product.AVAILABILITY_OUT_OF_STOCK and price_weight_kg is not None:
            tier = get_available_tier(
                product,
                pricing_quantity_ton,
                offer_id=item_data.get("offer_id"),
                pricing_tier_id=item_data.get("pricing_tier_id"),
            )
        offer = tier.offer if tier else None
        delivery = get_first_delivery(offer)
        unit_price = int(tier.unit_price) if tier else None
        total_price = money_for_weight(unit_price, price_weight_kg) if unit_price is not None else None
        if total_price is None:
            needs_quote = True
        else:
            subtotal += total_price

        created_items.append(
            StoreOrderItem.objects.create(
                order=order,
                product=product,
                offer=offer,
                pricing_tier=tier,
                product_name=product.name,
                seller_name=getattr(getattr(offer, "seller", None), "company_name", "") if offer else "",
                quantity=quantity,
                quantity_unit=quantity_unit,
                estimated_weight_kg=price_weight_kg,
                price_weight_kg=price_weight_kg,
                unit_price_amount=unit_price,
                total_price_amount=total_price,
                product_snapshot=product_snapshot(product),
                specification_snapshot=specification_snapshot(product),
                delivery_snapshot=delivery_snapshot(delivery),
            )
        )

    final_status = StoreOrderStatus.QUOTE_REQUESTED if needs_quote else StoreOrderStatus.PAYMENT_PENDING
    final_payment_status = StorePaymentStatus.UNPAID if needs_quote else StorePaymentStatus.PENDING
    order.status = final_status
    order.payment_status = final_payment_status
    order.subtotal_amount = subtotal
    order.settlement_term_fee_amount = 0 if needs_quote else settlement_fee_for(subtotal, settlement_term_days)
    order.total_amount = subtotal + order.settlement_term_fee_amount
    if not needs_quote:
        order.payment_due_at = timezone.now() + timedelta(
            days=settlement_term_days
        )
    order.save(
        update_fields=[
            "status",
            "payment_status",
            "subtotal_amount",
            "settlement_term_days",
            "settlement_term_fee_amount",
            "total_amount",
            "payment_due_at",
            "updated_at",
        ]
    )
    if not needs_quote:
        generate_payment_link(order, actor=user)
    write_status_history(
        order,
        None,
        final_status,
        "STORE_ORDER_CREATED",
        user,
        meta={"item_count": len(created_items), "needs_quote": needs_quote},
    )
    return order
