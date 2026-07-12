"""Opportunity transitions and idempotent synchronization from website records."""

import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from .models import (
    CrmOpportunity,
    CrmOpportunityStageHistory,
    CrmSyncEvent,
    Customer,
)
from .services import upsert_lead

logger = logging.getLogger(__name__)


STORE_ORDER_STAGE_MAP = {
    "DRAFT": CrmOpportunity.STAGE_NEW_INQUIRY,
    "SUBMITTED": CrmOpportunity.STAGE_NEW_INQUIRY,
    "QUOTE_REQUESTED": CrmOpportunity.STAGE_PRICING,
    "PRICE_CONFIRMED": CrmOpportunity.STAGE_QUOTE_SENT,
    "PAYMENT_PENDING": CrmOpportunity.STAGE_PAYMENT_PENDING,
    "PAID": CrmOpportunity.STAGE_FULFILLMENT,
    "FULFILLMENT_PENDING": CrmOpportunity.STAGE_FULFILLMENT,
    "READY_FOR_PICKUP": CrmOpportunity.STAGE_FULFILLMENT,
    "SHIPPED": CrmOpportunity.STAGE_FULFILLMENT,
    "DELIVERED": CrmOpportunity.STAGE_WON,
    "COMPLETED": CrmOpportunity.STAGE_WON,
    "CANCELLED": CrmOpportunity.STAGE_LOST,
    "EXPIRED": CrmOpportunity.STAGE_LOST,
}

ASSISTANT_INQUIRY_STAGE_MAP = {
    "new": CrmOpportunity.STAGE_NEW_INQUIRY,
    "contacted": CrmOpportunity.STAGE_QUALIFIED,
    "quoted": CrmOpportunity.STAGE_QUOTE_SENT,
    "won": CrmOpportunity.STAGE_WON,
    "lost": CrmOpportunity.STAGE_LOST,
}


def _authenticated_user(user):
    return user if getattr(user, "is_authenticated", False) else None


def _safe_int(value):
    try:
        return max(0, int(Decimal(str(value or 0))))
    except (InvalidOperation, TypeError, ValueError):
        return 0


def _user_name(user):
    if not user:
        return ""
    full_name = (user.get_full_name() or "").strip()
    return full_name or user.get_username()


def _profile_phone(user):
    profile = getattr(user, "profile", None)
    return (getattr(profile, "phone", "") or "").strip() if profile else ""


def _customer_for_source(*, phone="", name="", user=None, source=Customer.SOURCE_OTHER):
    customer = None
    if phone:
        customer, _created = upsert_lead(phone, name=name, source=source, user=user)
    if not customer and getattr(user, "pk", None):
        customer = Customer.objects.filter(user=user).order_by("-updated_at").first()
    return customer


def _store_order_title(order):
    names = list(order.items.order_by("id").values_list("product_name", flat=True)[:3])
    names = [name.strip() for name in names if (name or "").strip()]
    if names:
        suffix = " و ..." if order.items.count() > len(names) else ""
        return ("سفارش سایت: " + "، ".join(names) + suffix)[:240]
    return f"سفارش سایت #{str(order.pk)[:8]}"


def _assistant_title(inquiry):
    summary = (inquiry.summary or "").strip()
    if summary:
        return f"استعلام سایت: {summary}"[:240]
    raw_text = (inquiry.raw_text or "").strip()
    return (f"استعلام سایت: {raw_text[:210]}" if raw_text else f"استعلام سایت #{inquiry.pk}")[:240]


