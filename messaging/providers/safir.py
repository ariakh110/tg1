"""سرویس‌دهندهٔ «سفیر» بله (ارسالِ پیام به شمارهٔ موبایل) با `urllib` خام — بدونِ وابستگیِ pip.

سفیر اجازه می‌دهد یک پیامِ بله به یک شمارهٔ موبایل بفرستی (لازم نیست کاربر ربات را استارت
کرده باشد، فقط باید حسابِ بله داشته باشد). مثلِ پیامک ولی در بله.

API: POST https://safir.bale.ai/api/v3/send_message
هدر: api-access-key. بدنه: bot_id, phone_number (با ۹۸، بدونِ صفر/کاراکترِ اضافه), message_data.
خطاها به‌جای raise در `SendResult.error` می‌نشینند.
"""
import json
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings as dj_settings

SEND_URL = "https://safir.bale.ai/api/v3/send_message"

# کدهای خطای سفیر (برای پیامِ خوانا).
ERROR_LABELS = {
    2: "خطای داخلیِ سرورِ بله",
    3: "بیش از حدِ مجاز ارسال شده",
    4: "ورودیِ نامعتبر",
    8: "شمارهٔ نامعتبر",
    17: "کاربر حسابِ بله ندارد",
    20: "اعتبارِ کافی وجود ندارد",
    21: "به سقفِ مخاطبینِ ربات رسیده‌اید",
}


def _timeout():
    return getattr(dj_settings, "OPENAI_API_TIMEOUT_SECONDS", 30)


@dataclass
class SendResult:
    ok: bool = False
    status: str = ""           # نگاشت‌شده به وضعیتِ OutboundMessage (sent/failed)
    message_id: str = ""
    error: str = ""
    raw: dict = field(default_factory=dict)


def to_safir_phone(phone09):
    """تبدیلِ شمارهٔ نرمالِ 09XXXXXXXXX به فرمتِ سفیر 989XXXXXXXXX. خالی اگر نامعتبر."""
    digits = "".join(ch for ch in str(phone09 or "") if ch.isdigit())
    if len(digits) == 11 and digits.startswith("0"):
        return "98" + digits[1:]
    if len(digits) == 12 and digits.startswith("98"):
        return digits
    if len(digits) == 10 and digits.startswith("9"):
        return "98" + digits
    return ""


def _result_from_payload(payload):
    errors = (payload or {}).get("error_data") or []
    if errors:
        first = errors[0] if isinstance(errors, list) else errors
        code = first.get("code")
        desc = first.get("description") or ERROR_LABELS.get(code, "خطای نامشخص")
        return SendResult(ok=False, status="failed", error=f"سفیر (کد {code}): {desc}", raw=payload or {})
    message_id = str((payload or {}).get("message_id") or "")
    if message_id:
        return SendResult(ok=True, status="sent", message_id=message_id, raw=payload or {})
    return SendResult(ok=False, status="failed", error="پاسخِ سفیر نامعتبر بود.", raw=payload or {})


def send_message(access_key, bot_id, phone98, text, *, request_id="", is_secure=False):
    """ارسالِ یک پیامِ متنیِ بله به یک شمارهٔ موبایل (فرمتِ ۹۸). خروجی `SendResult`."""
    if not (access_key or "").strip() or not str(bot_id or "").strip():
        return SendResult(ok=False, status="failed", error="کلید یا bot_id سفیر تنظیم نشده است.")
    if not phone98:
        return SendResult(ok=False, status="failed", error="شمارهٔ گیرنده نامعتبر است.")
    try:
        bot_id_int = int(str(bot_id).strip())
    except (TypeError, ValueError):
        return SendResult(ok=False, status="failed", error="bot_id باید عددی باشد.")

    body = {
        "bot_id": bot_id_int,
        "phone_number": str(phone98),
        "message_data": {"is_secure": bool(is_secure), "message": {"text": text}},
    }
    if request_id:
        body["request_id"] = str(request_id)

    request = Request(
        SEND_URL,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"api-access-key": access_key.strip(), "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=_timeout()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", "replace"))
            return _result_from_payload(payload)
        except Exception:  # noqa: BLE001 — بدنه JSON نبود
            return SendResult(ok=False, status="failed", error=f"خطای HTTP {exc.code} از سفیر.")
    except (URLError, TimeoutError) as exc:
        return SendResult(ok=False, status="failed", error=f"ارتباط با سفیر برقرار نشد: {getattr(exc, 'reason', exc)}")
    except Exception as exc:  # noqa: BLE001 — هیچ خطایی نباید جریانِ اصلی را بشکند
        return SendResult(ok=False, status="failed", error=f"ارسالِ سفیر ناموفق: {type(exc).__name__}: {exc}")
    return _result_from_payload(payload)
