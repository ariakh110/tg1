"""سرویسِ پیام‌رسانیِ کانال‌پذیر (فعلاً فقط SMS/کاوه‌نگار).

نقطهٔ ورودِ یگانه برای ارسال: تنظیمات را می‌خواند، شماره را نرمال می‌کند، یک
`OutboundMessage` ثبت می‌کند، و در صورتِ فعال‌بودن سرویس‌دهنده را صدا می‌زند.
اگر `sms_enabled` خاموش یا کلید نباشد، ارسال «خشک» (skipped) ثبت می‌شود — بدونِ تماس با
سرویس و بدونِ خطا — تا کلِ جریان پیش از وجودِ اعتبار قابلِ آزمایش باشد.
"""
import re
from collections import defaultdict

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from customers.models import Customer, CustomerActivity
from products.models import ProductCategory

from .models import (
    MessagingContactGroup,
    MessagingContactGroupMember,
    MessagingSettings,
    OutboundMessage,
)
from .phones import is_valid_mobile, normalize_phone
from .providers import kavenegar, safir, telegram

# متنِ مراحلِ خرید (پیامکِ فروشِ مستقیم). {order}/{amount} در صورتِ وجود جایگزین می‌شوند.
PURCHASE_STEPS = {
    "registered": "سفارش شما ثبت شد.",
    "preparing": "سفارش شما در حال آماده‌سازی است.",
    "invoiced": "پیش‌فاکتور سفارش شما صادر شد.",
    "shipped": "سفارش شما ارسال شد.",
    "delivered": "سفارش شما تحویل داده شد. از خرید شما سپاسگزاریم.",
}


def _today_sent_count():
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return OutboundMessage.objects.filter(
        created_at__gte=start,
        channel=OutboundMessage.CHANNEL_SMS,
        status__in=(
            OutboundMessage.STATUS_QUEUED,
            OutboundMessage.STATUS_SENT,
            OutboundMessage.STATUS_DELIVERED,
        ),
    ).count()


def _log_activity(customer, message, status, created_by, channel_label="پیامک"):
    label = {
        OutboundMessage.STATUS_SENT: "ارسال شد",
        OutboundMessage.STATUS_SKIPPED: "خشک (سرویس غیرفعال)",
        OutboundMessage.STATUS_FAILED: "ناموفق",
    }.get(status, status)
    snippet = (message or "").strip().replace("\n", " ")[:120]
    CustomerActivity.objects.create(
        customer=customer,
        kind=CustomerActivity.KIND_MESSAGE,
        body=f"{channel_label} ({label}): {snippet}",
        created_by=created_by if getattr(created_by, "is_authenticated", False) else None,
    )


def send_sms(recipient, message, *, customer=None, purpose=OutboundMessage.PURPOSE_MANUAL,
             template="", tokens=None, created_by=None, cfg=None, log_activity=True, meta=None,
             tag=""):
    """ارسالِ یک پیامک و ثبتِ آن در لاگ. خروجی: نمونهٔ `OutboundMessage`.

    اگر `template` و `tokens` داده شود، مسیرِ verify/lookup (فیلترنشده) استفاده می‌شود؛
    وگرنه sms/send سادهٔ متنی.
    """
    cfg = cfg or MessagingSettings.load()
    recipient = normalize_phone(recipient)
    body = message or ("[الگو: %s] %s" % (template, " | ".join(tokens or [])) if template else "")

    msg = OutboundMessage(
        channel=OutboundMessage.CHANNEL_SMS,
        provider=cfg.provider,
        customer=customer,
        recipient=recipient,
        purpose=purpose,
        template=template,
        body=body,
        meta=meta,
        created_by=created_by if getattr(created_by, "is_authenticated", False) else None,
    )

    if not is_valid_mobile(recipient):
        msg.status = OutboundMessage.STATUS_FAILED
        msg.error = "شمارهٔ گیرنده نامعتبر است."
    elif not cfg.is_configured:
        # حالتِ خشک: سرویس خاموش یا بدونِ کلید — هیچ تماسی با سرویس‌دهنده گرفته نمی‌شود.
        msg.status = OutboundMessage.STATUS_SKIPPED
        msg.error = "" if cfg.sms_enabled else "ارسالِ پیامک در تنظیمات غیرفعال است."
    else:
        if template and tokens:
            t = list(tokens) + ["", "", ""]
            result = kavenegar.send_lookup(cfg.kavenegar_api_key, recipient, template, t[0], t[1], t[2])
        else:
            result = kavenegar.send_sms(cfg.kavenegar_api_key, recipient, body, cfg.sender, tag=tag)
        msg.status = result.status or (OutboundMessage.STATUS_SENT if result.ok else OutboundMessage.STATUS_FAILED)
        msg.provider_message_id = result.message_id
        msg.cost = result.cost
        msg.error = result.error[:400]

    msg.save()
    if customer and log_activity:
        _log_activity(customer, body, msg.status, created_by)
    return msg