@transaction.atomic
def transition_opportunity(
    opportunity,
    to_stage,
    *,
    actor=None,
    event="",
    event_key=None,
    reason="",
    metadata=None,
):
    """Move an opportunity and append one idempotent audit row."""

    valid_stages = {code for code, _label in CrmOpportunity.STAGE_CHOICES}
    if to_stage not in valid_stages:
        raise ValueError("invalid_opportunity_stage")

    if event_key:
        previous_event = CrmOpportunityStageHistory.objects.filter(event_key=event_key).first()
        if previous_event:
            return previous_event.opportunity, False

    locked = CrmOpportunity.objects.select_for_update().get(pk=opportunity.pk)
    if event_key:
        previous_event = CrmOpportunityStageHistory.objects.filter(event_key=event_key).first()
        if previous_event:
            return previous_event.opportunity, False

    from_stage = locked.stage
    changed_fields = []
    if from_stage != to_stage:
        locked.stage = to_stage
        changed_fields.append("stage")

    probability = CrmOpportunity.DEFAULT_PROBABILITY[to_stage]
    if locked.probability != probability:
        locked.probability = probability
        changed_fields.append("probability")

    if to_stage in CrmOpportunity.CLOSED_STAGES:
        if not locked.closed_at:
            locked.closed_at = timezone.now()
            changed_fields.append("closed_at")
    elif locked.closed_at:
        locked.closed_at = None
        changed_fields.append("closed_at")

    reason = (reason or "").strip()[:255]
    if to_stage == CrmOpportunity.STAGE_LOST:
        if reason and locked.lost_reason != reason:
            locked.lost_reason = reason
            changed_fields.append("lost_reason")
    elif locked.lost_reason:
        locked.lost_reason = ""
        changed_fields.append("lost_reason")

    if changed_fields:
        locked.save(update_fields=[*changed_fields, "updated_at"])

    CrmOpportunityStageHistory.objects.create(
        opportunity=locked,
        from_stage=from_stage if from_stage != to_stage else from_stage,
        to_stage=to_stage,
        event=(event or "").strip()[:80],
        event_key=event_key or None,
        reason=reason,
        actor_user=_authenticated_user(actor),
        metadata=metadata or {},
    )
    return locked, from_stage != to_stage


def _store_order_event(order):
    latest = order.status_history.select_related("actor_user").order_by("-at", "-id").first()
    if latest and latest.to_status == order.status:
        return (
            latest.event or f"STORE_ORDER_{order.status}",
            f"store_order:{order.pk}:history:{latest.pk}",
            latest.actor_user,
            latest.meta or {},
        )
    updated = order.updated_at.isoformat() if order.updated_at else "unknown"
    return f"STORE_ORDER_{order.status}", f"store_order:{order.pk}:{order.status}:{updated}", None, {}


def sync_store_order_opportunity(order_or_id, *, event_key=None):
    """Project one direct store order into exactly one CRM opportunity."""

    from sales.models import StoreOrder

    order = (
        order_or_id
        if isinstance(order_or_id, StoreOrder)
        else StoreOrder.objects.select_related("buyer").get(pk=order_or_id)
    )
    if not hasattr(order, "buyer"):
        order = StoreOrder.objects.select_related("buyer").get(pk=order.pk)

    stage = STORE_ORDER_STAGE_MAP.get(order.status)
    if not stage:
        raise ValueError(f"unsupported_store_order_status:{order.status}")

    buyer = order.buyer
    phone = (order.contact_phone or "").strip() or _profile_phone(buyer)
    name = (order.contact_name or "").strip() or _user_name(buyer)
    customer = _customer_for_source(
        phone=phone,
        name=name,
        user=buyer,
        source=Customer.SOURCE_STORE_PURCHASE,
    )
    reason = ""
    if stage == CrmOpportunity.STAGE_LOST:
        reason = "لغو سفارش" if order.status == "CANCELLED" else "انقضای سفارش"
    elif order.status == "QUOTE_REQUESTED" and order.quote_rejection_reason:
        reason = order.quote_rejection_reason

    source_event, source_event_key, actor, history_meta = _store_order_event(order)
    event_key = event_key or source_event_key
    metadata = {
        "order_id": str(order.pk),
        "order_status": order.status,
        "payment_status": order.payment_status,
        "quote_confirmation_status": order.quote_confirmation_status,
        "currency": order.currency,
        "destination_city": order.destination_city,
        "destination_province": order.destination_province,
        "history": history_meta,
    }

    with transaction.atomic():
        opportunity, _created = CrmOpportunity.objects.get_or_create(
            source_type=CrmOpportunity.SOURCE_STORE_ORDER,
            source_id=str(order.pk),
            defaults={
                "title": _store_order_title(order),
                "customer": customer,
                "source_status": order.status,
                "expected_value_irr": _safe_int(order.total_amount),
                "probability": CrmOpportunity.DEFAULT_PROBABILITY[CrmOpportunity.STAGE_NEW_INQUIRY],
                "need_details": (order.delivery_notes or "")[:2000],
                "metadata": metadata,
            },
        )
        dirty = []
        values = {
            "title": _store_order_title(order),
            "source_status": order.status,
            "expected_value_irr": _safe_int(order.total_amount),
            "need_details": (order.delivery_notes or "")[:2000],
            "metadata": metadata,
        }
        if customer and opportunity.customer_id != customer.pk:
            values["customer"] = customer
        for field, value in values.items():
            current = getattr(opportunity, f"{field}_id", None) if field == "customer" else getattr(opportunity, field)
            target = value.pk if field == "customer" else value
            if current != target:
                setattr(opportunity, field, value)
                dirty.append(field)
        if dirty:
            opportunity.save(update_fields=[*dirty, "updated_at"])

        opportunity, _changed = transition_opportunity(
            opportunity,
            stage,
            actor=actor,
            event=source_event,
            event_key=event_key,
            reason=reason,
            metadata=metadata,
        )
    return opportunity


