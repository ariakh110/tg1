"""ابزارهای دستیار فروش: جستجوی محصول، برآورد قیمت، و ثبت سرنخ.

این ابزارها به مدل اجازه می‌دهند روی دادهٔ واقعیِ فروشگاه (کاتالوگ/قیمت) عمل کند.
"""
from decimal import Decimal

from django.db.models import Q


def _spec(product):
    return getattr(product, "specifications", None)


def _fmt_num(value):
    try:
        d = Decimal(str(value))
    except Exception:
        return ""
    if d == d.to_integral_value():
        return str(int(d))
    return str(d.normalize())


def _product_title(product):
    spec = _spec(product)
    if not spec:
        return product.name
    parts = []
    surface = getattr(spec, "surface_finish", "")
    if surface:
        parts.append(surface)
    if getattr(spec, "thickness_mm", None):
        parts.append(f"{_fmt_num(spec.thickness_mm)} میل")
    if getattr(spec, "width_mm", None) and getattr(spec, "length_mm", None):
        parts.append(f"عرض {_fmt_num(spec.width_mm)}×{_fmt_num(spec.length_mm)}")
    elif getattr(spec, "width_mm", None):
        parts.append(f"عرض {_fmt_num(spec.width_mm)}")
    if getattr(spec, "manufacturing_process", None):
        parts.append(spec.manufacturing_process)
    if getattr(spec, "steel_grade", None):
        parts.append(spec.steel_grade)
    if getattr(spec, "factory", None):
        parts.append(spec.factory)
    return " - ".join(p for p in parts if p) or product.name


def _min_price(product):
    prices = []
    for offer in product.offers.all():
        if getattr(offer, "is_active", True) is False:
            continue
        for tier in offer.pricing_tiers.all():
            try:
                price = Decimal(str(tier.unit_price))
            except Exception:
                continue
            if price > 0:
                prices.append(price)
    return min(prices) if prices else None


def _delivery(product):
    for offer in product.offers.all():
        options = list(offer.delivery_options.all())
        if options:
            d = options[0]
            place = {"warehouse": "انبار", "factory": "کارخانه"}.get(d.address, d.address or "")
            city = d.city or d.province or ""
            return " - ".join(p for p in [city, place] if p) or "هماهنگی"
    return "هماهنگی"


def summarize_product(product):
    spec = _spec(product)
    price = _min_price(product)
    return {
        "id": product.id,
        "title": _product_title(product),
        "grade": getattr(spec, "steel_grade", "") if spec else "",
        "factory": getattr(spec, "factory", "") if spec else "",
        "category": product.category.name if product.category_id else "",
        "thickness_mm": _fmt_num(getattr(spec, "thickness_mm", "")) if spec else "",
        "width_mm": _fmt_num(getattr(spec, "width_mm", "")) if spec else "",
        "length_mm": _fmt_num(getattr(spec, "length_mm", "")) if spec else "",
        "price_toman": str(int(price)) if price is not None else None,
        "price_status": "قیمت‌دار" if price is not None else "نیازمند استعلام",
        "delivery": _delivery(product),
        "availability": getattr(product, "availability_status", ""),
        "url": f"/products/{product.id}",
    }


def search_products(query="", grade="", kind="", max_results=5):
    from products.models import Product

    qs = (
        Product.objects.filter(is_active=True)
        .select_related("specifications", "category")
        .prefetch_related("offers__pricing_tiers", "offers__delivery_options")
    )
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(short_description__icontains=query)
            | Q(category__name__icontains=query)
            | Q(specifications__steel_grade__icontains=query)
            | Q(specifications__factory__icontains=query)
        )
    if grade:
        qs = qs.filter(specifications__steel_grade__icontains=grade)
    if kind:
        qs = qs.filter(
            Q(category__name__icontains=kind)
            | Q(specifications__manufacturing_process__icontains=kind)
            | Q(specifications__surface_finish__icontains=kind)
        )
    try:
        limit = max(1, min(int(max_results), 10))
    except Exception:
        limit = 5
    results = [summarize_product(p) for p in qs.distinct()[:limit]]
    return {"count": len(results), "products": results}