def send_bale(recipient, message, *, customer=None, purpose=OutboundMessage.PURPOSE_MANUAL,
              created_by=None, cfg=None, log_activity=True, request_id="", meta=None):
    """ارسالِ یک پیامِ بله به یک شماره از طریقِ «سفیر» و ثبتِ آن در لاگ.

    اگر سفیر غیرفعال/بی‌کلید باشد، ارسالِ «خشک» (skipped) ثبت می‌شود — بدونِ تماس با سرویس.
    """
    cfg = cfg or MessagingSettings.load()
    phone09 = normalize_phone(recipient)
    phone98 = safir.to_safir_phone(phone09)
    body = message or ""

    msg = OutboundMessage(
        channel=OutboundMessage.CHANNEL_BALE, provider="safir", customer=customer,
        recipient=phone09, purpose=purpose, body=body, meta=meta,
        created_by=created_by if getattr(created_by, "is_authenticated", False) else None,
    )
    if not is_valid_mobile(phone09) or not phone98:
        msg.status = OutboundMessage.STATUS_FAILED
        msg.error = "شمارهٔ گیرنده نامعتبر است."
    elif not cfg.safir_configured:
        msg.status = OutboundMessage.STATUS_SKIPPED
        msg.error = "" if cfg.safir_enabled else "ارسالِ بله (سفیر) در تنظیمات غیرفعال است."
    else:
        result = safir.send_message(cfg.safir_access_key, cfg.safir_bot_id, phone98, body, request_id=request_id)
        msg.status = result.status or (OutboundMessage.STATUS_SENT if result.ok else OutboundMessage.STATUS_FAILED)
        msg.provider_message_id = result.message_id
        msg.error = result.error[:400]

    msg.save()
    if customer and log_activity:
        _log_activity(customer, body, msg.status, created_by, channel_label="بله")
    return msg


def send_to_customer(customer, message=None, *, channel=OutboundMessage.CHANNEL_SMS, template="",
                     tokens=None, purpose=OutboundMessage.PURPOSE_MANUAL, created_by=None, cfg=None):
    """ارسال به مشتریِ CRM روی شمارهٔ موبایلش (پیامک یا بله) + ثبتِ فعالیت روی تایم‌لاین."""
    if channel == OutboundMessage.CHANNEL_BALE:
        return send_bale(customer.phone, message, customer=customer, purpose=purpose, created_by=created_by, cfg=cfg)
    return send_sms(
        customer.phone, message, customer=customer, template=template, tokens=tokens,
        purpose=purpose, created_by=created_by, cfg=cfg,
    )


def _id_list(values):
    result = []
    for value in values or []:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0 and parsed not in result:
            result.append(parsed)
    return result