def sync_assistant_inquiry_opportunity(inquiry_or_id, *, event_key=None):
    """Project one structured assistant inquiry into exactly one CRM opportunity."""

    from assistant.models import AssistantInquiry

    inquiry = (
        inquiry_or_id
        if isinstance(inquiry_or_id, AssistantInquiry)
        else AssistantInquiry.objects.select_related("conversation__user").get(pk=inquiry_or_id)
    )
    conversation = inquiry.conversation
    user = getattr(conversation, "user", None) if conversation else None
    phone = (inquiry.contact_phone or "").strip() or (
        (getattr(conversation, "lead_phone", "") or "").strip() if conversation else ""
    )
    name = (inquiry.contact_name or "").strip() or (
        (getattr(conversation, "lead_name", "") or "").strip() if conversation else ""
    ) or _user_name(user)
    customer = _customer_for_source(phone=phone, name=name, user=user, source=Customer.SOURCE_CHAT)
    stage = ASSISTANT_INQUIRY_STAGE_MAP.get(inquiry.status, CrmOpportunity.STAGE_NEW_INQUIRY)
    updated = inquiry.updated_at.isoformat() if inquiry.updated_at else "unknown"
    event_key = event_key or f"assistant_inquiry:{inquiry.pk}:{inquiry.status}:{updated}"
    metadata = {
        "inquiry_id": inquiry.pk,
        "inquiry_status": inquiry.status,
        "product": inquiry.product,
        "size": inquiry.size,
        "grade": inquiry.grade,
        "factory": inquiry.factory,
        "quantity": inquiry.quantity,
        "city": inquiry.city,
        "matched_price_toman": _safe_int(inquiry.matched_price),
    }
    # matched_price is a catalog/unit price; without a normalized quantity it is not deal value.
    value_irr = 0

    with transaction.atomic():
        opportunity, _created = CrmOpportunity.objects.get_or_create(
            source_type=CrmOpportunity.SOURCE_ASSISTANT_INQUIRY,
            source_id=str(inquiry.pk),
            defaults={
                "title": _assistant_title(inquiry),
                "customer": customer,
                "source_status": inquiry.status,
                "expected_value_irr": value_irr,
                "probability": CrmOpportunity.DEFAULT_PROBABILITY[CrmOpportunity.STAGE_NEW_INQUIRY],
                "need_details": (inquiry.raw_text or inquiry.note or "")[:2000],
                "metadata": metadata,
            },
        )
        dirty = []
        values = {
            "title": _assistant_title(inquiry),
            "source_status": inquiry.status,
            "expected_value_irr": value_irr,
            "need_details": (inquiry.raw_text or inquiry.note or "")[:2000],
            "metadata": metadata,
        }
        if customer and opportunity.customer_id != customer.pk:
            values["customer"] = customer
        for field, value in values.items():
            current = getattr(opportunity, f"{field}_id", None) if field == "customer" else getattr(opportunity, field)
            target = value.pk if field == "customer" else value
            if current != target:
                setattr(opportunity, field, value)
                dirty.append(field)
        if dirty:
            opportunity.save(update_fields=[*dirty, "updated_at"])

        reason = inquiry.note if stage == CrmOpportunity.STAGE_LOST else ""
        opportunity, _changed = transition_opportunity(
            opportunity,
            stage,
            event=f"ASSISTANT_INQUIRY_{inquiry.status.upper()}",
            event_key=event_key,
            reason=reason,
            metadata=metadata,
        )
    return opportunity


