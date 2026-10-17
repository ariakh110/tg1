import csv
import hashlib
import io
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

import jdatetime
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import (
    CommodityExchangeTrade,
    GlobalMetalInstrument,
    GlobalMetalObservation,
    MarketDataSyncState,
)


IME_ENDPOINT = "https://www.ime.co.ir/subsystems/ime/services/home/imedata.asmx/GetAmareMoamelatList"
IME_SOURCE_URL = "https://www.ime.co.ir/deals_statistics.html"
METALS_DEV_ENDPOINT = "https://api.metals.dev/v1/latest"
METALS_DEV_SOURCE_URL = "https://metals.dev/"
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
MAX_IME_WINDOW_DAYS = 31

STEEL_GROUPS = {
    "میلگرد": ("میلگرد", "rebar"),
    "ورق و کلاف": ("ورق", "کلاف", "coil", "sheet", "hrc", "crc"),
    "شمش و اسلب": ("شمش", "بلوم", "بیلت", "اسلب", "billet", "bloom", "slab"),
    "تیرآهن و مقاطع": ("تیرآهن", "نبشی", "ناودانی", "مفتول", "beam", "angle", "channel", "wire"),
    "زنجیره سنگ‌آهن": ("سنگ آهن", "سنگ‌آهن", "گندله", "کنسانتره", "آهن اسفنجی", "pellet", "iron ore"),
    "قراضه و فولاد": ("قراضه", "فولاد", "آهن", "steel", "scrap"),
}

METALS_DEV_INSTRUMENTS = {
    "aluminum": ("aluminum", "آلومینیوم", "Aluminium", "LME", ("lme_aluminum",)),
    "copper": ("copper", "مس", "Copper", "LME", ("lme_copper",)),
    "nickel": ("nickel", "نیکل", "Nickel", "LME", ("lme_nickel",)),
    "lead": ("lead", "سرب", "Lead", "LME", ("lme_lead",)),
    "zinc": ("zinc", "روی", "Zinc", "LME", ("lme_zinc",)),
}


class MarketSyncError(RuntimeError):
    pass


def _decimal(value, *, required=False):
    if value in (None, "", "-"):
        if required:
            raise MarketSyncError("مقدار عددی اجباری خالی است.")
        return None
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise MarketSyncError(f"مقدار عددی نامعتبر: {value}") from exc
    if not math.isfinite(float(number)) or (required and number <= 0):
        raise MarketSyncError(f"مقدار عددی نامعتبر: {value}")
    return number


def _post_json(url, payload):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Origin": "https://www.ime.co.ir",
            "Referer": IME_SOURCE_URL,
            "User-Agent": "KavehMetal-MarketSync/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.MARKET_HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise MarketSyncError("ارتباط با سرویس رسمی بورس کالا برقرار نشد.") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise MarketSyncError("پاسخ سرویس بورس کالا بیش از حد مجاز است.")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MarketSyncError("پاسخ سرویس بورس کالا JSON معتبر نیست.") from exc