def _phone_candidates(raw):
    if isinstance(raw, (list, tuple)):
        chunks = [str(value or "") for value in raw]
    else:
        chunks = str(raw or "").splitlines()
    values = []
    invalid = 0
    pattern = re.compile(r"(?:0098|\+?98|0)?9(?:[\s-]?\d){9}")
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        matches = pattern.findall(chunk)
        if matches:
            values.extend(matches)
        elif is_valid_mobile(chunk):
            values.append(chunk)
        else:
            invalid += 1
    return values, invalid


@transaction.atomic
def replace_group_members(group, *, customer_ids=None, phones=None):
    """Replace a saved group's members from CRM ids and pasted/exported numbers."""
    customer_ids = _id_list(customer_ids)
    customers = list(Customer.objects.filter(pk__in=customer_ids, is_active=True))
    pasted, invalid = _phone_candidates(phones)
    candidates = [(customer.phone, customer, customer.name) for customer in customers]
    candidates.extend((value, None, "") for value in pasted)

    by_phone = {}
    duplicates = 0
    for raw_phone, customer, name in candidates:
        phone = normalize_phone(raw_phone)
        if not is_valid_mobile(phone):
            invalid += 1
            continue
        if phone in by_phone:
            duplicates += 1
            if customer and not by_phone[phone]["customer"]:
                by_phone[phone] = {"customer": customer, "name": name or customer.name}
            continue
        by_phone[phone] = {"customer": customer, "name": name}

    unlinked_phones = [phone for phone, item in by_phone.items() if not item["customer"]]
    variants = set(unlinked_phones)
    for phone in unlinked_phones:
        variants.update({f"98{phone[1:]}", f"+98{phone[1:]}", f"0098{phone[1:]}"})
    for customer in Customer.objects.filter(phone__in=variants, is_active=True):
        phone = normalize_phone(customer.phone)
        if phone in by_phone and not by_phone[phone]["customer"]:
            by_phone[phone] = {"customer": customer, "name": customer.name}

    group.members.all().delete()
    MessagingContactGroupMember.objects.bulk_create(
        [
            MessagingContactGroupMember(
                group=group,
                phone=phone,
                customer=item["customer"],
                name=item["name"] or (item["customer"].name if item["customer"] else ""),
            )
            for phone, item in by_phone.items()
        ]
    )
    group.save(update_fields=["updated_at"])
    return {
        "member_count": len(by_phone),
        "invalid_count": invalid,
        "duplicate_count": duplicates,
    }


