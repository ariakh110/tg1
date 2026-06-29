"""سرویس‌دهندهٔ پیامکِ کاوه‌نگار (REST/JSON) با `urllib` خام — بدونِ وابستگیِ pip جدید.

دو حالتِ ارسال (مطابقِ `openspec/sms-kavenegar-api-doc/api-doc.md`):
- `sms/send` : پیامکِ متنیِ آزاد (نیاز به خطِ فرستنده؛ ممکن است فیلترِ تبلیغاتی بخورد) — برای پیامکِ عمومیِ CRM.
- `verify/lookup` : مبتنی بر الگو، بالاترین اولویت، فیلترنشده — برای پیامکِ تراکنشی/مراحلِ خرید.

پاسخِ کاوه‌نگار پاکتی به شکلِ {"return": {status, message}, "entries": [...]} دارد؛
خطاهای سرویس (اعتبارِ ناکافی، گیرندهٔ نامعتبر و ...) به‌جای raise در `SendResult.error` می‌نشینند.
"""
import json
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings as dj_settings

BASE_URL = "https://api.kavenegar.com/v1"


def _timeout():
    return getattr(dj_settings, "OPENAI_API_TIMEOUT_SECONDS", 30)


@dataclass
class SendResult:
    ok: bool = False
    status: str = ""           # نگاشت‌شده به وضعیتِ OutboundMessage (sent/failed)
    message_id: str = ""
    cost: object = None        # هزینه (ریال) یا None
    error: str = ""
    raw: dict = field(default_factory=dict)


def _post(api_key, method_path, params):
    """فراخوانیِ یک متدِ کاوه‌نگار با POST (بدنهٔ urlencode؛ متنِ فارسی امن کد می‌شود)."""
    url = f"{BASE_URL}/{api_key}/{method_path}.json"
    data = urlencode({k: v for k, v in params.items() if v not in (None, "")}).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urlopen(request, timeout=_timeout()) as response:
        return json.loads(response.read().decode("utf-8"))


def _result_from_payload(payload):
    ret = (payload or {}).get("return") or {}
    api_status = ret.get("status")
    if api_status != 200:
        return SendResult(
            ok=False, status="failed",
            error=f"کاوه‌نگار (کد {api_status}): {ret.get('message') or 'بدون جزئیات'}",
            raw=payload or {},
        )
    entries = (payload or {}).get("entries") or []
    entry = entries[0] if entries else {}
    return SendResult(
        ok=True, status="sent",
        message_id=str(entry.get("messageid", "")),
        cost=entry.get("cost"),
        raw=payload or {},
    )


def _safe_call(api_key, method_path, params):
    try:
        payload = _post(api_key, method_path, params)
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", "replace"))
            return _result_from_payload(payload)
        except Exception:  # noqa: BLE001 — بدنه JSON نبود
            return SendResult(ok=False, status="failed", error=f"خطای HTTP {exc.code} از کاوه‌نگار.")
    except (URLError, TimeoutError) as exc:
        return SendResult(ok=False, status="failed", error=f"ارتباط با کاوه‌نگار برقرار نشد: {getattr(exc, 'reason', exc)}")
    except Exception as exc:  # noqa: BLE001 — هیچ خطایی نباید کلِ درخواست را ۵۰۰ کند
        return SendResult(ok=False, status="failed", error=f"ارسال ناموفق بود: {type(exc).__name__}: {exc}")
    return _result_from_payload(payload)


def send_sms(api_key, receptor, message, sender=""):
    """ارسالِ متنیِ ساده (sms/send)."""
    return _safe_call(api_key, "sms/send", {"receptor": receptor, "message": message, "sender": sender})


def send_lookup(api_key, receptor, template, token, token2="", token3=""):
    """ارسالِ مبتنی بر الگو (verify/lookup) — فیلترنشده، برای پیامکِ تراکنشی."""
    return _safe_call(
        api_key, "verify/lookup",
        {"receptor": receptor, "template": template, "token": token, "token2": token2, "token3": token3},
    )


def get_status(api_key, message_id):
    """واکشیِ وضعیتِ تحویلِ یک پیامک (sms/status)؛ خروجی خامِ کاوه‌نگار."""
    return _safe_call(api_key, "sms/status", {"messageid": message_id})