def get_price_quote(product_id, quantity=None, roll_count=None):
    from products.models import Product

    try:
        product = (
            Product.objects.select_related("specifications")
            .prefetch_related("offers__pricing_tiers")
            .get(id=product_id, is_active=True)
        )
    except Product.DoesNotExist:
        return {"error": "محصول یافت نشد."}

    price = _min_price(product)
    spec = _spec(product)
    is_coil = bool(spec and getattr(spec, "manufacturing_process", "") == "coil")
    quote = {
        "id": product.id,
        "title": _product_title(product),
        "unit_price_toman": str(int(price)) if price is not None else None,
        "price_status": "قیمت‌دار" if price is not None else "نیازمند استعلام",
        "delivery": _delivery(product),
        "url": f"/products/{product.id}",
        "note": "قیمت‌های نمایشی بدون ارزش افزوده هستند؛ ارزش افزوده هنگام نهایی‌سازی اعمال می‌شود.",
    }
    if is_coil:
        try:
            from sales.services import default_coil_weight_ton

            ton = default_coil_weight_ton(product)
            quote["roll_weight_ton"] = str(ton)
            count = int(roll_count or quantity or 1)
            if price is not None:
                total = (Decimal(str(ton)) * Decimal("1000") * Decimal(count) * price)
                quote["roll_count"] = count
                quote["estimated_total_toman"] = str(int(total))
        except Exception:
            pass
    return quote


def register_inquiry(conversation, product="", size="", grade="", factory="", quantity="", city="", note="", raw_text=""):
    """ثبت استعلام/سرنخِ ساختاریافته + تلاش برای تطبیق با کاتالوگ."""
    from .models import AssistantInquiry

    product = (product or "").strip()[:120]
    if not product:
        return {"ok": False, "error": "نوع کالا لازم است."}

    query = " ".join(p for p in [product, grade, size] if p).strip()
    found = search_products(query=query, grade=grade, kind=product, max_results=1)
    match = (found.get("products") or [None])[0]
    matched_price = None
    if match and match.get("price_toman"):
        try:
            matched_price = int(match["price_toman"])
        except (TypeError, ValueError):
            matched_price = None

    inquiry = AssistantInquiry.objects.create(
        conversation=conversation,
        product=product,
        size=(size or "").strip()[:60],
        grade=(grade or "").strip()[:60],
        factory=(factory or "").strip()[:80],
        quantity=(quantity or "").strip()[:60],
        city=(city or "").strip()[:80],
        note=(note or "").strip()[:255],
        raw_text=(raw_text or "").strip(),
        matched_product_id=(match or {}).get("id"),
        matched_price=matched_price,
        contact_name=conversation.lead_name if conversation else "",
        contact_phone=conversation.lead_phone if conversation else "",
    )
    if conversation and conversation.status == conversation.STATUS_OPEN:
        conversation.status = conversation.STATUS_LEAD
        conversation.save(update_fields=["status", "updated_at"])

    # هر درخواستِ جدید را به گروه/ادمین خبر بده (و اگر شماره داریم، سرنخ را هم به CRM ببر).
    if conversation:
        try:
            from messaging.events import on_chat_inquiry

            on_chat_inquiry(conversation, inquiry)
        except Exception:  # noqa: BLE001
            pass

    return {
        "ok": True,
        "inquiry_id": inquiry.id,
        "matched_product": match,
        "message": "استعلام ثبت شد.",
    }