def resolve_audience(selectors):
    """Resolve CRM/group/product selectors into unique valid mobile recipients without sending."""
    selectors = selectors or {}
    customer_ids = _id_list(selectors.get("customer_ids"))
    group_ids = _id_list(selectors.get("group_ids"))
    category_ids = _id_list(selectors.get("product_category_ids"))
    stage = str(selectors.get("stage") or "").strip()
    source = str(selectors.get("source") or "").strip()
    all_active = selectors.get("all_active") is True
    selector_count = sum(bool(value) for value in (customer_ids, group_ids, category_ids, stage, source, all_active))

    recipients = {}
    source_phones = defaultdict(set)
    invalid_count = 0
    duplicate_count = 0

    def add(phone, customer=None, name="", audience_source="customers"):
        nonlocal invalid_count, duplicate_count
        normalized = normalize_phone(phone)
        if not is_valid_mobile(normalized):
            invalid_count += 1
            return
        source_phones[audience_source].add(normalized)
        if normalized in recipients:
            duplicate_count += 1
            recipients[normalized]["sources"].add(audience_source)
            if customer and not recipients[normalized]["customer"]:
                recipients[normalized]["customer"] = customer
                recipients[normalized]["name"] = name or customer.name
            return
        recipients[normalized] = {
            "phone": normalized,
            "customer": customer,
            "name": name or (customer.name if customer else ""),
            "sources": {audience_source},
        }

    if customer_ids:
        for customer in Customer.objects.filter(pk__in=customer_ids, is_active=True):
            add(customer.phone, customer, customer.name, "customers")

    if group_ids:
        groups = MessagingContactGroup.objects.filter(pk__in=group_ids, is_active=True).prefetch_related(
            "members__customer"
        )
        for group in groups:
            for member in group.members.all():
                add(member.phone, member.customer, member.name, "groups")

    if category_ids:
        selected_categories = list(ProductCategory.objects.filter(pk__in=category_ids))
        expanded_ids = set()
        for category in selected_categories:
            expanded_ids.update(category.get_descendants(include_self=True).values_list("id", flat=True))
        if expanded_ids:
            from sales.models import StoreOrder, StoreOrderStatus

            excluded_statuses = (
                StoreOrderStatus.DRAFT,
                StoreOrderStatus.CANCELLED,
                StoreOrderStatus.EXPIRED,
            )
            explicit_ids = Customer.objects.filter(
                product_interests__id__in=expanded_ids,
                is_active=True,
            ).values_list("id", flat=True)
            buyer_ids = StoreOrder.objects.exclude(status__in=excluded_statuses).filter(
                items__product__category_id__in=expanded_ids,
            ).values_list("buyer_id", flat=True)
            product_customers = Customer.objects.filter(
                Q(id__in=explicit_ids) | Q(user_id__in=buyer_ids),
                is_active=True,
            ).distinct()
            for customer in product_customers:
                add(customer.phone, customer, customer.name, "products")

    if stage or source or all_active:
        filtered = Customer.objects.filter(is_active=True)
        if stage:
            filtered = filtered.filter(stage=stage)
        if source:
            filtered = filtered.filter(source=source)
        for customer in filtered:
            add(customer.phone, customer, customer.name, "filters")

    resolved = [
        {
            **item,
            "sources": sorted(item["sources"]),
        }
        for item in recipients.values()
    ]
    sample = [
        {
            "customer_id": item["customer"].id if item["customer"] else None,
            "name": item["name"],
            "phone": item["phone"],
            "sources": item["sources"],
        }
        for item in resolved[:10]
    ]
    return {
        "selector_count": selector_count,
        "valid_count": len(resolved),
        "invalid_count": invalid_count,
        "duplicate_count": duplicate_count,
        "source_counts": {key: len(value) for key, value in source_phones.items()},
        "sample": sample,
        "recipients": resolved,
    }


def _bulk_summary(messages, *, cap_limited=0):
    counters = {"sent": 0, "skipped": 0, "failed": 0}
    for msg in messages:
        if msg.status in (OutboundMessage.STATUS_SENT, OutboundMessage.STATUS_DELIVERED):
            counters["sent"] += 1
        elif msg.status == OutboundMessage.STATUS_SKIPPED:
            counters["skipped"] += 1
        else:
            counters["failed"] += 1
    return {**counters, "total": len(messages), "cap_limited": cap_limited, "messages": messages}


