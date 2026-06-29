"""سرویس‌دهندهٔ ربات تلگرام (Bot API) با `urllib` خام — بدونِ وابستگیِ pip جدید.

برای اطلاع‌رسانیِ آنیِ ادمین استفاده می‌شود (sendMessage). توکنِ ربات از BotFather گرفته
می‌شود و chat_id مقصدِ پیام است. خطاها به‌جای raise در `SendResult.error` می‌نشینند تا
هیچ‌وقت جریانِ اصلیِ سایت (ثبت‌نام/خرید/چت) را نشکنند.

با تغییرِ `base_url` با هر API هم‌شکلِ تلگرام کار می‌کند — مثلِ «بله» (`https://tapi.bale.ai`)
که بومیِ ایران است و از سرورِ داخلِ ایران مستقیم در دسترس است. `parse_mode` پیش‌فرض
خالی است (متنِ ساده) تا روی همهٔ این APIها یکسان و تمیز نمایش داده شود.
"""
import json
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings as dj_settings

BASE_URL = "https://api.telegram.org"


def _timeout():
    return getattr(dj_settings, "OPENAI_API_TIMEOUT_SECONDS", 30)


@dataclass
class SendResult:
    ok: bool = False
    status: str = ""           # نگاشت‌شده به وضعیتِ OutboundMessage (sent/failed)
    message_id: str = ""
    error: str = ""
    raw: dict = field(default_factory=dict)


def _result_from_payload(payload):
    if (payload or {}).get("ok"):
        result = (payload or {}).get("result") or {}
        return SendResult(ok=True, status="sent", message_id=str(result.get("message_id", "")), raw=payload or {})
    desc = (payload or {}).get("description") or "بدون جزئیات"
    return SendResult(ok=False, status="failed", error=f"تلگرام: {desc}", raw=payload or {})


def send_message(token, chat_id, text, *, parse_mode="", base_url=""):
    """ارسالِ یک پیام به یک chat_id با sendMessage. خروجی `SendResult`.

    `base_url` می‌تواند به یک واسطِ بازفرست (Cloudflare Worker/پروکسی) یا یک API هم‌شکل
    مثلِ «بله» اشاره کند تا از سرورِ داخلِ ایران هم کار کند. خالی ⇒ ریشهٔ پیش‌فرضِ تلگرام.
    `parse_mode` فقط اگر مقدار داشته باشد فرستاده می‌شود (خالی ⇒ متنِ ساده، سازگار با همه).
    """
    token = (token or "").strip()
    chat_id = str(chat_id or "").strip()
    if not token or not chat_id:
        return SendResult(ok=False, status="failed", error="توکن یا chat_id خالی است.")

    root = (base_url or "").strip().rstrip("/") or BASE_URL
    url = f"{root}/bot{token}/sendMessage"
    params = {"chat_id": chat_id, "text": text}
    if parse_mode:
        params["parse_mode"] = parse_mode
    data = urlencode(params).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with urlopen(request, timeout=_timeout()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", "replace"))
            return _result_from_payload(payload)
        except Exception:  # noqa: BLE001 — بدنه JSON نبود
            return SendResult(ok=False, status="failed", error=f"خطای HTTP {exc.code} از تلگرام.")
    except (URLError, TimeoutError) as exc:
        return SendResult(ok=False, status="failed", error=f"ارتباط با تلگرام برقرار نشد: {getattr(exc, 'reason', exc)}")
    except Exception as exc:  # noqa: BLE001 — هیچ خطایی نباید جریانِ اصلی را بشکند
        return SendResult(ok=False, status="failed", error=f"ارسالِ تلگرام ناموفق: {type(exc).__name__}: {exc}")
    return _result_from_payload(payload)