def _get_json(url, query):
    request_url = f"{url}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(
        request_url,
        headers={"Accept": "application/json", "User-Agent": "KavehMetal-MarketSync/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.MARKET_HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise MarketSyncError("ارتباط با ارائه‌دهنده قیمت جهانی برقرار نشد.") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise MarketSyncError("پاسخ ارائه‌دهنده قیمت جهانی بیش از حد مجاز است.")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MarketSyncError("پاسخ ارائه‌دهنده قیمت جهانی JSON معتبر نیست.") from exc


def jalali_to_gregorian(value):
    try:
        year, month, day = [int(part) for part in str(value).replace("-", "/").split("/")]
        return jdatetime.date(year, month, day).togregorian()
    except (ValueError, TypeError) as exc:
        raise MarketSyncError(f"تاریخ جلالی نامعتبر: {value}") from exc


def gregorian_to_jalali(value):
    converted = jdatetime.date.fromgregorian(date=value)
    return f"{converted.year:04d}/{converted.month:02d}/{converted.day:02d}"


def parse_ime_date(value):
    normalized = str(value or "").replace("-", "/")
    try:
        year, month, day = [int(part) for part in normalized.split("/")]
        gregorian = date(year, month, day) if year > 1700 else jdatetime.date(year, month, day).togregorian()
    except (ValueError, TypeError) as exc:
        raise MarketSyncError(f"تاریخ بورس کالا نامعتبر است: {value}") from exc
    return gregorian, gregorian_to_jalali(gregorian)


def _ime_row_id(row):
    official_id = int(row.get("xTalarReportPK") or row.get("X_TALAR_REPORT_PK") or 0)
    if official_id > 0:
        return official_id
    stable = "|".join(
        str(row.get(key) or "")
        for key in ("arzehPk", "Symbol", "date", "ContractType", "Quantity", "arze", "taghaza")
    )
    return int.from_bytes(hashlib.sha256(stable.encode("utf-8")).digest()[:8], "big") & ((1 << 63) - 1)


def classify_steel_product(row):
    searchable = " ".join(
        str(row.get(key) or "").lower()
        for key in ("GoodsName", "Symbol", "PacketName", "Talar")
    )
    for group, words in STEEL_GROUPS.items():
        if any(word in searchable for word in words):
            return group
    return None


def _sync_state_start(key):
    state, _ = MarketDataSyncState.objects.get_or_create(key=key)
    state.status = MarketDataSyncState.Status.RUNNING
    state.started_at = timezone.now()
    state.error_message = ""
    state.save(update_fields=("status", "started_at", "error_message", "updated_at"))
    return state


def _sync_state_finish(state, *, count, metadata=None):
    state.status = MarketDataSyncState.Status.SUCCESS
    state.finished_at = timezone.now()
    state.record_count = count
    state.error_message = ""
    state.metadata = metadata or {}
    state.save()


def _sync_state_error(state, exc):
    state.status = MarketDataSyncState.Status.ERROR
    state.finished_at = timezone.now()
    state.error_message = str(exc)[:2000]
    state.save(update_fields=("status", "finished_at", "error_message", "updated_at"))


def _unwrap_ime_payload(payload):
    rows = payload.get("d") if isinstance(payload, dict) else payload
    if isinstance(rows, str):
        try:
            rows = json.loads(rows)
        except json.JSONDecodeError as exc:
            raise MarketSyncError("ساختار پاسخ بورس کالا معتبر نیست.") from exc
    if isinstance(rows, dict):
        rows = rows.get("data") or rows.get("rows") or rows.get("Table")
    if not isinstance(rows, list):
        raise MarketSyncError("فهرست معاملات در پاسخ بورس کالا یافت نشد.")
    return rows


def sync_ime_market(from_jalali=None, to_jalali=None):
    state = _sync_state_start("ime")
    today = timezone.localdate()
    to_jalali = to_jalali or gregorian_to_jalali(today)
    from_jalali = from_jalali or gregorian_to_jalali(today - timedelta(days=14))
    start = jalali_to_gregorian(from_jalali)
    end = jalali_to_gregorian(to_jalali)
    if end < start or (end - start).days > MAX_IME_WINDOW_DAYS:
        exc = MarketSyncError("بازه بورس کالا باید بین صفر تا ۳۱ روز باشد.")
        _sync_state_error(state, exc)
        raise exc
    try:
        payload = _post_json(
            IME_ENDPOINT,
            {
                "Language": "0",
                "fari": "true",
                "GregorianFromDate": start.strftime("%Y/%m/%d"),
                "GregorianToDate": end.strftime("%Y/%m/%d"),
                "MainCat": "0",
                "Cat": "0",
                "SubCat": "0",
                "Producer": "0",
            },
        )
        parsed = []
        for row in _unwrap_ime_payload(payload):
            if not isinstance(row, dict):
                continue
            product_group = classify_steel_product(row)
            if not product_group:
                continue
            report_id = _ime_row_id(row)
            published_date = row.get("date") or row.get("Date")
            goods_name = str(row.get("GoodsName") or "").strip()
            if not published_date or not goods_name:
                raise MarketSyncError("یکی از شناسه، تاریخ یا نام کالا در پاسخ رسمی خالی است.")
            trade_date, trade_date_jalali = parse_ime_date(published_date)
            delivery_date = row.get("DeliveryDate")
            delivery_date_jalali = parse_ime_date(delivery_date)[1] if delivery_date else ""
            parsed.append(
                (
                    int(report_id),
                    {
                        "symbol": str(row.get("Symbol") or "").strip() or goods_name,
                        "goods_name": goods_name,
                        "product_group": product_group,
                        "producer_name": str(row.get("ProducerName") or "").strip(),
                        "hall": str(row.get("Talar") or row.get("PacketName") or "").strip(),
                        "contract_type": str(row.get("ContractType") or "").strip(),
                        "base_price": _decimal(row.get("ArzeBasePrice")),
                        "min_price": _decimal(row.get("MinPrice")),
                        "weighted_price": _decimal(row.get("Price")),
                        "max_price": _decimal(row.get("MaxPrice")),
                        "offered_volume": _decimal(row.get("arze")),
                        "demand_volume": _decimal(row.get("taghaza")),
                        "traded_volume": _decimal(row.get("Quantity")),
                        "transaction_value_thousand_rial": _decimal(row.get("TotalPrice")),
                        "currency": str(row.get("Currency") or "ریال").strip(),
                        "unit": str(row.get("Unit") or "").strip(),
                        "trade_date": trade_date,
                        "trade_date_jalali": str(trade_date_jalali),
                        "delivery_date_jalali": delivery_date_jalali,
                        "source_url": IME_SOURCE_URL,
                        "raw": {key: row.get(key) for key in row.keys() if key not in {"__type"}},
                    },
                )
            )
        with transaction.atomic():
            for report_id, defaults in parsed:
                CommodityExchangeTrade.objects.update_or_create(
                    source_report_id=report_id, defaults=defaults
                )
        _sync_state_finish(
            state,
            count=len(parsed),
            metadata={"from": from_jalali, "to": to_jalali, "source": IME_SOURCE_URL},
        )
        return len(parsed)
    except Exception as exc:
        _sync_state_error(state, exc)
        if isinstance(exc, MarketSyncError):
            raise
        raise MarketSyncError("همگام‌سازی بورس کالا ناموفق بود.") from exc


def _payload_metals(payload):
    if not isinstance(payload, dict):
        raise MarketSyncError("ساختار پاسخ ارائه‌دهنده جهانی معتبر نیست.")
    metals = payload.get("metals") or payload.get("rates") or payload.get("data")
    if not isinstance(metals, dict):
        raise MarketSyncError("قیمت فلزات در پاسخ ارائه‌دهنده یافت نشد.")
    return metals


def sync_global_metals(force=False):
    key = settings.METALS_DEV_API_KEY
    existing = MarketDataSyncState.objects.filter(key="metals_dev").first()
    if (
        key
        and not force
        and existing
        and existing.status == MarketDataSyncState.Status.SUCCESS
        and existing.finished_at
        and timezone.now() - existing.finished_at < timedelta(hours=settings.GLOBAL_METALS_MIN_REFRESH_HOURS)
    ):
        return existing.record_count
    state = _sync_state_start("metals_dev")
    if not key:
        exc = MarketSyncError("METALS_DEV_API_KEY تنظیم نشده است.")
        _sync_state_error(state, exc)
        return 0
    try:
        payload = _get_json(METALS_DEV_ENDPOINT, {"api_key": key, "currency": "USD"})
        metals = _payload_metals(payload)
        observed_at = parse_datetime(str(payload.get("timestamp") or payload.get("date") or ""))
        if observed_at is None:
            observed_at = timezone.now()
        elif timezone.is_naive(observed_at):
            observed_at = timezone.make_aware(observed_at, timezone.get_current_timezone())
        saved = 0
        with transaction.atomic():
            for sort_order, (_name, definition) in enumerate(METALS_DEV_INSTRUMENTS.items(), start=1):
                code, name_fa, name_en, exchange, aliases = definition
                raw_value = next((metals.get(alias) for alias in aliases if metals.get(alias) is not None), None)
                if isinstance(raw_value, dict):
                    raw_value = raw_value.get("price") or raw_value.get("value")
                if raw_value is None:
                    continue
                price = _decimal(raw_value, required=True)
                instrument, _ = GlobalMetalInstrument.objects.update_or_create(
                    code=code,
                    defaults={
                        "name_fa": name_fa,
                        "name_en": name_en,
                        "exchange": exchange,
                        "currency": "USD",
                        "unit": "metric_ton",
                        "sort_order": sort_order,
                        "is_active": True,
                    },
                )
                GlobalMetalObservation.objects.update_or_create(
                    instrument=instrument,
                    provider="Metals.Dev",
                    observed_on=timezone.localtime(observed_at).date(),
                    defaults={
                        "price": price,
                        "observed_at": observed_at,
                        "source_url": METALS_DEV_SOURCE_URL,
                        "raw": {"instrument": code, "value": str(raw_value)},
                    },
                )
                saved += 1
        _sync_state_finish(
            state, count=saved, metadata={"provider": "Metals.Dev", "source": METALS_DEV_SOURCE_URL}
        )
        return saved
    except Exception as exc:
        _sync_state_error(state, exc)
        if isinstance(exc, MarketSyncError):
            raise
        raise MarketSyncError("همگام‌سازی قیمت‌های جهانی ناموفق بود.") from exc


GLOBAL_CSV_REQUIRED_COLUMNS = {
    "instrument_code",
    "name_fa",
    "name_en",
    "price",
    "currency",
    "unit",
    "exchange",
    "observed_at",
    "provider",
    "source_url",
}


def import_global_metals_csv(content):
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    missing = GLOBAL_CSV_REQUIRED_COLUMNS - set(reader.fieldnames or [])
    if missing:
        raise MarketSyncError(f"ستون‌های اجباری CSV موجود نیست: {', '.join(sorted(missing))}")
    parsed = []
    for line_number, row in enumerate(reader, start=2):
        observed_at = parse_datetime((row.get("observed_at") or "").strip())
        if observed_at is None:
            raise MarketSyncError(f"تاریخ observed_at در سطر {line_number} معتبر نیست.")
        if timezone.is_naive(observed_at):
            observed_at = timezone.make_aware(observed_at, timezone.get_current_timezone())
        source_url = (row.get("source_url") or "").strip()
        if not source_url.startswith(("https://", "http://")):
            raise MarketSyncError(f"source_url در سطر {line_number} معتبر نیست.")
        parsed.append((row, observed_at, _decimal(row.get("price"), required=True), source_url))
    with transaction.atomic():
        for sort_order, (row, observed_at, price, source_url) in enumerate(parsed, start=100):
            code = (row.get("instrument_code") or "").strip().lower()
            if not code:
                raise MarketSyncError("instrument_code نمی‌تواند خالی باشد.")
            instrument, _ = GlobalMetalInstrument.objects.update_or_create(
                code=code,
                defaults={
                    "name_fa": row["name_fa"].strip(),
                    "name_en": row["name_en"].strip(),
                    "exchange": row["exchange"].strip(),
                    "currency": row["currency"].strip().upper(),
                    "unit": row["unit"].strip(),
                    "is_active": True,
                    "sort_order": sort_order,
                },
            )
            GlobalMetalObservation.objects.update_or_create(
                instrument=instrument,
                provider=row["provider"].strip(),
                observed_on=timezone.localtime(observed_at).date(),
                defaults={
                    "price": price,
                    "observed_at": observed_at,
                    "source_url": source_url,
                    "raw": {"import": "staff_csv"},
                },
            )
    return len(parsed)
