from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from datetime import timedelta
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import RoleCode, UserRole
from products.models import DeliveryLocation, Offer, PricingBasis, PricingTier, Product

from .models import (
    FreightBidInvite,
    FreightBidInviteStatus,
    FreightBidOffer,
    FreightBidSession,
    FreightBidStatus,
    FreightRateSettings,
    StoreOrder,
    StoreDeliveryAssignment,
    StoreDeliveryAssignmentStatus,
    StoreDeliveryDocument,
    StoreDeliveryDocumentType,
    StoreDeliveryEvent,
    StoreDeliveryOffer,
    StoreDeliveryOfferStatus,
    StoreDeliveryRecipientType,
    StoreDeliveryRequest,
    StoreDeliveryRequestStatus,
    StoreDriverOperationalProfile,
    StoreOrderItem,
    StoreOrderLoadingVehicle,
    StoreOrderNotification,
    StoreQuoteConfirmationStatus,
    StoreOrderStatus,
    StoreOrderStatusHistory,
    StoreRiskStatus,
    StoreNotificationChannel,
    StoreNotificationStatus,
    StorePaymentStatus,
    StorePaymentMethod,
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

LOADING_STATUSES = {
    StoreOrderStatus.READY_FOR_PICKUP,
    StoreOrderStatus.SHIPPED,
    StoreOrderStatus.DELIVERED,
    StoreOrderStatus.COMPLETED,
}

FINAL_WEIGHT_REQUIRED_STATUSES = {
    StoreOrderStatus.READY_FOR_PICKUP,
    StoreOrderStatus.SHIPPED,
    StoreOrderStatus.DELIVERED,
    StoreOrderStatus.COMPLETED,
}

SETTLEMENT_TERM_FEE_BPS = {
    1: 0,
    2: 50,
    3: 100,
    4: 150,
}

STEEL_SHEET_WEIGHT_FACTOR = Decimal("8") / Decimal("1000000")


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
        "purchase_terms": product.purchase_terms if isinstance(product.purchase_terms, list) else [],
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
        "sales_mode": spec.sales_mode,
        "head_tail_policy": spec.head_tail_policy,
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


def normalize_price_basis(value):
    value = (value or PricingBasis.KG).strip().lower()
    allowed = {PricingBasis.TON, PricingBasis.KG, PricingBasis.SHEET}
    return value if value in allowed else PricingBasis.KG


def pricing_condition_label(tier):
    if not tier:
        return ""
    if tier.condition_label:
        return tier.condition_label
    width = getattr(tier, "dimension_width_mm", None)
    length = getattr(tier, "dimension_length_mm", None)
    if width and length:
        return f"{width.normalize():f}x{length.normalize():f} mm"
    if width:
        return f"width {width.normalize():f} mm"
    return tier.tier_name or ""


def tier_quantity_for_comparison(product, tier, quantity, quantity_unit):
    basis = normalize_price_basis(getattr(tier, "price_basis", PricingBasis.TON))
    quantity = Decimal(str(quantity or 1))
    quantity_unit = normalize_quantity_unit(quantity_unit)
    if basis == PricingBasis.SHEET:
        return quantity if quantity_unit == StoreQuantityUnit.SHEET else None
    weight_kg = pricing_weight_kg_for_item(product, quantity, quantity_unit, tier=tier)
    if basis == PricingBasis.KG:
        return weight_kg
    return weight_kg_to_ton(weight_kg)


def get_available_tier(product, quantity, quantity_unit=StoreQuantityUnit.TON, offer_id=None, pricing_tier_id=None):
    offers = Offer.objects.filter(product=product, is_active=True).select_related("seller")
    if offer_id:
        offers = offers.filter(id=offer_id)
    tiers = PricingTier.objects.filter(offer__in=offers).select_related("offer", "offer__seller")
    if pricing_tier_id:
        tiers = tiers.filter(id=pricing_tier_id)
    quantity = Decimal(str(quantity or 1))
    eligible = []
    for tier in tiers:
        try:
            comparison_quantity = tier_quantity_for_comparison(product, tier, quantity, quantity_unit)
        except ValueError:
            continue
        if comparison_quantity is None:
            continue
        minimum = Decimal(str(tier.minimum_quantity or 0))
        maximum = Decimal(str(tier.maximum_quantity)) if tier.maximum_quantity is not None else None
        if comparison_quantity < minimum:
            continue
        if maximum is not None and comparison_quantity > maximum:
            continue
        eligible.append(tier)
    if not eligible:
        return None
    return sorted(
        eligible,
        key=lambda item: money_for_tier(item, product, quantity, quantity_unit) or int(item.unit_price),
    )[0]


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


def product_is_coil(product):
    spec = getattr(product, "specifications", None)
    process = (getattr(spec, "manufacturing_process", "") or "").strip().lower()
    return process in {"coil", "roll"}


def product_sales_mode(product):
    spec = getattr(product, "specifications", None)
    sales_mode = (getattr(spec, "sales_mode", "") or "").strip()
    if sales_mode:
        return sales_mode
    if product_is_coil(product):
        return "coil_full"
    if product_is_sheet(product):
        return "sheet"
    return ""


def default_coil_weight_ton(product):
    spec = getattr(product, "specifications", None)
    # اگر «وزن واحد» (kg) برای محصول تنظیم شده باشد، همان وزنِ هر رول است؛
    # وگرنه پیش‌فرضِ ثابت بر اساس ضخامت.
    configured_kg = Decimal(str(getattr(spec, "weight_kg_per_unit", "") or 0))
    if configured_kg > 0:
        return (configured_kg / Decimal("1000")).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    thickness = Decimal(str(getattr(spec, "thickness_mm", "") or 0))
    if thickness >= Decimal("3"):
        return Decimal("22.5")
    return Decimal("20")


def _decimal_from_selection(value, field_name):
    try:
        number = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"invalid_{field_name}") from exc
    if number <= 0:
        raise ValueError(f"invalid_{field_name}")
    return number


