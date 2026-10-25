"""Generate reviewable IME channel messages and publish an explicit draft once per platform."""
import hashlib
import json
import urllib.error
import urllib.request
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from core.models import SiteSettings
from products.external_markets import gregorian_to_jalali, trade_display_name
from products.models import CommodityExchangeTrade
from .models import GoogleRelayJob, MarketChannelDraft, MarketChannelPublication, MessagingSettings, OutboundMessage


PLATFORMS = ("telegram", "bale")
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def number(value, places=0):
    if value is None:
        return "اعلام نشده"
    rounded = Decimal(value).quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)
    formatted = f"{rounded:,.{places}f}"
    if places == 3:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted.translate(FA_DIGITS)


def volume(rows, field):
    # A physical offer can have several execution reports. Do not repeat its offered/demand volume.
    if field == "traded_volume":
        values = [getattr(row, field) for row in rows if getattr(row, field) is not None]
    else:
        offers = {}
        for row in sorted(rows, key=lambda item: item.source_report_id):
            key = str((row.raw or {}).get("arzehPk") or row.source_report_id)
            offers[key] = getattr(row, field)
        values = [value for value in offers.values() if value is not None]
    return sum(values, Decimal(0)) if values else None


def weighted(rows, price_field, weight_field):
    if price_field == "base_price":
        offers = {}
        for row in sorted(rows, key=lambda item: item.source_report_id):
            offers[str((row.raw or {}).get("arzehPk") or row.source_report_id)] = row
        rows = list(offers.values())
    pairs = [(getattr(row, price_field), getattr(row, weight_field)) for row in rows]
    valid = [(price, weight) for price, weight in pairs if price is not None and weight and weight > 0]
    if valid:
        return sum(price * weight for price, weight in valid) / sum(weight for _, weight in valid)
    if price_field == "base_price":
        values = [price for price, _ in pairs if price is not None]
        if values and len(set(values)) == 1:
            return values[0]
    return None


def message_body(rows, kind, date, cfg):
    first = rows[0]
    brand = SiteSettings.load().site_name or "کاوه‌متال"
    lines = [f"📊 {brand} | گزارش بورس کالا", f"تاریخ معاملات: {gregorian_to_jalali(date).translate(FA_DIGITS)}", ""]
    if kind == "summary":
        lines += [f"گروه: {first.product_group}", f"تعداد نمادها: {number(len({row.symbol for row in rows}))}"]
        units = defaultdict(list)
        for row in rows:
            units[row.unit or "واحد اعلامی"].append(row)
        for unit, entries in units.items():
            lines += [f"حجم عرضه: {number(volume(entries, 'offered_volume'), 3)} {unit}",
                      f"تقاضا: {number(volume(entries, 'demand_volume'), 3)} {unit}",
                      f"حجم معامله: {number(volume(entries, 'traded_volume'), 3)} {unit}"]
        lines.append("جزئیات هر کالا در پیام‌های تفکیکی و تابلوی سایت منتشر می‌شود.")
    else:
        base = weighted(rows, "base_price", "offered_volume")
        price = weighted(rows, "weighted_price", "traded_volume")
        vat = cfg.market_vat_percent
        multiplier = 1 + vat / 100
        competition = (price / base - 1) * 100 if price is not None and base and base > 0 else None
        lines += [f"تولیدکننده: {first.producer_name or 'اعلام نشده'}", f"نام کالا: {trade_display_name(first)}",
                  f"نماد: {first.symbol}", f"نوع قرارداد: {first.contract_type or 'اعلام نشده'}",
                  f"حجم عرضه: {number(volume(rows, 'offered_volume'), 3)} {first.unit}",
                  f"نرخ پایه: {number(base * multiplier if base is not None else None)} {first.currency}",
                  f"تقاضای اولیه: {number(volume(rows, 'demand_volume'), 3)} {first.unit}",
                  f"حجم معامله: {number(volume(rows, 'traded_volume'), 3)} {first.unit}",
                  f"متوسط رقابت: {number(competition, 2)}{'٪' if competition is not None else ''}",
                  f"نرخ میانگین معامله: {number(price * multiplier if price is not None else None)} {first.currency}",
                  f"تاریخ تحویل: {(first.delivery_date_jalali or 'اعلام نشده').translate(FA_DIGITS)}"]
        lines += ["", f"نرخ‌ها با افزودن {number(vat, 2)}٪ مالیات انتخاب‌شده در پنل محاسبه شده‌اند." if vat else "نرخ‌ها مطابق گزارش منبع هستند؛ مالیات جداگانه به آن‌ها اضافه نشده است."]
    lines += ["", "منبع: گزارش معاملات بورس کالای ایران", f"{cfg.site_base_url.rstrip('/')}/commodity-exchange"]
    if cfg.market_contact_phone:
        lines.append(f"تماس: {cfg.market_contact_phone}")
    return "\n".join(lines)