def process_sync_event(sync_event_or_id):
    """Process or retry one durable synchronization event."""

    sync_event = (
        sync_event_or_id
        if isinstance(sync_event_or_id, CrmSyncEvent)
        else CrmSyncEvent.objects.get(pk=sync_event_or_id)
    )
    CrmSyncEvent.objects.filter(pk=sync_event.pk).update(
        status=CrmSyncEvent.STATUS_PENDING,
        attempts=sync_event.attempts + 1,
        last_error="",
    )
    try:
        if sync_event.source_type == CrmOpportunity.SOURCE_STORE_ORDER:
            opportunity = sync_store_order_opportunity(sync_event.source_id, event_key=sync_event.event_key)
        elif sync_event.source_type == CrmOpportunity.SOURCE_ASSISTANT_INQUIRY:
            opportunity = sync_assistant_inquiry_opportunity(sync_event.source_id, event_key=sync_event.event_key)
        else:
            raise ValueError(f"unsupported_sync_source:{sync_event.source_type}")
    except Exception as exc:  # noqa: BLE001
        CrmSyncEvent.objects.filter(pk=sync_event.pk).update(
            status=CrmSyncEvent.STATUS_FAILED,
            last_error=str(exc)[:4000],
            processed_at=None,
            updated_at=timezone.now(),
        )
        logger.exception("CRM synchronization failed for %s", sync_event.event_key)
        return None

    CrmSyncEvent.objects.filter(pk=sync_event.pk).update(
        status=CrmSyncEvent.STATUS_PROCESSED,
        last_error="",
        processed_at=timezone.now(),
        updated_at=timezone.now(),
    )
    return opportunity


def opportunity_funnel_snapshot(queryset=None):
    """Return the site opportunity funnel and KPI snapshot in source IRR."""

    now = timezone.localtime()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    opportunities = queryset if queryset is not None else CrmOpportunity.objects.filter(is_active=True)
    rows = opportunities.values("stage").annotate(count=Count("id"), value_irr=Sum("expected_value_irr"))
    by_stage = {row["stage"]: row for row in rows}
    stages = [
        {
            "code": code,
            "label": label,
            "count": by_stage.get(code, {}).get("count", 0),
            "value_irr": by_stage.get(code, {}).get("value_irr") or 0,
        }
        for code, label in CrmOpportunity.STAGE_CHOICES
    ]
    total = opportunities.count()
    open_qs = opportunities.filter(stage__in=CrmOpportunity.OPEN_STAGES)
    won_qs = opportunities.filter(stage=CrmOpportunity.STAGE_WON)
    lost_count = opportunities.filter(stage=CrmOpportunity.STAGE_LOST).count()
    won_count = won_qs.count()
    closed_count = won_count + lost_count
    weighted_value = sum(
        (row["expected_value_irr"] or 0) * (row["probability"] or 0) // 100
        for row in open_qs.values("expected_value_irr", "probability")
    )
    won_cycles = [
        (row["closed_at"] - row["created_at"]).total_seconds()
        for row in won_qs.values("created_at", "closed_at")
        if row["closed_at"] and row["created_at"]
    ]
    return {
        "stages": stages,
        "total_opportunities": total,
        "open_count": open_qs.count(),
        "won_count": won_count,
        "lost_count": lost_count,
        "conversion_rate": round(won_count / closed_count, 4) if closed_count else None,
        "open_pipeline_value_irr": open_qs.aggregate(total=Sum("expected_value_irr"))["total"] or 0,
        "weighted_pipeline_value_irr": weighted_value,
        "won_revenue_irr": won_qs.aggregate(total=Sum("expected_value_irr"))["total"] or 0,
        "new_this_month": opportunities.filter(created_at__gte=month_start).count(),
        "avg_cycle_days": round((sum(won_cycles) / len(won_cycles)) / 86400, 1) if won_cycles else None,
        "unassigned_count": open_qs.filter(owner__isnull=True).count(),
        "overdue_count": open_qs.filter(next_follow_up_at__lt=now).count(),
    }
