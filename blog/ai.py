import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils.html import strip_tags


class AIContentSuggestionError(Exception):
    pass


SUGGESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "excerpt": {"type": "string"},
        "focus_keyword": {"type": "string"},
        "secondary_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 8,
        },
    },
    "required": ["excerpt", "focus_keyword", "secondary_keywords"],
    "additionalProperties": False,
}


def _response_text(payload):
    for output in payload.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "")
    raise AIContentSuggestionError("پاسخ هوش مصنوعی قابل پردازش نبود.")


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

    site_settings = SiteSettings.load()
    api_key = (site_settings.openai_api_key or getattr(settings, "OPENAI_API_KEY", "")).strip()
    if not api_key:
        raise AIContentSuggestionError("کلید OPENAI_API_KEY برای تولید پیشنهاد تنظیم نشده است.")

    plain_content = " ".join(strip_tags(content or "").split())[:12000]
    if not plain_content:
        raise AIContentSuggestionError("برای دریافت پیشنهاد، ابتدا متن اصلی مطلب را وارد کنید.")

    prompt = (
        "برای مطلب فارسی زیر، یک خلاصه دقیق و قابل ویرایش برای نویسنده، یک کلیدواژه اصلی "
        "و حداکثر هشت کلیدواژه فرعی پیشنهاد بده. خلاصه حداکثر ۳۲۰ کاراکتر باشد و "
        "اطلاعاتی خارج از متن اضافه نکن.\n\n"
        f"عنوان: {title.strip()}\n\nمتن مطلب:\n{plain_content}"
    )
    body = {
        "model": (site_settings.openai_content_model or getattr(settings, "OPENAI_CONTENT_MODEL", "gpt-5-mini")),
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "content_metadata_suggestions",
                "strict": True,
                "schema": SUGGESTION_SCHEMA,
            }
        },
    }
    request = Request(
        "https://api.openai.com/v1/responses",
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
        return _clean_suggestions(json.loads(_response_text(payload)))
    except json.JSONDecodeError as exc:
        raise AIContentSuggestionError("پاسخ هوش مصنوعی قابل پردازش نبود.") from exc
