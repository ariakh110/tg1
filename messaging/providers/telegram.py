"""سرویس‌دهندهٔ ربات تلگرام/بله (Bot API) با `urllib` خام — بدونِ وابستگیِ pip جدید.

برای اطلاع‌رسانیِ ادمین (sendMessage) و ربات دوطرفه (setWebhook/answerCallbackQuery و …)
استفاده می‌شود. خطاها به‌جای raise در `SendResult.error` می‌نشینند تا هیچ‌وقت جریانِ
اصلیِ سایت را نشکنند.

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
        result = (payload or {}).get("result")
        message_id = str(result.get("message_id", "")) if isinstance(result, dict) else ""
        return SendResult(ok=True, status="sent", message_id=message_id, raw=payload or {})
    desc = (payload or {}).get("description") or "بدون جزئیات"
    return SendResult(ok=False, status="failed", error=f"بله/تلگرام: {desc}", raw=payload or {})


def _call(token, method, params, *, base_url=""):
    """یک متدِ Bot API را با POST صدا می‌زند و `SendResult` برمی‌گرداند (هیچ‌وقت raise نمی‌کند)."""
    token = (token or "").strip()
    if not token:
        return SendResult(ok=False, status="failed", error="توکن خالی است.")
    root = (base_url or "").strip().rstrip("/") or BASE_URL
    url = f"{root}/bot{token}/{method}"
    data = urlencode({k: v for k, v in params.items() if v not in (None, "")}).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with urlopen(request, timeout=_timeout()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", "replace"))
            return _result_from_payload(payload)
        except Exception:  # noqa: BLE001 — بدنه JSON نبود
            return SendResult(ok=False, status="failed", error=f"خطای HTTP {exc.code} از بله/تلگرام.")
    except (URLError, TimeoutError) as exc:
        return SendResult(ok=False, status="failed", error=f"ارتباط برقرار نشد: {getattr(exc, 'reason', exc)}")
    except Exception as exc:  # noqa: BLE001 — هیچ خطایی نباید جریانِ اصلی را بشکند
        return SendResult(ok=False, status="failed", error=f"درخواست ناموفق: {type(exc).__name__}: {exc}")
    return _result_from_payload(payload)


def send_message(token, chat_id, text, *, parse_mode="", base_url="", reply_markup=None):
    """ارسالِ یک پیام به یک chat_id با sendMessage.

    `reply_markup` یک dict (مثلاً InlineKeyboardMarkup) است که JSON-سریال می‌شود — برای
    دکمه‌های این‌لاینِ روی پیام. خالی ⇒ بدونِ دکمه.
    """
    chat_id = str(chat_id or "").strip()
    if not chat_id:
        return SendResult(ok=False, status="failed", error="chat_id خالی است.")
    params = {"chat_id": chat_id, "text": text}
    if parse_mode:
        params["parse_mode"] = parse_mode
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    return _call(token, "sendMessage", params, base_url=base_url)


def answer_callback_query(token, callback_query_id, text="", *, base_url=""):
    """پاسخ به کلیکِ روی دکمهٔ این‌لاین (حذفِ لودینگ + نمایشِ یک toast کوتاه)."""
    return _call(token, "answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text}, base_url=base_url)


def set_webhook(token, webhook_url, *, base_url=""):
    """تعیینِ آدرسِ وب‌هوک تا آپدیت‌های ربات به بک‌اند ارسال شوند. رشتهٔ خالی ⇒ حذفِ وب‌هوک."""
    return _call(token, "setWebhook", {"url": webhook_url}, base_url=base_url)


def get_webhook_info(token, *, base_url=""):
    """وضعیتِ فعلیِ وب‌هوک (برای نمایش/عیب‌یابی)."""
    return _call(token, "getWebhookInfo", {}, base_url=base_url)
