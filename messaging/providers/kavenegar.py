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
    return _results_from_payload(payload, 1)[0]


def _results_from_payload(payload, expected_count):
    ret = (payload or {}).get("return") or {}
    api_status = ret.get("status")
    if api_status != 200:
        error = f"کاوه‌نگار (کد {api_status}): {ret.get('message') or 'بدون جزئیات'}"
        return [
            SendResult(ok=False, status="failed", error=error, raw=payload or {})
            for _ in range(expected_count)
        ]
    entries = (payload or {}).get("entries") or []
    results = []
    for index in range(expected_count):
        entry = entries[index] if index < len(entries) else None
        if entry is None:
            results.append(
                SendResult(
                    ok=False,
                    status="failed",
                    error="کاوه‌نگار برای این گیرنده نتیجه‌ای برنگرداند.",
                    raw=payload or {},
                )
            )
            continue
        results.append(
            SendResult(
                ok=True,
                status="sent",
                message_id=str(entry.get("messageid", "")),
                cost=entry.get("cost"),
                raw={"return": ret, "entry": entry},
            )
        )
    return results


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


def send_sms(api_key, receptor, message, sender="", tag=""):
    """ارسالِ متنیِ ساده (sms/send)."""
    return _safe_call(
        api_key,
        "sms/send",
        {"receptor": receptor, "message": message, "sender": sender, "tag": tag},
    )


def send_sms_many(api_key, receptors, message, sender="", tag=""):
    """Send one text to up to 200 explicit receptors in a single Kavenegar request."""
    receptors = [str(value).strip() for value in receptors if str(value).strip()]
    if not receptors:
        return []
    if len(receptors) > 200:
        error = "حداکثر ۲۰۰ گیرنده در هر درخواست کاوه‌نگار مجاز است."
        return [SendResult(ok=False, status="failed", error=error) for _ in receptors]
    try:
        payload = _post(
            api_key,
            "sms/send",
            {"receptor": ",".join(receptors), "message": message, "sender": sender, "tag": tag},
        )
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", "replace"))
            return _results_from_payload(payload, len(receptors))
        except Exception:  # noqa: BLE001
            error = f"خطای HTTP {exc.code} از کاوه‌نگار."
    except (URLError, TimeoutError) as exc:
        error = f"ارتباط با کاوه‌نگار برقرار نشد: {getattr(exc, 'reason', exc)}"
    except Exception as exc:  # noqa: BLE001
        error = f"ارسال ناموفق بود: {type(exc).__name__}: {exc}"
    else:
        return _results_from_payload(payload, len(receptors))
    return [SendResult(ok=False, status="failed", error=error) for _ in receptors]


def send_lookup(api_key, receptor, template, token, token2="", token3=""):
    """ارسالِ مبتنی بر الگو (verify/lookup) — فیلترنشده، برای پیامکِ تراکنشی."""
    return _safe_call(
        api_key, "verify/lookup",
        {"receptor": receptor, "template": template, "token": token, "token2": token2, "token3": token3},
    )


def get_status(api_key, message_id):
    """واکشیِ وضعیتِ تحویلِ یک پیامک (sms/status)؛ خروجی خامِ کاوه‌نگار."""
    return _safe_call(api_key, "sms/status", {"messageid": message_id})