def send_bulk_recipients(recipients, message, *, channel=OutboundMessage.CHANNEL_SMS,
                         purpose=OutboundMessage.PURPOSE_BULK, created_by=None, cfg=None, tag=""):
    """Send to resolved recipient dictionaries while preserving one audit row per phone."""
    cfg = cfg or MessagingSettings.load()
    recipients = list(recipients)
    actor = created_by if getattr(created_by, "is_authenticated", False) else None

    if channel == OutboundMessage.CHANNEL_BALE:
        messages = [
            send_bale(
                item["phone"],
                message,
                customer=item.get("customer"),
                purpose=purpose,
                created_by=created_by,
                cfg=cfg,
                meta={"audience_sources": item.get("sources", [])},
            )
            for item in recipients
        ]
        return _bulk_summary(messages)

    cap = cfg.daily_send_cap or 0
    already = _today_sent_count() if cap and cfg.is_configured else 0
    available = max(cap - already, 0) if cap and cfg.is_configured else len(recipients)
    sendable = recipients[:available]
    capped = recipients[available:]
    messages = []

    for item in capped:
        msg = OutboundMessage.objects.create(
            channel=OutboundMessage.CHANNEL_SMS,
            provider=cfg.provider,
            customer=item.get("customer"),
            recipient=item["phone"],
            purpose=purpose,
            body=message,
            status=OutboundMessage.STATUS_SKIPPED,
            error="سقفِ ارسالِ روزانه پر شده است.",
            meta={"audience_sources": item.get("sources", []), "kavenegar_tag": tag},
            created_by=actor,
        )
        messages.append(msg)
        if item.get("customer"):
            _log_activity(item["customer"], message, msg.status, created_by)

    if not cfg.is_configured:
        for item in sendable:
            messages.append(
                send_sms(
                    item["phone"],
                    message,
                    customer=item.get("customer"),
                    purpose=purpose,
                    created_by=created_by,
                    cfg=cfg,
                    tag=tag,
                    meta={"audience_sources": item.get("sources", []), "kavenegar_tag": tag},
                )
            )
        return _bulk_summary(messages, cap_limited=len(capped))

    queued = []
    for item in sendable:
        msg = OutboundMessage.objects.create(
            channel=OutboundMessage.CHANNEL_SMS,
            provider=cfg.provider,
            customer=item.get("customer"),
            recipient=item["phone"],
            purpose=purpose,
            body=message,
            status=OutboundMessage.STATUS_QUEUED,
            meta={"audience_sources": item.get("sources", []), "kavenegar_tag": tag},
            created_by=actor,
        )
        queued.append((item, msg))
        messages.append(msg)

    for offset in range(0, len(queued), 200):
        chunk = queued[offset:offset + 200]
        provider_results = kavenegar.send_sms_many(
            cfg.kavenegar_api_key,
            [item["phone"] for item, _msg in chunk],
            message,
            cfg.sender,
            tag=tag,
        )
        for (item, msg), result in zip(chunk, provider_results):
            msg.status = result.status or (
                OutboundMessage.STATUS_SENT if result.ok else OutboundMessage.STATUS_FAILED
            )
            msg.provider_message_id = result.message_id
            msg.cost = result.cost
            msg.error = result.error[:400]
            msg.save(update_fields=["status", "provider_message_id", "cost", "error", "updated_at"])
            if item.get("customer"):
                _log_activity(item["customer"], message, msg.status, created_by)
    return _bulk_summary(messages, cap_limited=len(capped))


def send_bulk(customers, message, *, channel=OutboundMessage.CHANNEL_SMS,
              purpose=OutboundMessage.PURPOSE_BULK, created_by=None, cfg=None):
    recipients = [
        {"phone": normalize_phone(customer.phone), "customer": customer, "name": customer.name, "sources": ["filters"]}
        for customer in customers
    ]
    return send_bulk_recipients(
        recipients,
        message,
        channel=channel,
        purpose=purpose,
        created_by=created_by,
        cfg=cfg,
    )


def notify_purchase_step(customer, step, *, order_no="", amount=None, created_by=None, cfg=None):
    """ارسالِ پیامکِ یک مرحله از خرید به مشتری (فروشِ مستقیم).

    متن از `PURCHASE_STEPS` ساخته می‌شود (+ شمارهٔ سفارش/مبلغ). اگر الگوی مراحلِ خرید
    در تنظیمات باشد، از مسیرِ verify/lookup (فیلترنشده) با توکن‌ها استفاده می‌شود.
    """
    cfg = cfg or MessagingSettings.load()
    base = PURCHASE_STEPS.get(step)
    if not base:
        raise ValueError(f"مرحلهٔ نامعتبر: {step}")

    parts = [base]
    if order_no:
        parts.append(f"شمارهٔ سفارش: {order_no}")
    if amount is not None:
        parts.append(f"مبلغ: {int(amount):,} تومان")
    body = " ".join(parts)

    template = cfg.purchase_template or ""
    tokens = [str(order_no or step)] if template else None
    if template and amount is not None:
        tokens.append(f"{int(amount):,}")

    return send_sms(
        customer.phone, body, customer=customer, template=template, tokens=tokens,
        purpose=OutboundMessage.PURPOSE_ORDER_STATUS, created_by=created_by, cfg=cfg,
        meta={"step": step, "order_no": order_no},
    )


