import re

from django.db import migrations


STORE_STAGE_MAP = {
    "DRAFT": "new_inquiry",
    "SUBMITTED": "new_inquiry",
    "QUOTE_REQUESTED": "pricing",
    "PRICE_CONFIRMED": "quote_sent",
    "PAYMENT_PENDING": "payment_pending",
    "PAID": "fulfillment",
    "FULFILLMENT_PENDING": "fulfillment",
    "READY_FOR_PICKUP": "fulfillment",
    "SHIPPED": "fulfillment",
    "DELIVERED": "won",
    "COMPLETED": "won",
    "CANCELLED": "lost",
    "EXPIRED": "lost",
}

INQUIRY_STAGE_MAP = {
    "new": "new_inquiry",
    "contacted": "qualified",
    "quoted": "quote_sent",
    "won": "won",
    "lost": "lost",
}

PROBABILITY = {
    "new_inquiry": 10,
    "qualified": 25,
    "pricing": 40,
    "quote_sent": 55,
    "payment_pending": 75,
    "fulfillment": 90,
    "won": 100,
    "lost": 0,
}


def normalize_phone(raw):
    digits = re.sub(r"\D", "", str(raw or ""))
    if digits.startswith("0098"):
        digits = digits[4:]
    elif digits.startswith("98") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    return digits


def customer_for(Customer, *, user_id=None, phone=""):
    normalized = normalize_phone(phone)
    if normalized:
        customer = Customer.objects.filter(phone=normalized).first()
        if customer:
            return customer
    if user_id:
        return Customer.objects.filter(user_id=user_id).order_by("-updated_at").first()
    return None


def backfill_site_opportunities(apps, schema_editor):
    Customer = apps.get_model("customers", "Customer")
    Opportunity = apps.get_model("customers", "CrmOpportunity")
    History = apps.get_model("customers", "CrmOpportunityStageHistory")
    StoreOrder = apps.get_model("sales", "StoreOrder")
    StoreOrderItem = apps.get_model("sales", "StoreOrderItem")
    AssistantInquiry = apps.get_model("assistant", "AssistantInquiry")

    for order in StoreOrder.objects.all().iterator(chunk_size=250):
        stage = STORE_STAGE_MAP.get(order.status)
        if not stage:
            continue
        product_names = list(
            StoreOrderItem.objects.filter(order_id=order.pk)
            .order_by("id")
            .values_list("product_name", flat=True)[:3]
        )
        product_names = [name.strip() for name in product_names if (name or "").strip()]
        title = (
            "سفارش سایت: " + "، ".join(product_names)
            if product_names
            else f"سفارش سایت #{str(order.pk)[:8]}"
        )[:240]
        customer = customer_for(
            Customer,
            user_id=order.buyer_id,
            phone=order.contact_phone,
        )
        opportunity, created = Opportunity.objects.get_or_create(
            source_type="store_order",
            source_id=str(order.pk),
            defaults={
                "customer_id": customer.pk if customer else None,
                "title": title,
                "stage": stage,
                "source_status": order.status,
                "expected_value_irr": max(0, int(order.total_amount or 0)),
                "probability": PROBABILITY[stage],
                "need_details": (order.delivery_notes or "")[:2000],
                "lost_reason": (
                    "لغو سفارش"
                    if order.status == "CANCELLED"
                    else ("انقضای سفارش" if order.status == "EXPIRED" else "")
                ),
                "metadata": {
                    "order_id": str(order.pk),
                    "order_status": order.status,
                    "payment_status": order.payment_status,
                    "quote_confirmation_status": order.quote_confirmation_status,
                    "currency": order.currency,
                    "destination_city": order.destination_city,
                    "destination_province": order.destination_province,
                    "backfilled": True,
                },
                "closed_at": order.updated_at if stage in {"won", "lost"} else None,
            },
        )
        if not created:
            continue
        Opportunity.objects.filter(pk=opportunity.pk).update(
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
        history = History.objects.create(
            opportunity_id=opportunity.pk,
            from_stage="",
            to_stage=stage,
            event="CRM_BACKFILL_STORE_ORDER",
            event_key=f"backfill:store_order:{order.pk}:{order.status}",
            metadata={"order_id": str(order.pk), "backfilled": True},
        )
        History.objects.filter(pk=history.pk).update(created_at=order.updated_at)

    for inquiry in AssistantInquiry.objects.select_related("conversation").all().iterator(chunk_size=250):
        stage = INQUIRY_STAGE_MAP.get(inquiry.status, "new_inquiry")
        conversation = inquiry.conversation if inquiry.conversation_id else None
        customer = customer_for(
            Customer,
            user_id=conversation.user_id if conversation else None,
            phone=inquiry.contact_phone or (conversation.lead_phone if conversation else ""),
        )
        parts = [inquiry.product, inquiry.grade, inquiry.size, inquiry.factory, inquiry.quantity, inquiry.city]
        summary = " - ".join(part for part in parts if (part or "").strip())
        title = (f"استعلام سایت: {summary}" if summary else f"استعلام سایت #{inquiry.pk}")[:240]
        value_irr = 0
        opportunity, created = Opportunity.objects.get_or_create(
            source_type="assistant_inquiry",
            source_id=str(inquiry.pk),
            defaults={
                "customer_id": customer.pk if customer else None,
                "title": title,
                "stage": stage,
                "source_status": inquiry.status,
                "expected_value_irr": value_irr,
                "probability": PROBABILITY[stage],
                "need_details": (inquiry.raw_text or inquiry.note or "")[:2000],
                "lost_reason": (inquiry.note or "")[:255] if stage == "lost" else "",
                "metadata": {
                    "inquiry_id": inquiry.pk,
                    "inquiry_status": inquiry.status,
                    "product": inquiry.product,
                    "size": inquiry.size,
                    "grade": inquiry.grade,
                    "factory": inquiry.factory,
                    "quantity": inquiry.quantity,
                    "city": inquiry.city,
                    "matched_price_toman": max(0, int(inquiry.matched_price or 0)),
                    "backfilled": True,
                },
                "closed_at": inquiry.updated_at if stage in {"won", "lost"} else None,
            },
        )
        if not created:
            continue
        Opportunity.objects.filter(pk=opportunity.pk).update(
            created_at=inquiry.created_at,
            updated_at=inquiry.updated_at,
        )
        history = History.objects.create(
            opportunity_id=opportunity.pk,
            from_stage="",
            to_stage=stage,
            event="CRM_BACKFILL_ASSISTANT_INQUIRY",
            event_key=f"backfill:assistant_inquiry:{inquiry.pk}:{inquiry.status}",
            metadata={"inquiry_id": inquiry.pk, "backfilled": True},
        )
        History.objects.filter(pk=history.pk).update(created_at=inquiry.updated_at)


class Migration(migrations.Migration):
    dependencies = [
        ("assistant", "0004_assistantsettings_lead_capture_mode"),
        ("customers", "0006_crmopportunity_crmopportunitystagehistory_and_more"),
        ("sales", "0013_freightratesettings"),
    ]

    operations = [
        migrations.RunPython(backfill_site_opportunities, migrations.RunPython.noop),
    ]
