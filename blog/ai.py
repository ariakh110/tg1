import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils.html import strip_tags


class AIContentSuggestionError(Exception):
    pass


def _clean_suggestions(value):
    if not isinstance(value, dict):
        raise AIContentSuggestionError("ساختار پیشنهاد هوش مصنوعی معتبر نبود.")
    keywords = value.get("secondary_keywords", [])
    if not isinstance(keywords, list):
        keywords = []
    return {
        "excerpt": str(value.get("excerpt", "")).strip()[:500],
        "focus_keyword": str(value.get("focus_keyword", "")).strip()[:100],
        "secondary_keywords": [
            str(keyword).strip()[:100]
            for keyword in keywords[:8]
            if str(keyword).strip()
        ],
    }


def generate_content_suggestions(title, content):
    from core.models import SiteSettings
    from assistant.models import AssistantSettings

    site_settings = SiteSettings.load()
    api_key = (site_settings.openai_api_key or getattr(settings, "OPENAI_API_KEY", "")).strip()
    if not api_key:
        raise AIContentSuggestionError("کلید OPENAI_API_KEY برای تولید پیشنهاد تنظیم نشده است.")

    plain_content = " ".join(strip_tags(content or "").split())[:12000]
    if not plain_content:
        raise AIContentSuggestionError("برای دریافت پیشنهاد، ابتدا متن اصلی مطلب را وارد کنید.")

    # از همان نقطهٔ پایانیِ سازگار با OpenAI که برای دستیار تنظیم شده استفاده می‌کنیم
    # (base_url قابل‌تنظیم؛ مثلاً گیت‌وی ایرانیِ AvalAI تا از ایران هم کار کند).
    cfg = AssistantSettings.load()
    base = (cfg.openai_base_url or "https://api.openai.com/v1").rstrip("/")
    model = (
        (site_settings.openai_content_model or "").strip()
        or (cfg.chat_model or "").strip()
        or "gpt-4o-mini"
    )

    system_prompt = (
        "تو دستیار سئوی فارسی هستی. خروجی را فقط به‌صورت یک شیء JSON بده با کلیدهای: "
        "excerpt (رشته، خلاصهٔ دقیق و قابل ویرایش، حداکثر ۳۲۰ کاراکتر)، "
        "focus_keyword (رشته)، و secondary_keywords (آرایه‌ای از رشته، حداکثر ۸). "
        "اطلاعاتی خارج از متن اضافه نکن."
    )
    user_prompt = f"عنوان: {title.strip()}\n\nمتن مطلب:\n{plain_content}"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }
    request = Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(
            request,
            timeout=getattr(settings, "OPENAI_API_TIMEOUT_SECONDS", 30),
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise AIContentSuggestionError("سرویس هوش مصنوعی درخواست را نپذیرفت. تنظیمات API را بررسی کنید.") from exc
    except (URLError, TimeoutError) as exc:
        raise AIContentSuggestionError("ارتباط با سرویس هوش مصنوعی برقرار نشد.") from exc
    except json.JSONDecodeError as exc:
        raise AIContentSuggestionError("پاسخ هوش مصنوعی قابل پردازش نبود.") from exc

    try:
        message = payload["choices"][0]["message"]["content"]
        return _clean_suggestions(json.loads(message))
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise AIContentSuggestionError("پاسخ هوش مصنوعی قابل پردازش نبود.") from exc