def notify_admin(title, lines=None, *, customer=None, cfg=None):
    """اطلاع‌رسانیِ یک رویداد به ادمین از کانال‌های فعال (تلگرام + پیامک).

    `title` تیترِ پیام و `lines` فهرستِ سطرهای جزئیات است. اگر هیچ کانالی پیکربندی نشده باشد،
    یک ردیفِ «خشک» (skipped) ثبت می‌شود تا در گزارش دیده شود ولی چیزی ارسال نمی‌گردد.
    خروجی: فهرستِ `OutboundMessage`های ثبت‌شده. هیچ خطایی بیرون نمی‌دهد (caller امن است).
    """
    cfg = cfg or MessagingSettings.load()
    lines = [str(x) for x in (lines or []) if str(x).strip()]
    plain = "\n".join([str(title)] + lines).strip()
    messages = []

    # --- تلگرام/بله (متنِ ساده تا روی هر دو تمیز نمایش یابد) ---
    # اگر ربات دوطرفه فعال و مشتری مشخص باشد، دکمه‌های عملیاتی به پیام می‌چسبد.
    reply_markup = None
    if customer is not None and getattr(customer, "pk", None) and cfg.bale_webhook_enabled:
        from .bale_bot import _lead_buttons

        reply_markup = _lead_buttons(customer.pk)

    if cfg.telegram_configured:
        for chat_id in cfg.telegram_chat_ids:
            result = telegram.send_message(
                cfg.telegram_bot_token, chat_id, plain, base_url=cfg.telegram_api_base,
                reply_markup=reply_markup,
            )
            messages.append(
                OutboundMessage.objects.create(
                    channel=OutboundMessage.CHANNEL_TELEGRAM,
                    provider="telegram",
                    customer=customer,
                    recipient=str(chat_id),
                    purpose=OutboundMessage.PURPOSE_ADMIN_ALERT,
                    body=plain,
                    status=result.status or (OutboundMessage.STATUS_SENT if result.ok else OutboundMessage.STATUS_FAILED),
                    provider_message_id=result.message_id,
                    error=(result.error or "")[:400],
                )
            )

    # --- پیامک به ادمین ---
    admin_phone = (cfg.admin_alert_phone or "").strip()
    if admin_phone:
        messages.append(
            send_sms(
                admin_phone, plain, purpose=OutboundMessage.PURPOSE_ADMIN_ALERT,
                cfg=cfg, log_activity=False,
            )
        )

    # --- حالتِ خشک: هیچ کانالی پیکربندی نشده ---
    if not messages:
        messages.append(
            OutboundMessage.objects.create(
                channel=OutboundMessage.CHANNEL_TELEGRAM,
                provider="",
                customer=customer,
                recipient="",
                purpose=OutboundMessage.PURPOSE_ADMIN_ALERT,
                body=plain,
                status=OutboundMessage.STATUS_SKIPPED,
                error="هیچ کانالِ اطلاع‌رسانیِ ادمین پیکربندی نشده است.",
            )
        )
    return messages


def log_incoming_sms(sender, text, raw=None):
    """پیامکِ دریافتی از مشتری (وب‌هوکِ کاوه‌نگار) را روی تایم‌لاینِ همان مشتری ثبت می‌کند.

    اگر شماره با هیچ مشتری‌ای جور نشود، چیزی ثبت نمی‌شود (None برمی‌گردد).
    """
    phone = normalize_phone(sender)
    customer = Customer.objects.filter(phone=phone).first()
    if not customer:
        return None
    snippet = (text or "").strip().replace("\n", " ")[:200]
    return CustomerActivity.objects.create(
        customer=customer,
        kind=CustomerActivity.KIND_MESSAGE,
        body=f"پیامکِ دریافتی: {snippet}",
    )