def capture_lead(conversation, name="", phone="", interest=""):
    from customers.services import normalize_phone

    name = (name or "").strip()[:120]
    interest = (interest or "").strip()[:255]
    norm = normalize_phone(phone)
    if not (len(norm) == 11 and norm.startswith("09")):
        return {"ok": False, "error": "شمارهٔ موبایلِ معتبر (با ۰۹ و ۱۱ رقم) لازم است؛ از مشتری بخواه کامل بدهد."}
    if not name:
        return {"ok": False, "error": "نام و نام‌خانوادگی لازم است؛ از مشتری بپرس."}
    phone = norm
    conversation.lead_name = name or conversation.lead_name
    conversation.lead_phone = phone
    conversation.lead_interest = interest or conversation.lead_interest
    conversation.status = conversation.STATUS_LEAD
    conversation.save(update_fields=["lead_name", "lead_phone", "lead_interest", "status", "updated_at"])

    # سرنخ را به CRM ببر و به ادمین خبر بده (امن: هیچ خطایی پاسخِ چت را نمی‌شکند).
    try:
        from messaging.events import on_chat_lead

        on_chat_lead(conversation)
    except Exception:  # noqa: BLE001
        pass

    return {"ok": True, "message": "سرنخ ثبت شد. کارشناس فروش تماس می‌گیرد."}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "جستجوی محصولات فروشگاه (ورق، رول، تیرآهن، میلگرد، لوله، پروفیل...) بر اساس کلیدواژه، گرید/آلیاژ یا نوع کالا. برای معرفی محصول و قیمت استفاده کن.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "کلیدواژهٔ آزاد مثل نام، ضخامت، کارخانه"},
                    "grade": {"type": "string", "description": "گرید/آلیاژ مثل ST37 یا ST52 یا CK45"},
                    "kind": {"type": "string", "description": "نوع کالا مثل ورق، رول، تیرآهن، میلگرد"},
                    "max_results": {"type": "integer", "description": "حداکثر تعداد نتیجه (پیش‌فرض ۵)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_quote",
            "description": "دریافت قیمت و برآورد فاکتور یک محصول مشخص بر اساس شناسهٔ آن (و برای رول، وزن هر رول).",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "شناسهٔ محصول از نتایج جستجو"},
                    "roll_count": {"type": "integer", "description": "تعداد رول برای محصولات رول"},
                    "quantity": {"type": "number", "description": "مقدار درخواستی"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "register_inquiry",
            "description": "وقتی مشتری یک نیازِ مشخص می‌گوید (مثل «۲۰ تن میلگرد ۱۴ اصفهان»)، آن را به‌صورت ساختاریافته ثبت کن. هر فیلدی که در متن آمده را پر کن.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string", "description": "نوع کالا مثل میلگرد، ورق، تیرآهن، لوله"},
                    "size": {"type": "string", "description": "سایز یا ضخامت مثل 14 یا 3 میل"},
                    "grade": {"type": "string", "description": "گرید/آلیاژ مثل ST37 یا A3"},
                    "factory": {"type": "string", "description": "کارخانه یا مبدا مثل اصفهان، ذوب‌آهن"},
                    "quantity": {"type": "string", "description": "مقدار مثل 20 تن"},
                    "city": {"type": "string", "description": "شهر مشتری یا محل تحویل"},
                    "note": {"type": "string", "description": "توضیح اضافه"},
                    "raw_text": {"type": "string", "description": "عین جملهٔ مشتری"},
                },
                "required": ["product"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capture_lead",
            "description": "ثبت سرنخ فروش. نام و نام‌خانوادگیِ کامل و شمارهٔ موبایلِ مشتری را بگیر و این ابزار را صدا بزن.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "نام و نام‌خانوادگیِ کاملِ مشتری"},
                    "phone": {"type": "string", "description": "شمارهٔ موبایلِ مشتری (۰۹ و ۱۱ رقم)"},
                    "interest": {"type": "string", "description": "محصول/نیاز موردنظر مشتری"},
                },
                "required": ["name", "phone"],
            },
        },
    },
]


def execute_tool(name, args, conversation, *, lead_capture_enabled=True, lead_gate="off"):
    args = args or {}
    if name == "search_products":
        return search_products(
            query=args.get("query", ""),
            grade=args.get("grade", ""),
            kind=args.get("kind", ""),
            max_results=args.get("max_results", 5),
        )
    if name == "get_price_quote":
        # حالتِ «اجباری»: قیمتِ دقیق تا قبل از گرفتنِ نام و موبایل داده نمی‌شود.
        if lead_gate == "strict" and conversation and not (conversation.lead_phone or "").strip():
            return {
                "gated": True,
                "message": "قبل از اعلامِ قیمت، نام و نام‌خانوادگی و شمارهٔ موبایلِ مشتری را بگیر و با ابزار capture_lead ثبت کن، سپس دوباره قیمت را بخواه.",
            }
        return get_price_quote(
            product_id=args.get("product_id"),
            quantity=args.get("quantity"),
            roll_count=args.get("roll_count"),
        )
    if name == "register_inquiry":
        return register_inquiry(
            conversation,
            product=args.get("product", ""),
            size=args.get("size", ""),
            grade=args.get("grade", ""),
            factory=args.get("factory", ""),
            quantity=args.get("quantity", ""),
            city=args.get("city", ""),
            note=args.get("note", ""),
            raw_text=args.get("raw_text", ""),
        )
    if name == "capture_lead":
        if not lead_capture_enabled:
            return {"ok": False, "error": "ثبت سرنخ غیرفعال است."}
        return capture_lead(
            conversation,
            name=args.get("name", ""),
            phone=args.get("phone", ""),
            interest=args.get("interest", ""),
        )
    return {"error": f"ابزار ناشناخته: {name}"}