def generate_drafts(date, group="", kind="item", actor=None, traded_only=False):
    cfg = MessagingSettings.load()
    rows = CommodityExchangeTrade.objects.filter(trade_date=date).order_by("product_group", "producer_name", "symbol", "source_report_id")
    if group:
        rows = rows.filter(product_group=group)
    if traded_only:
        rows = rows.filter(traded_volume__gt=0)
    buckets = defaultdict(list)
    for row in rows:
        key = (row.product_group,) if kind == "summary" else (
            row.product_group, row.symbol, row.producer_name, row.contract_type,
            row.delivery_date_jalali, row.currency, row.unit,
        )
        buckets[key].append(row)
    drafts = []
    for entries in buckets.values():
        body = message_body(entries, kind, date, cfg)
        texts = {}
        targets = {}
        for platform in PLATFORMS:
            link = getattr(cfg, f"market_{platform}_channel_url")
            texts[platform] = body + (f"\n{link}" if link else "")
            targets[platform] = getattr(cfg, f"market_{platform}_channel_id")
        if any(len(text) > 4000 for text in texts.values()):
            raise ValueError("متن یکی از گزارش‌ها طولانی است؛ گروه کوچک‌تری انتخاب کنید.")
        ids = sorted(row.source_report_id for row in entries)
        fingerprint = hashlib.sha256(json.dumps([str(date), kind, ids, texts, targets], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        draft, _ = MarketChannelDraft.objects.get_or_create(fingerprint=fingerprint, defaults={
            "report_date": date, "kind": kind, "product_group": entries[0].product_group,
            "title": (entries[0].product_group if kind == "summary" else f"{trade_display_name(entries[0])} — {entries[0].producer_name}")[:500],
            "texts": texts, "targets": targets, "source_report_ids": ids, "created_by": actor,
        })
        drafts.append(draft)
    return drafts


def draft_payload(draft):
    from .google_relay import expire_claims
    expire_claims()
    publications = {item.platform: {"status": item.outbound.status, "error": item.outbound.error,
                    "message_id": item.outbound.provider_message_id} for item in draft.publications.select_related("outbound")}
    for item in draft.publications.select_related('outbound'):
        job = item.outbound.google_jobs.order_by('-created_at').first()
        if job:
            publications[item.platform]['relay_status'] = job.status
    return {"id": draft.id, "date": draft.report_date.isoformat(), "kind": draft.kind,
            "group": draft.product_group, "title": draft.title, "texts": draft.texts,
            "targets": draft.targets, "publications": publications}


class BotRejected(Exception):
    pass


def bot_send(platform, token, recipient, text, api_base):
    request = urllib.request.Request(f"{api_base.rstrip('/')}/bot{token}/sendMessage",
        data=json.dumps({"chat_id": recipient, "text": text, "disable_web_page_preview": True}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read(1024 * 1024))
    except urllib.error.HTTPError as exc:
        if 400 <= exc.code < 500:
            raise BotRejected("سرویس پیام‌رسان درخواست را نپذیرفت؛ دسترسی ربات به کانال و تنظیمات را بررسی کنید.") from None
        raise
    if payload.get("ok") is not True:
        raise BotRejected("سرویس پیام‌رسان درخواست را نپذیرفت؛ تنظیمات و دسترسی ربات را بررسی کنید.")
    message_id = payload.get("result", {}).get("message_id")
    if message_id is None:
        raise RuntimeError("Unconfirmed bot result")
    return str(message_id)


def publish_draft(draft, platforms, actor, retry_failed=False):
    cfg = MessagingSettings.load()
    # Validate every selected platform before sending anything.
    for platform in platforms:
        google = platform == 'telegram' and cfg.market_telegram_transport == 'google'
        if (not cfg.market_google_relay_key_hash if google else not getattr(cfg, f"market_{platform}_bot_token")) or not getattr(cfg, f"market_{platform}_channel_id"):
            raise ValueError(f"تنظیمات کانال {platform} کامل نیست.")
        if platform == "telegram" and cfg.market_telegram_transport == "mtproto":
            from .telegram_transport import check_configuration, TelegramNotSent
            try:
                check_configuration(cfg)
            except TelegramNotSent as exc:
                raise ValueError(str(exc)) from None
        if draft.targets[platform] != getattr(cfg, f"market_{platform}_channel_id"):
            raise ValueError("مقصد کانال تغییر کرده است؛ پیش‌نمایش جدید بسازید.")
    for platform in platforms:
        with transaction.atomic():
            locked = MarketChannelDraft.objects.select_for_update().get(pk=draft.pk)
            previous = MarketChannelPublication.objects.select_related("outbound").filter(draft=locked, platform=platform).first()
            if previous:
                if not retry_failed or previous.outbound.status != OutboundMessage.STATUS_FAILED:
                    continue
                outbound = previous.outbound
                outbound.status = OutboundMessage.STATUS_QUEUED
                outbound.error = ""
                outbound.save()
            else:
                outbound = OutboundMessage.objects.create(
                    channel=platform, provider="bale_bot" if platform == "bale" else "telegram_bot",
                    recipient=draft.targets[platform], purpose=OutboundMessage.PURPOSE_MANUAL,
                    body=draft.texts[platform], created_by=actor, meta={"market_draft_id": draft.pk},
                )
                MarketChannelPublication.objects.create(draft=locked, platform=platform, outbound=outbound)
            if platform == 'telegram' and cfg.market_telegram_transport == 'google':
                if not outbound.body or len(outbound.body) > 4000:
                    raise ValueError('متن واسط گوگل باید بین ۱ تا ۴۰۰۰ نویسه باشد.')
                outbound.provider = 'google_relay'
                outbound.save(update_fields=['provider'])
                GoogleRelayJob.objects.create(outbound=outbound)
                continue
        try:
            if platform == "telegram" and cfg.market_telegram_transport == "mtproto":
                from .telegram_transport import send_mtproto, TelegramNotSent
                try:
                    outbound.provider_message_id = send_mtproto(cfg, outbound.body)
                except TelegramNotSent as exc:
                    raise BotRejected(str(exc)) from None
            else:
                outbound.provider_message_id = bot_send(platform, getattr(cfg, f"market_{platform}_bot_token"),
                    outbound.recipient, outbound.body, "https://tapi.bale.ai" if platform == "bale" else cfg.market_telegram_api_base)
            outbound.status = OutboundMessage.STATUS_SENT
        except BotRejected as exc:
            outbound.status = OutboundMessage.STATUS_FAILED
            outbound.error = str(exc)
        except Exception:
            # A timeout can occur after the platform accepted the post. Never resend automatically.
            outbound.status = OutboundMessage.STATUS_QUEUED
            outbound.error = "نتیجه ارسال نامشخص است؛ پیش از هر اقدام کانال را بررسی کنید. ارسال خودکار تکرار نمی‌شود."
        outbound.save()
    return draft_payload(draft)