def normalize_cut_lines_selection(product, selection_details, *, allow_coil=False):
    cut_lines = selection_details.get("cut_lines") if isinstance(selection_details, dict) else None
    if not cut_lines:
        return selection_details, None, None
    if not isinstance(cut_lines, list):
        raise ValueError("cut_lines_must_be_list")
    if not product_is_sheet(product):
        raise ValueError("cut_lines_require_sheet_product")
    if product_is_coil(product) and not allow_coil:
        raise ValueError("cut_lines_require_sheet_product")
    spec = getattr(product, "specifications", None)
    thickness = Decimal(str(getattr(spec, "thickness_mm", "") or 0))
    if thickness <= 0:
        raise ValueError("sheet_thickness_required_for_cut_lines")

    normalized_lines = []
    total_weight_kg = Decimal("0")
    total_count = Decimal("0")
    for index, line in enumerate(cut_lines, start=1):
        if not isinstance(line, dict):
            raise ValueError("invalid_cut_line")
        count = _decimal_from_selection(line.get("count") or line.get("quantity"), "cut_line_count")
        if count != count.to_integral_value():
            raise ValueError("cut_line_count_must_be_integer")
        width_m = _decimal_from_selection(line.get("width_m") or line.get("width"), "cut_line_width_m")
        length_m = _decimal_from_selection(line.get("length_m") or line.get("length"), "cut_line_length_m")
        estimated_weight_kg = (thickness * width_m * length_m * Decimal("8") * count).quantize(
            Decimal("0.001"),
            rounding=ROUND_HALF_UP,
        )
        total_weight_kg += estimated_weight_kg
        total_count += count
        normalized_lines.append(
            {
                "index": index,
                "count": int(count),
                "width_m": str(width_m.normalize()),
                "length_m": str(length_m.normalize()),
                "estimated_weight_kg": str(estimated_weight_kg),
            }
        )

    normalized = dict(selection_details or {})
    normalized["cut_lines"] = normalized_lines
    normalized["estimated_weight_kg"] = str(total_weight_kg.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
    normalized["total_sheet_count"] = int(total_count)
    normalized["selection_mode"] = "cut_lines"
    return normalized, total_count, total_weight_kg.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def normalize_order_item_selection(product, quantity, quantity_unit, selection_details=None):
    quantity = Decimal(str(quantity or 1))
    quantity_unit = normalize_quantity_unit(quantity_unit)
    selection_details = dict(selection_details or {})
    sales_mode = product_sales_mode(product)
    selection_mode = (selection_details.get("selection_mode") or "").strip()

    if product_is_coil(product):
        wants_cut = selection_mode == "cut_lines" or bool(selection_details.get("cut_lines"))
        if sales_mode == "coil_full" and wants_cut:
            raise ValueError("coil_cut_is_not_allowed_for_this_product")
        if sales_mode == "coil_must_cut" and not wants_cut:
            raise ValueError("coil_requires_cut_lines")
        if sales_mode in {"coil_cuttable", "coil_must_cut"} and wants_cut:
            selection_details, sheet_count, cut_weight_kg = normalize_cut_lines_selection(
                product,
                selection_details,
                allow_coil=True,
            )
            selection_details["sales_mode"] = sales_mode
            selection_details["head_tail_policy"] = getattr(
                getattr(product, "specifications", None),
                "head_tail_policy",
                "optional",
            )
            selection_details["head_tail_taken"] = bool(selection_details.get("head_tail_taken", True))
            return sheet_count, StoreQuantityUnit.SHEET, selection_details, cut_weight_kg

        coil_weight_ton = default_coil_weight_ton(product)
        configured_roll_kg = Decimal(
            str(getattr(getattr(product, "specifications", None), "weight_kg_per_unit", "") or 0)
        )
        roll_count = _decimal_from_selection(selection_details.get("roll_count") or quantity or 1, "roll_count")
        if roll_count != roll_count.to_integral_value():
            raise ValueError("roll_count_must_be_integer")
        total_weight_ton = (coil_weight_ton * roll_count).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        coil_weight_kg = (coil_weight_ton * Decimal("1000")).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        total_weight_kg = (total_weight_ton * Decimal("1000")).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        selection_details.update(
            {
                "selection_mode": "coil_full_roll",
                "sales_mode": sales_mode,
                "roll_count": int(roll_count),
                "roll_weight_ton": str(coil_weight_ton),
                "roll_weight_kg": str(coil_weight_kg),
                "total_roll_weight_ton": str(total_weight_ton),
                "total_roll_weight_kg": str(total_weight_kg),
                "roll_weight_rule": "configured"
                if configured_roll_kg > 0
                else ("gte_3mm" if coil_weight_ton > Decimal("20") else "2mm_standard"),
                "client_quantity_ignored": str(quantity),
                "client_quantity_unit_ignored": str(quantity_unit),
            }
        )
        return total_weight_ton, StoreQuantityUnit.TON, selection_details, total_weight_kg

    selection_details, sheet_count, cut_weight_kg = normalize_cut_lines_selection(product, selection_details)
    if cut_weight_kg is not None:
        return sheet_count, StoreQuantityUnit.SHEET, selection_details, cut_weight_kg

    return quantity, quantity_unit, selection_details, None


def estimate_sheet_unit_weight_kg(product, tier=None):
    spec = getattr(product, "specifications", None)
    if not spec:
        return None
    tier_width = getattr(tier, "dimension_width_mm", None) if tier else None
    tier_length = getattr(tier, "dimension_length_mm", None) if tier else None
    if tier_width and tier_length and spec.thickness_mm:
        return (
            Decimal(str(spec.thickness_mm))
            * Decimal(str(tier_width))
            * Decimal(str(tier_length))
            * STEEL_SHEET_WEIGHT_FACTOR
        ).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if spec.weight_kg_per_unit:
        return Decimal(str(spec.weight_kg_per_unit))
    required = (spec.thickness_mm, spec.width_mm, spec.length_mm)
    if not all(required):
        return None
    return (
        Decimal(str(spec.thickness_mm))
        * Decimal(str(spec.width_mm))
        * Decimal(str(spec.length_mm))
        * STEEL_SHEET_WEIGHT_FACTOR
    ).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def pricing_weight_kg_for_item(product, quantity, quantity_unit, tier=None):
    quantity = Decimal(str(quantity or 1))
    quantity_unit = normalize_quantity_unit(quantity_unit)
    if quantity_unit == StoreQuantityUnit.TON:
        return (quantity * Decimal("1000")).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if quantity_unit == StoreQuantityUnit.KG:
        return quantity.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if quantity != quantity.to_integral_value() or quantity < Decimal("1"):
        raise ValueError("sheet_quantity_must_be_integer")
    if not product_is_sheet(product):
        raise ValueError("sheet_unit_requires_sheet_product")
    unit_weight = estimate_sheet_unit_weight_kg(product, tier=tier)
    if unit_weight is None:
        raise ValueError("sheet_weight_unavailable")
    return (quantity * unit_weight).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def weight_kg_to_ton(weight_kg):
    return (Decimal(str(weight_kg or 0)) / Decimal("1000")).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def money_for_basis(unit_price, price_basis, weight_kg=None, quantity=None, quantity_unit=None):
    basis = normalize_price_basis(price_basis)
    if unit_price is None:
        return None
    if basis != PricingBasis.SHEET and weight_kg is None:
        return None
    if basis == PricingBasis.KG:
        amount = Decimal(str(unit_price)) * Decimal(str(weight_kg or 0))
    elif basis == PricingBasis.SHEET:
        if normalize_quantity_unit(quantity_unit) != StoreQuantityUnit.SHEET or quantity is None:
            return None
        amount = Decimal(str(unit_price)) * Decimal(str(quantity))
    else:
        amount = Decimal(str(unit_price)) * (Decimal(str(weight_kg or 0)) / Decimal("1000"))
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def money_for_weight(unit_price, weight_kg):
    return money_for_basis(unit_price, PricingBasis.TON, weight_kg=weight_kg)


def money_for_tier(tier, product, quantity, quantity_unit):
    if tier is None:
        return None
    try:
        weight_kg = pricing_weight_kg_for_item(product, quantity, quantity_unit, tier=tier)
    except ValueError:
        weight_kg = None
    return money_for_basis(
        tier.unit_price,
        tier.price_basis,
        weight_kg=weight_kg,
        quantity=quantity,
        quantity_unit=quantity_unit,
    )


def settlement_fee_for(subtotal_amount, settlement_term_days):
    days = int(settlement_term_days or 1)
    bps = SETTLEMENT_TERM_FEE_BPS.get(days, SETTLEMENT_TERM_FEE_BPS[max(SETTLEMENT_TERM_FEE_BPS)])
    return int((Decimal(str(subtotal_amount or 0)) * Decimal(str(bps)) / Decimal("10000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _money_int(value):
    if value in ("", None):
        return 0
    return max(int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)), 0)


def _clean_text(value):
    return str(value or "").strip()


def order_freight_amount(order):
    metadata = order.metadata if isinstance(order.metadata, dict) else {}
    quote = metadata.get("quote") if isinstance(metadata.get("quote"), dict) else {}
    return _money_int(quote.get("freight_amount"))


def recalculated_order_amounts(order):
    subtotal = sum(int(item.total_price_amount or 0) for item in order.items.all())
    unpriced = any(item.total_price_amount is None for item in order.items.all())
    fee = 0 if unpriced else settlement_fee_for(subtotal, order.settlement_term_days)
    total = subtotal + fee + order_freight_amount(order) + int(order.weight_adjustment_amount or 0)
    return subtotal, fee, total, unpriced


def paid_amount_for_order(order):
    return sum(
        payment.amount
        for payment in StorePayment.objects.filter(order=order, status=StorePaymentStatus.PAID)
    )


def remaining_amount_for_order(order):
    return max(int(order.total_amount or 0) - int(paid_amount_for_order(order) or 0), 0)


def default_price_valid_until(now=None):
    now = now or timezone.now()
    minutes = int(getattr(settings, "STORE_ORDER_PRICE_VALIDITY_MINUTES", 120) or 120)
    return now + timedelta(minutes=minutes)


def is_order_price_expired(order, now=None):
    if not order.price_valid_until or order.payment_status == StorePaymentStatus.PAID:
        return False
    if paid_amount_for_order(order) > 0:
        return False
    now = now or timezone.now()
    return order.price_valid_until < now


def risk_blockers_for_order(order, target_status=None, now=None):
    blockers = []
    target_status = target_status or order.status
    if order.risk_status == StoreRiskStatus.BLOCKED:
        blockers.append("risk_blocked")
    if is_order_price_expired(order, now=now):
        blockers.append("price_expired")
    if target_status == StoreOrderStatus.FULFILLMENT_PENDING:
        return blockers
    if target_status in LOADING_STATUSES:
        if order.payment_status != StorePaymentStatus.PAID:
            blockers.append("payment_not_confirmed")
        if remaining_amount_for_order(order) > 0:
            blockers.append("remaining_payment_required")
        if target_status in FINAL_WEIGHT_REQUIRED_STATUSES:
            final_weight_missing = order.items.filter(
                estimated_weight_kg__isnull=False,
                final_weight_kg__isnull=True,
            ).exists()
            if final_weight_missing:
                blockers.append("final_weight_not_recorded")
        if not order.stock_verified_at:
            blockers.append("stock_not_verified")
        if not order.proforma_confirmed_at:
            blockers.append("proforma_not_confirmed")
        if not order.loading_permission_at:
            blockers.append("loading_permission_not_recorded")
        required_count = required_driver_count_for_weight(delivery_weight_kg_for_order(order))
        assigned_count = order.delivery_assignments.exclude(status=StoreDeliveryAssignmentStatus.CANCELLED).count()
        if required_count and assigned_count < required_count:
            blockers.append("delivery_capacity_not_assigned")
        weight_kg = delivery_weight_kg_for_order(order)
        if weight_kg > MAX_DRIVER_LOAD_KG:
            required_vehicles = required_driver_count_for_weight(weight_kg)
            active_vehicles = list(order.loading_vehicles.filter(is_active=True).order_by("sequence", "id"))
            if len(active_vehicles) < required_vehicles:
                blockers.append("loading_vehicles_insufficient")
            else:
                names = [v.driver_name.strip() for v in active_vehicles[:required_vehicles]]
                plates = [v.vehicle_plate.strip() for v in active_vehicles[:required_vehicles]]
                if any(not n for n in names) or any(not p for p in plates):
                    blockers.append("loading_vehicles_incomplete")
                elif len(set(names)) < len(names):
                    blockers.append("loading_vehicles_duplicate_drivers")
    return blockers


def validate_order_transition(order, target_status):
    if target_status in {StoreOrderStatus.CANCELLED, StoreOrderStatus.EXPIRED}:
        return []
    blockers = risk_blockers_for_order(order, target_status=target_status)
    if blockers:
        raise ValueError(",".join(blockers))
    return blockers


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
    validate_order_transition(order, to_status)
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
    if order.quote_confirmation_status == StoreQuoteConfirmationStatus.AWAITING_BUYER:
        raise ValueError("quote_requires_buyer_confirmation")
    if order.quote_confirmation_status == StoreQuoteConfirmationStatus.REJECTED:
        raise ValueError("quote_rejected_by_buyer")
    if is_order_price_expired(order):
        raise ValueError("price_validity_expired")
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
        final_price = money_for_basis(
            item.unit_price_amount,
            item.price_basis or PricingBasis.TON,
            weight_kg=final_weight,
            quantity=item.quantity,
            quantity_unit=item.quantity_unit,
        )
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
    order.total_amount = (
        int(order.subtotal_amount or 0)
        + int(order.settlement_term_fee_amount or 0)
        + order_freight_amount(order)
        + order.weight_adjustment_amount
    )
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
        if order.payment_method == StorePaymentMethod.SATNA_OFFLINE:
            from offline_payments.services import initiate_store_order_payment

            initiate_store_order_payment(order, order.buyer)
        else:
            generate_payment_link(order, actor=actor)
    return order


def normalize_quote_loading_points(loading_points):
    if not loading_points:
        return []
    if not isinstance(loading_points, list):
        raise ValueError("quote_loading_points_must_be_list")
    normalized = []
    for raw in loading_points:
        if not isinstance(raw, dict):
            raise ValueError("invalid_quote_loading_point")
        item_id = raw.get("item_id")
        if not item_id:
            continue
        point = {
            "item_id": int(item_id),
            "province": _clean_text(raw.get("province") or raw.get("loading_province")),
            "city": _clean_text(raw.get("city") or raw.get("loading_city")),
            "place_type": _clean_text(raw.get("place_type") or raw.get("loading_place_type")),
            "address": _clean_text(raw.get("address") or raw.get("loading_address")),
            "freight_amount": _money_int(raw.get("freight_amount")),
            "note": _clean_text(raw.get("note") or raw.get("loading_note")),
        }
        normalized.append(point)
    return normalized


@transaction.atomic
def submit_admin_quote(
    order,
    items_data,
    actor=None,
    price_valid_until=None,
    payment_due_at=None,
    loading_points=None,
    multi_loading=False,
    freight_amount=None,
    freight_note="",
):
    items_by_id = {item.id: item for item in order.items.all()}
    if not items_data:
        raise ValueError("quote_items_required")
    now = timezone.now()
    normalized_loading_points = normalize_quote_loading_points(loading_points)
    loading_points_by_item_id = {point["item_id"]: point for point in normalized_loading_points}
    changed = []
    for item_data in items_data:
        item_id = int(item_data["item_id"])
        if item_id not in items_by_id:
            raise ValueError("order_item_not_found")
        item = items_by_id[item_id]
        unit_price = int(item_data["unit_price_amount"])
        price_basis = normalize_price_basis(item_data.get("price_basis") or item.price_basis or PricingBasis.KG)
        if item_data.get("estimated_weight_kg") is not None:
            item.price_weight_kg = Decimal(str(item_data["estimated_weight_kg"])).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            item.estimated_weight_kg = item.price_weight_kg
        total_price = item_data.get("total_price_amount")
        force_total_price = bool(item_data.get("force_total_price"))
        if not force_total_price or total_price in ("", None):
            total_price = money_for_basis(
                unit_price,
                price_basis,
                weight_kg=item.price_weight_kg,
                quantity=item.quantity,
                quantity_unit=item.quantity_unit,
            )
        if total_price is None:
            raise ValueError("quote_item_total_unavailable")
        item.unit_price_amount = unit_price
        item.price_basis = price_basis
        item.total_price_amount = int(total_price)
        details = dict(item.selection_details or {})
        details["quote_unit_price_amount"] = unit_price
        details["quote_price_basis"] = price_basis
        item.selection_details = details
        loading_point = loading_points_by_item_id.get(item.id)
        if loading_point:
            delivery = dict(item.delivery_snapshot or {})
            delivery.update(
                {
                    "province": loading_point["province"],
                    "city": loading_point["city"],
                    "address": loading_point["address"],
                    "place_type": loading_point["place_type"],
                    "freight_amount": loading_point["freight_amount"],
                    "note": loading_point["note"],
                }
            )
            item.delivery_snapshot = delivery
            details["quote_loading_point"] = loading_point
            item.selection_details = details
        item.save(
            update_fields=[
                "unit_price_amount",
                "price_basis",
                "estimated_weight_kg",
                "price_weight_kg",
                "total_price_amount",
                "delivery_snapshot",
                "selection_details",
            ]
        )
        changed.append(
            {
                "item_id": item.id,
                "unit_price_amount": unit_price,
                "price_basis": price_basis,
                "total_price_amount": int(total_price),
                "loading_point": loading_point or {},
            }
        )

    order.refresh_from_db()
    if hasattr(order, "_prefetched_objects_cache"):
        order._prefetched_objects_cache = {}
    metadata = dict(order.metadata or {})
    quote_metadata = dict(metadata.get("quote") or {})
    freight_total = _money_int(freight_amount)
    if not freight_total and normalized_loading_points:
        freight_total = sum(_money_int(point.get("freight_amount")) for point in normalized_loading_points)
    quote_metadata.update(
        {
            "sent_at": now.isoformat(),
            "multi_loading": bool(multi_loading or len(normalized_loading_points) > 1),
            "freight_amount": freight_total,
            "freight_note": (freight_note or "").strip(),
            "loading_points": normalized_loading_points,
        }
    )
    metadata["quote"] = quote_metadata
    order.metadata = metadata
    subtotal, fee, total, unpriced = recalculated_order_amounts(order)
    if unpriced:
        raise ValueError("quote_items_still_unpriced")
    previous_status = order.status
    order.subtotal_amount = subtotal
    order.settlement_term_fee_amount = fee
    order.total_amount = total
    order.status = StoreOrderStatus.PRICE_CONFIRMED
    order.payment_status = StorePaymentStatus.UNPAID
    order.quote_confirmation_status = StoreQuoteConfirmationStatus.AWAITING_BUYER
    order.quote_rejection_reason = ""
    order.quote_rejection_note = ""
    order.quote_confirmed_at = None
    order.quote_rejected_at = None
    order.price_valid_until = price_valid_until or default_price_valid_until(now)
    order.payment_due_at = payment_due_at or now + timedelta(days=order.settlement_term_days)
    order.payment_link_token = ""
    order.payment_link_url = ""
    order.payment_link_created_at = None
    order.save(
        update_fields=[
            "subtotal_amount",
            "settlement_term_fee_amount",
            "total_amount",
            "status",
            "payment_status",
            "quote_confirmation_status",
            "quote_rejection_reason",
            "quote_rejection_note",
            "quote_confirmed_at",
            "quote_rejected_at",
            "price_valid_until",
            "payment_due_at",
            "payment_link_token",
            "payment_link_url",
            "payment_link_created_at",
            "metadata",
            "updated_at",
        ]
    )
    write_status_history(
        order,
        previous_status,
        order.status,
        "STORE_ORDER_QUOTE_SENT",
        actor,
        meta={
            "items": changed,
            "subtotal_amount": subtotal,
            "settlement_term_fee_amount": fee,
            "freight_amount": freight_total,
            "total_amount": total,
            "price_valid_until": order.price_valid_until.isoformat() if order.price_valid_until else None,
            "payment_due_at": order.payment_due_at.isoformat() if order.payment_due_at else None,
        },
    )
    return order


@transaction.atomic
def confirm_store_order_quote(order, actor=None):
    if order.quote_confirmation_status != StoreQuoteConfirmationStatus.AWAITING_BUYER:
        raise ValueError("quote_is_not_waiting_for_buyer")
    _subtotal, _fee, _total, unpriced = recalculated_order_amounts(order)
    if unpriced:
        raise ValueError("quote_items_still_unpriced")
    now = timezone.now()
    previous_status = order.status
    order.quote_confirmation_status = StoreQuoteConfirmationStatus.CONFIRMED
    order.quote_confirmed_at = now
    order.status = StoreOrderStatus.PAYMENT_PENDING
    order.payment_status = StorePaymentStatus.PENDING
    if not order.price_valid_until or order.price_valid_until < now:
        order.price_valid_until = default_price_valid_until(now)
    if not order.payment_due_at or order.payment_due_at < now:
        order.payment_due_at = now + timedelta(days=order.settlement_term_days)
    order.save(
        update_fields=[
            "quote_confirmation_status",
            "quote_confirmed_at",
            "status",
            "payment_status",
            "price_valid_until",
            "payment_due_at",
            "updated_at",
        ]
    )
    write_status_history(
        order,
        previous_status,
        order.status,
        "STORE_ORDER_QUOTE_CONFIRMED_BY_BUYER",
        actor,
        meta={"total_amount": order.total_amount},
    )
    if order.payment_method == StorePaymentMethod.SATNA_OFFLINE:
        from offline_payments.services import initiate_store_order_payment

        initiate_store_order_payment(order, order.buyer)
        return order
    return generate_payment_link(order, actor=actor)


@transaction.atomic
def reject_store_order_quote(order, reason, actor=None, note=""):
    if order.quote_confirmation_status != StoreQuoteConfirmationStatus.AWAITING_BUYER:
        raise ValueError("quote_is_not_waiting_for_buyer")
    reason = (reason or "").strip()
    note = (note or "").strip()
    if not reason and not note:
        raise ValueError("quote_rejection_reason_required")
    previous_status = order.status
    order.quote_confirmation_status = StoreQuoteConfirmationStatus.REJECTED
    order.quote_rejection_reason = reason
    order.quote_rejection_note = note
    order.quote_rejected_at = timezone.now()
    order.status = StoreOrderStatus.QUOTE_REQUESTED
    order.payment_status = StorePaymentStatus.UNPAID
    order.payment_link_token = ""
    order.payment_link_url = ""
    order.payment_link_created_at = None
    order.save(
        update_fields=[
            "quote_confirmation_status",
            "quote_rejection_reason",
            "quote_rejection_note",
            "quote_rejected_at",
            "status",
            "payment_status",
            "payment_link_token",
            "payment_link_url",
            "payment_link_created_at",
            "updated_at",
        ]
    )
    write_status_history(
        order,
        previous_status,
        order.status,
        "STORE_ORDER_QUOTE_REJECTED_BY_BUYER",
        actor,
        meta={"reason": reason, "note": note},
    )
    return order


MAX_DRIVER_LOAD_KG = Decimal("25000.000")
DEFAULT_DELIVERY_OFFER_TTL_MINUTES = 30
DEFAULT_DELIVERY_SEARCH_RADIUS_KM = 150
DEFAULT_DELIVERY_CANDIDATE_BUFFER = 2
LOGISTICS_ROLE_CODES = {
    RoleCode.DRIVER,
    RoleCode.CARRIER,
}

DELIVERY_ASSIGNMENT_TRANSITIONS = {
    StoreDeliveryAssignmentStatus.ACCEPTED: {StoreDeliveryAssignmentStatus.ARRIVED_FOR_LOADING},
    StoreDeliveryAssignmentStatus.ARRIVED_FOR_LOADING: {StoreDeliveryAssignmentStatus.LOADED},
    StoreDeliveryAssignmentStatus.LOADED: {StoreDeliveryAssignmentStatus.IN_TRANSIT},
    StoreDeliveryAssignmentStatus.IN_TRANSIT: {StoreDeliveryAssignmentStatus.DELIVERED},
    StoreDeliveryAssignmentStatus.DELIVERED: {StoreDeliveryAssignmentStatus.PROOF_SUBMITTED},
}

DELIVERY_ASSIGNMENT_TIMESTAMP_FIELDS = {
    StoreDeliveryAssignmentStatus.ACCEPTED: "accepted_at",
    StoreDeliveryAssignmentStatus.ARRIVED_FOR_LOADING: "arrived_for_loading_at",
    StoreDeliveryAssignmentStatus.LOADED: "loaded_at",
    StoreDeliveryAssignmentStatus.IN_TRANSIT: "in_transit_at",
    StoreDeliveryAssignmentStatus.DELIVERED: "delivered_at",
    StoreDeliveryAssignmentStatus.PROOF_SUBMITTED: "proof_submitted_at",
}


def delivery_weight_kg_for_order(order):
    weight = Decimal("0")
    for item in order.items.all():
        item_weight = item.final_weight_kg if item.final_weight_kg is not None else item.estimated_weight_kg
        if item_weight is not None:
            weight += Decimal(str(item_weight))
    return weight.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def required_driver_count_for_weight(weight_kg):
    weight = Decimal(str(weight_kg or 0))
    if weight <= 0:
        return 0
    return int((weight / MAX_DRIVER_LOAD_KG).to_integral_value(rounding=ROUND_CEILING))


def decimal_or_none(value):
    if value in (None, ""):
        return None
    return Decimal(str(value))


def mirror_first_loading_vehicle(order):
    """اولین خودرو active را به فیلدهای legacy سفارش منعکس می‌کند."""
    first = order.loading_vehicles.filter(is_active=True).order_by("sequence", "id").first()
    order.driver_name = first.driver_name if first else ""
    order.driver_phone = first.driver_phone if first else ""
    order.vehicle_type = first.vehicle_type if first else ""
    order.vehicle_plate = first.vehicle_plate if first else ""
    order.save(update_fields=["driver_name", "driver_phone", "vehicle_type", "vehicle_plate", "updated_at"])


def normalized_positive_int(value, default=0, maximum=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = int(default)
    result = max(0, result)
    if maximum is not None:
        result = min(result, maximum)
    return result


def normalize_delivery_recipient_type(value):
    value = (value or StoreDeliveryRecipientType.ALL).strip().upper()
    valid_values = {choice[0] for choice in StoreDeliveryRecipientType.choices}
    return value if value in valid_values else StoreDeliveryRecipientType.ALL


def role_codes_for_recipient_type(recipient_type):
    recipient_type = normalize_delivery_recipient_type(recipient_type)
    if recipient_type == StoreDeliveryRecipientType.DRIVER:
        return {RoleCode.DRIVER}
    if recipient_type == StoreDeliveryRecipientType.CARRIER:
        return {RoleCode.CARRIER}
    return LOGISTICS_ROLE_CODES


def recipient_type_for_role(role):
    return StoreDeliveryRecipientType.CARRIER if role.role == RoleCode.CARRIER else StoreDeliveryRecipientType.DRIVER


def active_logistics_roles(recipient_ids=None, recipient_type=StoreDeliveryRecipientType.ALL):
    roles = UserRole.objects.filter(
        role__in=role_codes_for_recipient_type(recipient_type),
        is_active=True,
    ).select_related(
        "user",
        "user__profile",
        "user__store_driver_profile",
    )
    if recipient_ids:
        roles = roles.filter(user_id__in=recipient_ids)
    unique_roles = {}
    for role in roles.order_by("user__username", "user_id", "role"):
        unique_roles.setdefault(role.user_id, role)
    return list(unique_roles.values())


def active_driver_roles(driver_ids=None):
    return active_logistics_roles(driver_ids, recipient_type=StoreDeliveryRecipientType.DRIVER)


def active_driver_users(driver_ids=None):
    return [role.user for role in active_driver_roles(driver_ids)]


def ensure_driver_operational_profile(user):
    profile, _created = StoreDriverOperationalProfile.objects.get_or_create(user=user)
    return profile


def haversine_distance_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return Decimal(str(6371 * 2 * asin(sqrt(a)))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _location_value(mapping, *keys):
    if not isinstance(mapping, dict):
        return ""
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return ""


def resolve_delivery_loading_location(order, payload=None):
    payload = payload or {}
    quote = order.metadata.get("quote") if isinstance(order.metadata, dict) else {}
    loading_points = quote.get("loading_points") if isinstance(quote, dict) and isinstance(quote.get("loading_points"), list) else []
    first_point = loading_points[0] if loading_points else {}
    if not first_point:
        first_item = order.items.first()
        first_point = first_item.delivery_snapshot if first_item and isinstance(first_item.delivery_snapshot, dict) else {}
    province = (payload.get("pickup_province") or _location_value(first_point, "province", "pickup_province") or "").strip()
    city = (payload.get("pickup_city") or _location_value(first_point, "city", "pickup_city") or "").strip()
    address = (payload.get("pickup_address") or _location_value(first_point, "address", "pickup_address") or "").strip()
    latitude = decimal_or_none(payload.get("pickup_latitude") or _location_value(first_point, "latitude", "lat", "pickup_latitude"))
    longitude = decimal_or_none(payload.get("pickup_longitude") or _location_value(first_point, "longitude", "lng", "lon", "pickup_longitude"))
    return {
        "province": province,
        "city": city,
        "address": address,
        "latitude": latitude,
        "longitude": longitude,
    }


def resolve_delivery_destination(order, payload=None):
    payload = payload or {}
    return {
        "province": (payload.get("destination_province") or order.destination_province or "").strip(),
        "city": (payload.get("destination_city") or order.destination_city or "").strip(),
        "address": (payload.get("destination_address") or order.destination_address or "").strip(),
        "latitude": decimal_or_none(
            payload.get("destination_latitude")
            if payload.get("destination_latitude") not in (None, "")
            else order.destination_latitude
        ),
        "longitude": decimal_or_none(
            payload.get("destination_longitude")
            if payload.get("destination_longitude") not in (None, "")
            else order.destination_longitude
        ),
        "delivery_notes": order.delivery_notes or "",
    }


def sync_order_delivery_destination(order, destination):
    update_fields = []
    field_map = {
        "destination_province": destination.get("province") or "",
        "destination_city": destination.get("city") or "",
        "destination_address": destination.get("address") or "",
        "destination_latitude": destination.get("latitude"),
        "destination_longitude": destination.get("longitude"),
    }
    for field, value in field_map.items():
        if getattr(order, field) != value:
            setattr(order, field, value)
            update_fields.append(field)
    if update_fields:
        order.save(update_fields=[*update_fields, "updated_at"])


def delivery_request_location(request_obj):
    return {
        "province": request_obj.pickup_province,
        "city": request_obj.pickup_city,
        "address": request_obj.pickup_address,
        "latitude": request_obj.pickup_latitude,
        "longitude": request_obj.pickup_longitude,
    }


def is_profile_geo_match(profile, location, search_radius_km):
    pickup_lat = location.get("latitude")
    pickup_lng = location.get("longitude")
    if pickup_lat is not None and pickup_lng is not None and profile.current_latitude is not None and profile.current_longitude is not None:
        distance = haversine_distance_km(pickup_lat, pickup_lng, profile.current_latitude, profile.current_longitude)
        request_radius = normalized_positive_int(search_radius_km, DEFAULT_DELIVERY_SEARCH_RADIUS_KM) or DEFAULT_DELIVERY_SEARCH_RADIUS_KM
        driver_radius = normalized_positive_int(profile.service_radius_km, DEFAULT_DELIVERY_SEARCH_RADIUS_KM) or DEFAULT_DELIVERY_SEARCH_RADIUS_KM
        if distance <= min(Decimal(request_radius), Decimal(driver_radius)):
            return True, distance, "coordinate_radius"
        return False, distance, "outside_radius"

    pickup_city = (location.get("city") or "").strip()
    pickup_province = (location.get("province") or "").strip()
    if pickup_city and profile.current_city and pickup_city == profile.current_city:
        return True, None, "city_match"
    if pickup_province and profile.current_province and pickup_province == profile.current_province:
        return True, None, "province_match"
    if not pickup_city and not pickup_province and pickup_lat is None and pickup_lng is None:
        return True, None, "no_pickup_location"
    return False, None, "location_mismatch"


def driver_match_payload(role, profile, location, search_radius_km, manual=False, rank=None):
    distance = None
    reason = "manual"
    eligible = True
    if profile:
        eligible, distance, reason = is_profile_geo_match(profile, location, search_radius_km)
    elif not manual:
        eligible = False
        reason = "profile_missing"
    return {
        "user": role.user,
        "recipient_type": recipient_type_for_role(role),
        "profile": profile,
        "eligible": eligible,
        "distance_km": distance,
        "match_reason": reason,
        "match_rank": rank,
    }


def match_delivery_drivers(
    *,
    order=None,
    request_obj=None,
    driver_ids=None,
    recipient_type=StoreDeliveryRecipientType.ALL,
    exclude_driver_ids=None,
    total_weight_kg=None,
    required_driver_count=None,
    limit=None,
    location=None,
    search_radius_km=None,
    manual=False,
):
    if request_obj is not None:
        order = request_obj.order
        location = location or delivery_request_location(request_obj)
        search_radius_km = search_radius_km if search_radius_km is not None else request_obj.search_radius_km
        total_weight_kg = total_weight_kg if total_weight_kg is not None else request_obj.total_weight_kg
        required_driver_count = required_driver_count if required_driver_count is not None else request_obj.required_driver_count
    if order is not None and location is None:
        location = resolve_delivery_loading_location(order)
    location = location or {}
    search_radius_km = normalized_positive_int(search_radius_km, DEFAULT_DELIVERY_SEARCH_RADIUS_KM) or DEFAULT_DELIVERY_SEARCH_RADIUS_KM
    total_weight_kg = Decimal(str(total_weight_kg or 0))
    required_driver_count = int(required_driver_count or required_driver_count_for_weight(total_weight_kg))
    planned_capacity = min(MAX_DRIVER_LOAD_KG, total_weight_kg) if total_weight_kg > 0 else MAX_DRIVER_LOAD_KG
    exclude_driver_ids = set(exclude_driver_ids or [])
    recipient_type = normalize_delivery_recipient_type(recipient_type)
    roles = active_logistics_roles(driver_ids, recipient_type=recipient_type)
    matches = []

    for role in roles:
        if role.user_id in exclude_driver_ids:
            continue
        profile = getattr(role.user, "store_driver_profile", None)
        if manual:
            match = driver_match_payload(role, profile, location, search_radius_km, manual=True)
            match["eligible"] = True
            matches.append(match)
            continue
        if not profile:
            continue
        if not profile.is_verified or not profile.is_available:
            continue
        if Decimal(str(profile.capacity_kg or 0)) < planned_capacity:
            continue
        match = driver_match_payload(role, profile, location, search_radius_km)
        if match["eligible"]:
            matches.append(match)

    matches.sort(
        key=lambda item: (
            item["distance_km"] is None,
            item["distance_km"] if item["distance_km"] is not None else Decimal("999999"),
            item["user"].username,
            item["user"].id,
        )
    )
    default_limit = required_driver_count + DEFAULT_DELIVERY_CANDIDATE_BUFFER if not manual else len(matches)
    limit = normalized_positive_int(limit, default_limit) or default_limit
    selected = matches[:limit]
    for index, match in enumerate(selected, start=1):
        match["match_rank"] = index
    return selected


def delivery_request_blockers(order):
    blockers = []
    if order.status in TERMINAL_STATUSES:
        blockers.append("terminal_order_status")
    if order.risk_status == StoreRiskStatus.BLOCKED:
        blockers.append("risk_blocked")
    if is_order_price_expired(order):
        blockers.append("price_expired")
    if order.quote_confirmation_status in {
        StoreQuoteConfirmationStatus.AWAITING_ADMIN_QUOTE,
        StoreQuoteConfirmationStatus.AWAITING_BUYER,
    }:
        blockers.append("quote_not_confirmed")
    if order.quote_confirmation_status == StoreQuoteConfirmationStatus.REJECTED:
        blockers.append("quote_rejected_by_buyer")
    weight = delivery_weight_kg_for_order(order)
    if weight <= 0:
        blockers.append("shipment_weight_missing")
    active_exists = order.delivery_requests.exclude(
        status__in=[StoreDeliveryRequestStatus.CANCELLED, StoreDeliveryRequestStatus.COMPLETED]
    ).exists()
    if active_exists:
        blockers.append("active_delivery_request_exists")
    return blockers


def _first_order_item_title(order):
    first_item = order.items.first()
    return first_item.product_name if first_item else str(order.id)


def delivery_shipment_snapshot(order, total_weight_kg, required_driver_count, loading_location=None, destination=None):
    quote = order.metadata.get("quote") if isinstance(order.metadata, dict) else {}
    loading_points = quote.get("loading_points") if isinstance(quote, dict) and isinstance(quote.get("loading_points"), list) else []
    loading_location = loading_location or resolve_delivery_loading_location(order)
    destination = destination or resolve_delivery_destination(order)
    items = []
    item_loading_points = {int(point.get("item_id")): point for point in loading_points if point.get("item_id")}
    for item in order.items.all():
        item_weight = item.final_weight_kg if item.final_weight_kg is not None else item.estimated_weight_kg
        loading_point = item_loading_points.get(item.id) or item.delivery_snapshot or {}
        items.append(
            {
                "id": item.id,
                "product_name": item.product_name,
                "quantity": str(item.quantity),
                "quantity_unit": item.quantity_unit,
                "estimated_weight_kg": str(item.estimated_weight_kg or ""),
                "final_weight_kg": str(item.final_weight_kg or ""),
                "planned_weight_kg": str(item_weight or ""),
                "loading_point": loading_point,
            }
        )
    return {
        "order_id": str(order.id),
        "order_title": _first_order_item_title(order),
        "buyer_username": order.buyer.username,
        "contact_name": order.contact_name,
        "contact_phone": order.contact_phone,
        "destination": {
            "province": destination.get("province") or "",
            "city": destination.get("city") or "",
            "address": destination.get("address") or "",
            "latitude": str(destination.get("latitude") or ""),
            "longitude": str(destination.get("longitude") or ""),
            "delivery_notes": destination.get("delivery_notes") or "",
        },
        "total_amount": order.total_amount,
        "currency": order.currency,
        "total_weight_kg": str(total_weight_kg),
        "required_driver_count": required_driver_count,
        "per_driver_weight_limit_kg": str(MAX_DRIVER_LOAD_KG),
        "items": items,
        "loading_points": loading_points,
        "pickup": {
            "province": loading_location.get("province") or "",
            "city": loading_location.get("city") or "",
            "address": loading_location.get("address") or "",
            "latitude": str(loading_location.get("latitude") or ""),
            "longitude": str(loading_location.get("longitude") or ""),
        },
    }


def write_delivery_event(request_obj, event, actor=None, assignment=None, from_status="", to_status="", payload=None):
    return StoreDeliveryEvent.objects.create(
        request=request_obj,
        assignment=assignment,
        actor_user=actor if getattr(actor, "is_authenticated", False) else None,
        event=event,
        from_status=from_status or "",
        to_status=to_status or "",
        payload=payload or {},
    )


def delivery_offer_expiry(offer_ttl_minutes, now=None):
    now = now or timezone.now()
    ttl = normalized_positive_int(offer_ttl_minutes, DEFAULT_DELIVERY_OFFER_TTL_MINUTES, maximum=1440)
    if ttl <= 0:
        ttl = DEFAULT_DELIVERY_OFFER_TTL_MINUTES
    return now + timedelta(minutes=ttl)


def notify_delivery_offer(offer, actor=None):
    driver = offer.driver
    profile_phone = getattr(getattr(driver, "profile", None), "phone", "") or ""
    recipient = driver.email or profile_phone or driver.username
    notification = StoreOrderNotification.objects.create(
        order=offer.request.order,
        channel=StoreNotificationChannel.MANUAL,
        recipient=recipient,
        event="DELIVERY_LOAD_OFFERED",
        status=StoreNotificationStatus.SENT,
        actor_user=actor if getattr(actor, "is_authenticated", False) else None,
        payload={
            "delivery_request_id": str(offer.request_id),
            "offer_id": str(offer.id),
            "driver_id": offer.driver_id,
            "recipient_type": offer.recipient_type,
            "expires_at": offer.expires_at.isoformat() if offer.expires_at else None,
            "distance_km": str(offer.distance_km or ""),
            "match_rank": offer.match_rank,
            "match_reason": offer.match_reason,
        },
    )
    offer.notified_at = timezone.now()
    offer.notification_status = StoreNotificationStatus.SENT
    offer.save(update_fields=["notified_at", "notification_status", "updated_at"])
    return notification


def create_delivery_offers_for_matches(request_obj, matches, actor=None, event="DELIVERY_OFFERS_CREATED"):
    created = []
    now = timezone.now()
    expires_at = delivery_offer_expiry(request_obj.offer_ttl_minutes, now=now)
    for match in matches:
        offer, is_created = StoreDeliveryOffer.objects.get_or_create(
            request=request_obj,
            driver=match["user"],
            defaults={
                "expires_at": expires_at,
                "recipient_type": match.get("recipient_type") or StoreDeliveryRecipientType.DRIVER,
                "distance_km": match.get("distance_km"),
                "match_rank": match.get("match_rank"),
                "match_reason": match.get("match_reason", ""),
            },
        )
        if not is_created:
            continue
        notify_delivery_offer(offer, actor=actor)
        write_delivery_event(
            request_obj,
            event,
            actor,
            payload={
                "offer_id": str(offer.id),
                "driver_id": offer.driver_id,
                "recipient_type": offer.recipient_type,
                "distance_km": str(offer.distance_km or ""),
                "match_rank": offer.match_rank,
                "match_reason": offer.match_reason,
                "expires_at": offer.expires_at.isoformat() if offer.expires_at else None,
            },
        )
        created.append(offer)
    return created


@transaction.atomic
def create_delivery_request(order, actor, driver_ids=None, **payload):
    order = StoreOrder.objects.select_for_update().prefetch_related("items", "delivery_requests").get(pk=order.pk)
    blockers = delivery_request_blockers(order)
    if blockers:
        raise ValueError(f"delivery_blockers:{','.join(blockers)}")

    total_weight_kg = delivery_weight_kg_for_order(order)
    required_driver_count = required_driver_count_for_weight(total_weight_kg)
    loading_location = resolve_delivery_loading_location(order, payload)
    destination = resolve_delivery_destination(order, payload)
    sync_order_delivery_destination(order, destination)
    recipient_type = normalize_delivery_recipient_type(payload.get("recipient_type"))
    search_radius_km = normalized_positive_int(payload.get("search_radius_km"), DEFAULT_DELIVERY_SEARCH_RADIUS_KM) or DEFAULT_DELIVERY_SEARCH_RADIUS_KM
    offer_ttl_minutes = normalized_positive_int(payload.get("offer_ttl_minutes"), DEFAULT_DELIVERY_OFFER_TTL_MINUTES, maximum=1440)
    if offer_ttl_minutes <= 0:
        offer_ttl_minutes = DEFAULT_DELIVERY_OFFER_TTL_MINUTES
    max_candidate_count = normalized_positive_int(payload.get("max_candidate_count"), 0, maximum=100)
    manual = bool(driver_ids)
    matches = match_delivery_drivers(
        order=order,
        driver_ids=driver_ids,
        total_weight_kg=total_weight_kg,
        required_driver_count=required_driver_count,
        location=loading_location,
        search_radius_km=search_radius_km,
        limit=max_candidate_count or None,
        manual=manual,
        recipient_type=recipient_type,
    )
    if len(matches) < required_driver_count:
        raise ValueError("not_enough_active_drivers")

    request_obj = StoreDeliveryRequest.objects.create(
        order=order,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        total_weight_kg=total_weight_kg,
        required_driver_count=required_driver_count,
        per_driver_weight_limit_kg=MAX_DRIVER_LOAD_KG,
        recipient_type=recipient_type,
        vehicle_type=(payload.get("vehicle_type") or "").strip(),
        pickup_province=loading_location.get("province") or "",
        pickup_city=loading_location.get("city") or "",
        pickup_address=loading_location.get("address") or "",
        pickup_latitude=loading_location.get("latitude"),
        pickup_longitude=loading_location.get("longitude"),
        destination_province=destination.get("province") or "",
        destination_city=destination.get("city") or "",
        destination_address=destination.get("address") or "",
        destination_latitude=destination.get("latitude"),
        destination_longitude=destination.get("longitude"),
        search_radius_km=search_radius_km,
        offer_ttl_minutes=offer_ttl_minutes,
        auto_reassign_enabled=bool(payload.get("auto_reassign_enabled", True)),
        max_candidate_count=max_candidate_count,
        pickup_window_start=payload.get("pickup_window_start"),
        pickup_window_end=payload.get("pickup_window_end"),
        dispatch_deadline=payload.get("dispatch_deadline"),
        pickup_notes=(payload.get("pickup_notes") or "").strip(),
        dispatcher_notes=(payload.get("dispatcher_notes") or "").strip(),
        shipment_snapshot=delivery_shipment_snapshot(
            order,
            total_weight_kg,
            required_driver_count,
            loading_location=loading_location,
            destination=destination,
        ),
        metadata=payload.get("metadata") or {},
    )
    created_offers = create_delivery_offers_for_matches(request_obj, matches, actor=actor, event="DELIVERY_REQUEST_OFFERED")
    write_delivery_event(
        request_obj,
        "DELIVERY_REQUEST_PUBLISHED",
        actor,
        payload={
            "driver_count": len(created_offers),
            "required_driver_count": required_driver_count,
            "total_weight_kg": str(total_weight_kg),
            "search_radius_km": search_radius_km,
            "auto_matched": not manual,
            "recipient_type": recipient_type,
        },
    )
    if order.status not in LOADING_STATUSES | {StoreOrderStatus.FULFILLMENT_PENDING}:
        set_order_status(
            order,
            StoreOrderStatus.FULFILLMENT_PENDING,
            "STORE_ORDER_DELIVERY_REQUESTED",
            actor,
            meta={"delivery_request_id": str(request_obj.id), "recipient_type": recipient_type},
        )
    return request_obj


def planned_weight_for_sequence(total_weight_kg, sequence):
    remaining_before = Decimal(str(total_weight_kg)) - (MAX_DRIVER_LOAD_KG * Decimal(sequence - 1))
    return min(MAX_DRIVER_LOAD_KG, max(Decimal("0"), remaining_before)).quantize(Decimal("0.001"))


def accepted_driver_count_for_request(request_obj):
    return request_obj.assignments.exclude(status=StoreDeliveryAssignmentStatus.CANCELLED).count()


def remaining_driver_slots(request_obj):
    return max(0, int(request_obj.required_driver_count or 0) - accepted_driver_count_for_request(request_obj))


def offered_driver_ids_for_request(request_obj):
    return set(request_obj.offers.values_list("driver_id", flat=True))


@transaction.atomic
def reassign_delivery_request(request_obj, actor=None, reason="manual", driver_ids=None):
    request_obj = (
        StoreDeliveryRequest.objects.select_for_update()
        .select_related("order", "order__buyer")
        .prefetch_related("order__items", "offers", "assignments")
        .get(pk=request_obj.pk)
    )
    if request_obj.status in {StoreDeliveryRequestStatus.CANCELLED, StoreDeliveryRequestStatus.COMPLETED}:
        return []
    needed = remaining_driver_slots(request_obj)
    if needed <= 0:
        return []
    manual = bool(driver_ids)
    if not manual and not request_obj.auto_reassign_enabled:
        return []
    matches = match_delivery_drivers(
        request_obj=request_obj,
        driver_ids=driver_ids,
        exclude_driver_ids=offered_driver_ids_for_request(request_obj),
        limit=needed if not manual else None,
        manual=manual,
        recipient_type=request_obj.recipient_type,
    )
    created = create_delivery_offers_for_matches(
        request_obj,
        matches,
        actor=actor,
        event="DELIVERY_OFFER_REASSIGNED",
    )
    if created:
        write_delivery_event(
            request_obj,
            "DELIVERY_REQUEST_REASSIGNED",
            actor,
            payload={
                "reason": reason,
                "created_offer_ids": [str(offer.id) for offer in created],
                "needed_driver_count": needed,
            },
        )
    return created


@transaction.atomic
def expire_delivery_offer(offer, now=None, actor=None, reassign=True):
    now = now or timezone.now()
    offer = StoreDeliveryOffer.objects.select_for_update().select_related("request", "request__order", "driver").get(pk=offer.pk)
    if offer.status != StoreDeliveryOfferStatus.OFFERED:
        return False
    if offer.expires_at and offer.expires_at > now:
        return False
    offer.status = StoreDeliveryOfferStatus.EXPIRED
    offer.responded_at = now
    offer.save(update_fields=["status", "responded_at", "updated_at"])
    write_delivery_event(
        offer.request,
        "DELIVERY_OFFER_EXPIRED",
        actor,
        payload={"offer_id": str(offer.id), "driver_id": offer.driver_id, "expires_at": offer.expires_at.isoformat() if offer.expires_at else None},
    )
    if reassign:
        reassign_delivery_request(offer.request, actor=actor, reason="expired")
    return True


@transaction.atomic
def expire_due_delivery_offers(now=None):
    now = now or timezone.now()
    offers = StoreDeliveryOffer.objects.filter(
        status=StoreDeliveryOfferStatus.OFFERED,
        expires_at__lte=now,
    ).select_related("request", "request__order", "driver")
    expired = 0
    for offer in offers.iterator():
        if expire_delivery_offer(offer, now=now, reassign=True):
            expired += 1
    return {"expired": expired}


def respond_to_delivery_offer(offer, actor, action, note=""):
    initial_offer = StoreDeliveryOffer.objects.select_related("request", "request__order", "driver").get(pk=offer.pk)
    if initial_offer.driver_id != actor.id:
        raise ValueError("offer_not_for_driver")
    if initial_offer.status == StoreDeliveryOfferStatus.OFFERED and initial_offer.expires_at and initial_offer.expires_at <= timezone.now():
        expire_delivery_offer(initial_offer, reassign=True)
        raise ValueError("offer_expired")

    with transaction.atomic():
        offer = (
            StoreDeliveryOffer.objects.select_for_update()
            .select_related("request", "request__order", "driver")
            .get(pk=offer.pk)
        )
        request_obj = StoreDeliveryRequest.objects.select_for_update().get(pk=offer.request_id)
        if offer.driver_id != actor.id:
            raise ValueError("offer_not_for_driver")
        if offer.status != StoreDeliveryOfferStatus.OFFERED:
            raise ValueError("offer_not_open")
        if offer.expires_at and offer.expires_at <= timezone.now():
            mark_expired_after_commit = True
        else:
            mark_expired_after_commit = False
        if mark_expired_after_commit:
            offer.status = StoreDeliveryOfferStatus.EXPIRED
            offer.responded_at = timezone.now()
            offer.save(update_fields=["status", "responded_at", "updated_at"])
            write_delivery_event(
                request_obj,
                "DELIVERY_OFFER_EXPIRED",
                actor,
                payload={"offer_id": str(offer.id), "driver_id": offer.driver_id, "expires_at": offer.expires_at.isoformat() if offer.expires_at else None},
            )
            transaction.on_commit(lambda: reassign_delivery_request(request_obj, actor=actor, reason="expired"))
            expired = True
            assignment = None
        elif request_obj.status in {StoreDeliveryRequestStatus.CANCELLED, StoreDeliveryRequestStatus.COMPLETED}:
            raise ValueError("delivery_request_closed")
        else:
            now = timezone.now()
            note = (note or "").strip()
            if action == "decline":
                offer.status = StoreDeliveryOfferStatus.DECLINED
                offer.response_note = note
                offer.responded_at = now
                offer.save(update_fields=["status", "response_note", "responded_at", "updated_at"])
                write_delivery_event(request_obj, "DELIVERY_OFFER_DECLINED", actor, payload={"offer_id": str(offer.id), "note": note})
                transaction.on_commit(lambda: reassign_delivery_request(request_obj, actor=actor, reason="declined"))
                expired = False
                assignment = None
            else:
                if action != "accept":
                    raise ValueError("invalid_offer_action")
                accepted_count = accepted_driver_count_for_request(request_obj)
                if accepted_count >= request_obj.required_driver_count:
                    raise ValueError("delivery_capacity_full")
                sequence = accepted_count + 1
                assignment = StoreDeliveryAssignment.objects.create(
                    request=request_obj,
                    offer=offer,
                    order=request_obj.order,
                    driver=actor,
                    recipient_type=offer.recipient_type,
                    status=StoreDeliveryAssignmentStatus.ACCEPTED,
                    load_sequence=sequence,
                    planned_weight_kg=planned_weight_for_sequence(request_obj.total_weight_kg, sequence),
                    vehicle_type=request_obj.vehicle_type,
                    driver_phone=getattr(getattr(actor, "profile", None), "phone", "") or "",
                    accepted_at=now,
                )
                offer.status = StoreDeliveryOfferStatus.ACCEPTED
                offer.response_note = note
                offer.responded_at = now
                offer.save(update_fields=["status", "response_note", "responded_at", "updated_at"])
                request_obj.accepted_driver_count = accepted_count + 1
                request_obj.status = (
                    StoreDeliveryRequestStatus.ASSIGNED
                    if request_obj.accepted_driver_count >= request_obj.required_driver_count
                    else StoreDeliveryRequestStatus.PUBLISHED
                )
                request_obj.save(update_fields=["accepted_driver_count", "status", "updated_at"])
                write_delivery_event(
                    request_obj,
                    "DELIVERY_OFFER_ACCEPTED",
                    actor,
                    assignment=assignment,
                    to_status=assignment.status,
                    payload={"offer_id": str(offer.id), "planned_weight_kg": str(assignment.planned_weight_kg)},
                )
                expired = False

    if expired:
        raise ValueError("offer_expired")
    return assignment


def validate_delivery_file(file):
    extension = Path(getattr(file, "name", "")).suffix.lower()
    allowed = {".jpg", ".jpeg", ".png", ".pdf", ".zip"}
    if extension not in allowed:
        raise ValueError("invalid_delivery_document_extension")
    max_mb = int(getattr(settings, "STORE_DELIVERY_DOCUMENT_MAX_SIZE_MB", 10))
    if file.size > max_mb * 1024 * 1024:
        raise ValueError("delivery_document_too_large")


@transaction.atomic
def transition_delivery_assignment(assignment, actor, target_status, note=""):
    assignment = (
        StoreDeliveryAssignment.objects.select_for_update()
        .select_related("request", "order", "driver")
        .get(pk=assignment.pk)
    )
    if assignment.driver_id != actor.id:
        raise ValueError("assignment_not_for_driver")
    target_status = (target_status or "").strip()
    allowed = DELIVERY_ASSIGNMENT_TRANSITIONS.get(assignment.status, set())
    if target_status not in allowed:
        raise ValueError("invalid_delivery_transition")
    if target_status == StoreDeliveryAssignmentStatus.IN_TRANSIT:
        blockers = risk_blockers_for_order(assignment.order, StoreOrderStatus.SHIPPED)
        if blockers:
            raise ValueError(f"delivery_blockers:{','.join(blockers)}")

    previous = assignment.status
    now = timezone.now()
    assignment.status = target_status
    timestamp_field = DELIVERY_ASSIGNMENT_TIMESTAMP_FIELDS.get(target_status)
    update_fields = ["status", "updated_at"]
    if timestamp_field:
        setattr(assignment, timestamp_field, now)
        update_fields.append(timestamp_field)
    assignment.save(update_fields=update_fields)

    request_obj = assignment.request
    active_statuses = {StoreDeliveryAssignmentStatus.ARRIVED_FOR_LOADING, StoreDeliveryAssignmentStatus.LOADED, StoreDeliveryAssignmentStatus.IN_TRANSIT}
    if target_status == StoreDeliveryAssignmentStatus.PROOF_SUBMITTED and not request_obj.assignments.exclude(
        status=StoreDeliveryAssignmentStatus.PROOF_SUBMITTED
    ).exists():
        request_obj.status = StoreDeliveryRequestStatus.COMPLETED
    elif target_status in active_statuses:
        request_obj.status = StoreDeliveryRequestStatus.IN_PROGRESS
    request_obj.save(update_fields=["status", "updated_at"])

    write_delivery_event(
        request_obj,
        "DELIVERY_ASSIGNMENT_STATUS_CHANGED",
        actor,
        assignment=assignment,
        from_status=previous,
        to_status=target_status,
        payload={"note": (note or "").strip()},
    )
    return assignment


@transaction.atomic
def upload_delivery_document(assignment, actor, file, document_type=StoreDeliveryDocumentType.OTHER, note=""):
    assignment = StoreDeliveryAssignment.objects.select_for_update().select_related("request", "driver").get(pk=assignment.pk)
    if assignment.driver_id != actor.id:
        raise ValueError("assignment_not_for_driver")
    validate_delivery_file(file)
    document = StoreDeliveryDocument.objects.create(
        assignment=assignment,
        document_type=document_type or StoreDeliveryDocumentType.OTHER,
        file=file,
        note=(note or "").strip(),
        uploaded_by=actor,
    )
    write_delivery_event(
        assignment.request,
        "DELIVERY_DOCUMENT_UPLOADED",
        actor,
        assignment=assignment,
        payload={"document_id": document.id, "document_type": document.document_type},
    )
    return document


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
        quantity, quantity_unit, selection_details, forced_weight_kg = normalize_order_item_selection(
            product,
            quantity,
            quantity_unit,
            item_data.get("selection_details") or {},
        )
        tier = None
        if product.availability_status != Product.AVAILABILITY_OUT_OF_STOCK:
            tier = get_available_tier(
                product,
                quantity,
                quantity_unit=quantity_unit,
                offer_id=item_data.get("offer_id"),
                pricing_tier_id=item_data.get("pricing_tier_id"),
            )
        try:
            price_weight_kg = forced_weight_kg or pricing_weight_kg_for_item(product, quantity, quantity_unit, tier=tier)
        except ValueError:
            if quantity_unit == StoreQuantityUnit.SHEET:
                raise
            price_weight_kg = None
        offer = tier.offer if tier else None
        delivery = get_first_delivery(offer)
        unit_price = int(tier.unit_price) if tier else None
        price_basis = normalize_price_basis(tier.price_basis) if tier else ""
        selected_condition_label = pricing_condition_label(tier)
        total_price = (
            money_for_basis(
                unit_price,
                price_basis,
                weight_kg=price_weight_kg,
                quantity=quantity,
                quantity_unit=quantity_unit,
            )
            if unit_price is not None
            else None
        )
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
                price_basis=price_basis,
                selected_condition_label=selected_condition_label,
                total_price_amount=total_price,
                product_snapshot=product_snapshot(product),
                specification_snapshot=specification_snapshot(product),
                delivery_snapshot=delivery_snapshot(delivery),
                selection_details=selection_details,
            )
        )

    final_status = StoreOrderStatus.QUOTE_REQUESTED if needs_quote else StoreOrderStatus.PAYMENT_PENDING
    final_payment_status = StorePaymentStatus.UNPAID if needs_quote else StorePaymentStatus.PENDING
    quote_confirmation_status = (
        StoreQuoteConfirmationStatus.AWAITING_ADMIN_QUOTE if needs_quote else StoreQuoteConfirmationStatus.NOT_REQUIRED
    )
    order.status = final_status
    order.payment_status = final_payment_status
    order.quote_confirmation_status = quote_confirmation_status
    order.subtotal_amount = subtotal
    order.settlement_term_fee_amount = 0 if needs_quote else settlement_fee_for(subtotal, settlement_term_days)
    order.total_amount = subtotal + order.settlement_term_fee_amount
    if not needs_quote:
        order.price_valid_until = default_price_valid_until()
        order.payment_due_at = timezone.now() + timedelta(
            days=settlement_term_days
        )
    order.save(
        update_fields=[
            "status",
            "payment_status",
            "quote_confirmation_status",
            "subtotal_amount",
            "settlement_term_days",
            "settlement_term_fee_amount",
            "total_amount",
            "price_valid_until",
            "payment_due_at",
            "updated_at",
        ]
    )
    if not needs_quote:
        if order.payment_method == StorePaymentMethod.SATNA_OFFLINE:
            from offline_payments.services import initiate_store_order_payment

            initiate_store_order_payment(order, user)
        else:
            generate_payment_link(order, actor=user)
    write_status_history(
        order,
        None,
        final_status,
        "STORE_ORDER_CREATED",
        user,
        meta={"item_count": len(created_items), "needs_quote": needs_quote},
    )

    # خبر به ادمین/گروه پس از ثبتِ موفق (بعد از commit تا داخلِ تراکنش شبکه نزنیم؛ امن).
    def _notify_admin_new_order():
        try:
            from messaging.events import on_order_submitted

            on_order_submitted(order, needs_quote=needs_quote)
        except Exception:  # noqa: BLE001
            pass

    transaction.on_commit(_notify_admin_new_order)
    return order


# ── Freight Cost Calculation (ton-km, مصوبه شورای عالی هماهنگی ترابری) ───────

def get_freight_rate_settings():
    """تنظیمات نرخ حمل را برمی‌گرداند (در صورت نبود، با مقادیر پیش‌فرض سال جاری ساخته می‌شود)."""
    return FreightRateSettings.get_solo()


def freight_vehicle_coefficient(vehicle_type, rate_settings=None):
    rate_settings = rate_settings or get_freight_rate_settings()
    coefficients = rate_settings.vehicle_coefficients if isinstance(rate_settings.vehicle_coefficients, dict) else {}
    key = (vehicle_type or "").strip()
    raw = coefficients.get(key) if key else None
    if raw in (None, ""):
        return Decimal(str(rate_settings.default_vehicle_coefficient))
    try:
        return Decimal(str(raw))
    except Exception:
        return Decimal(str(rate_settings.default_vehicle_coefficient))


def calculate_freight_cost(weight_kg, distance_km, vehicle_type=""):
    """محاسبه کرایه حمل بر اساس روش تن-کیلومتر:

        کرایه خالص = وزن (تن) × مسافت (کیلومتر) × نرخ پایه × ضریب ناوگان
        کرایه نهایی = کرایه خالص + کارمزد (٪) ، با رعایت حداقل کرایه

    نرخ پایه، ضرایب ناوگان، کارمزد و حداقل کرایه از FreightRateSettings خوانده
    می‌شوند تا تغییر سالانه نرخ‌ها (مثلاً برای ۱۴۰۶) نیازی به تغییر کد نداشته باشد.
    """
    rate_settings = get_freight_rate_settings()
    weight_ton = Decimal(str(weight_kg or 0)) / Decimal("1000")
    distance = Decimal(str(distance_km or 0))
    base_rate = Decimal(str(rate_settings.base_rate_toman))
    coefficient = freight_vehicle_coefficient(vehicle_type, rate_settings)
    admin_fee_percent = Decimal(str(rate_settings.admin_fee_percent))
    minimum_amount = Decimal(str(rate_settings.minimum_amount_toman))

    net_amount = weight_ton * distance * base_rate * coefficient
    admin_fee_amount = net_amount * admin_fee_percent / Decimal("100")
    total_amount = net_amount + admin_fee_amount
    minimum_applied = bool(minimum_amount and total_amount < minimum_amount)
    if minimum_applied:
        total_amount = minimum_amount

    cents = Decimal("1")
    return {
        "weight_ton": weight_ton.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
        "distance_km": distance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "base_rate_toman": base_rate.quantize(cents, rounding=ROUND_HALF_UP),
        "vehicle_coefficient": coefficient,
        "admin_fee_percent": admin_fee_percent,
        "net_amount_toman": net_amount.quantize(cents, rounding=ROUND_HALF_UP),
        "admin_fee_toman": admin_fee_amount.quantize(cents, rounding=ROUND_HALF_UP),
        "minimum_amount_toman": minimum_amount.quantize(cents, rounding=ROUND_HALF_UP),
        "minimum_applied": minimum_applied,
        "total_amount_toman": total_amount.quantize(cents, rounding=ROUND_HALF_UP),
        "year_label": rate_settings.year_label,
    }


def freight_distance_km_for_order(order):
    """فاصله مبدأ تا مقصد سفارش را با فرمول هاورساین برآورد می‌کند (در صورت وجود مختصات)."""
    loading = resolve_delivery_loading_location(order)
    destination = resolve_delivery_destination(order)
    return haversine_distance_km(
        loading.get("latitude"),
        loading.get("longitude"),
        destination.get("latitude"),
        destination.get("longitude"),
    )


# ── Freight Bidding ──────────────────────────────────────────────────────────

def start_freight_bid_session(order, carrier_users, deadline_at, admin_note="", created_by=None):
    """Create a new open bid session and invite all given carriers."""
    with transaction.atomic():
        session = FreightBidSession.objects.create(
            order=order,
            deadline_at=deadline_at,
            admin_note=admin_note,
            created_by=created_by,
        )
        for carrier in carrier_users:
            FreightBidInvite.objects.create(session=session, carrier=carrier)
    return session


def _try_auto_award(session):
    """
    If all non-declined invites have submitted offers, pick the lowest and award.
    Returns True if awarded, False otherwise.
    """
    pending_invites = session.invites.filter(status=FreightBidInviteStatus.INVITED)
    if pending_invites.exists():
        return False
    offers = FreightBidOffer.objects.filter(
        invite__session=session
    ).order_by("amount").select_related("invite")
    if not offers.exists():
        return False
    winner = offers.first()
    session.winner_offer = winner
    session.status = FreightBidStatus.AWARDED
    session.save(update_fields=["winner_offer", "status", "updated_at"])
    return True


def submit_freight_bid_offer(invite, amount, note=""):
    """Carrier submits a price offer for an invite."""
    with transaction.atomic():
        if invite.status != FreightBidInviteStatus.INVITED:
            raise ValueError("invite_not_open")
        if invite.session.status != FreightBidStatus.OPEN:
            raise ValueError("session_not_open")
        offer = FreightBidOffer.objects.create(invite=invite, amount=amount, note=note)
        invite.status = FreightBidInviteStatus.QUOTED
        invite.responded_at = timezone.now()
        invite.save(update_fields=["status", "responded_at"])
        _try_auto_award(invite.session)
    return offer


def decline_freight_bid_invite(invite):
    """Carrier declines an invite."""
    with transaction.atomic():
        if invite.status != FreightBidInviteStatus.INVITED:
            raise ValueError("invite_not_open")
        invite.status = FreightBidInviteStatus.DECLINED
        invite.responded_at = timezone.now()
        invite.save(update_fields=["status", "responded_at"])
        _try_auto_award(invite.session)


def confirm_freight_bid(session):
    """Buyer confirms the awarded freight quote → order moves to FULFILLMENT_PENDING."""
    with transaction.atomic():
        if session.status != FreightBidStatus.AWARDED:
            raise ValueError("session_not_awarded")
        session.status = FreightBidStatus.BUYER_CONFIRMED
        session.save(update_fields=["status", "updated_at"])
        order = session.order
        if order.status == StoreOrderStatus.PAID:
            order.status = StoreOrderStatus.FULFILLMENT_PENDING
            order.save(update_fields=["status", "updated_at"])
            StoreOrderStatusHistory.objects.create(
                order=order,
                from_status=StoreOrderStatus.PAID,
                to_status=StoreOrderStatus.FULFILLMENT_PENDING,
                event="FREIGHT_CONFIRMED",
            )


def reject_freight_bid(session):
    """Buyer rejects the awarded freight quote → session cancelled, order stays PAID."""
    with transaction.atomic():
        if session.status != FreightBidStatus.AWARDED:
            raise ValueError("session_not_awarded")
        session.status = FreightBidStatus.BUYER_REJECTED
        session.save(update_fields=["status", "updated_at"])
