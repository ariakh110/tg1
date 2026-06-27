"""ابزارهای دستیار سئو.

`fetch_page_seo`: یک URL زنده را واکشی و سیگنال‌های on-page آن را استخراج می‌کند
(عنوان، meta description، canonical، meta robots، H1/H2، کد وضعیت HTTP، شمارش کلمات/لینک‌ها)
تا دستیار بتواند صفحات واقعیِ سایت (مثلاً تیرکسا) را آدیت کند. فقط stdlib.
"""
import re
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings as dj_settings

MAX_BYTES = 1_500_000  # سقف دانلود (~1.5MB) برای جلوگیری از صفحات سنگین


def _timeout():
    return getattr(dj_settings, "OPENAI_API_TIMEOUT_SECONDS", 30)


class _SeoHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta_description = ""
        self.meta_robots = ""
        self.canonical = ""
        self.h1 = []
        self.h2 = []
        self.link_count = 0
        self._capture = None  # "title" | "h1" | "h2"
        self._buf = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._capture, self._buf = "title", []
        elif tag in ("h1", "h2"):
            self._capture, self._buf = tag, []
        elif tag == "a" and a.get("href"):
            self.link_count += 1
        elif tag == "meta":
            name = a.get("name", "").lower()
            if name == "description" and not self.meta_description:
                self.meta_description = a.get("content", "").strip()
            elif name == "robots" and not self.meta_robots:
                self.meta_robots = a.get("content", "").strip()
        elif tag == "link" and a.get("rel", "").lower() == "canonical":
            self.canonical = a.get("href", "").strip()

    def handle_endtag(self, tag):
        if self._capture and tag == self._capture:
            text = "".join(self._buf).strip()
            if tag == "title":
                self.title = text
            elif tag == "h1":
                self.h1.append(text)
            elif tag == "h2":
                self.h2.append(text)
            self._capture, self._buf = None, []

    def handle_data(self, data):
        if self._capture:
            self._buf.append(data)


def _visible_word_count(html):
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return len(text.split())


def fetch_page_seo(url):
    url = (url or "").strip()
    if not url:
        return {"error": "آدرس صفحه لازم است."}
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    if not re.match(r"^https?://[^\s]+$", url, re.I):
        return {"error": "آدرس نامعتبر است."}

    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (SEO-Assistant; +tirexa)"}, method="GET")
    try:
        with urlopen(request, timeout=_timeout()) as response:
            status_code = getattr(response, "status", None) or response.getcode()
            final_url = response.geturl()
            ctype = response.headers.get("Content-Type", "")
            raw = response.read(MAX_BYTES)
    except HTTPError as exc:
        return {"url": url, "status_code": exc.code, "error": f"صفحه با خطای HTTP {exc.code} پاسخ داد."}
    except (URLError, TimeoutError) as exc:
        return {"url": url, "error": f"ارتباط با صفحه برقرار نشد: {getattr(exc, 'reason', exc)}"}
    except Exception as exc:  # noqa: BLE001 — هر خطای غیرمنتظره (قطع اتصال/SSL هنگام read، …) نباید کلِ گفتگو را ۵۰۰ کند
        return {"url": url, "error": f"واکشی صفحه ناموفق بود: {type(exc).__name__}: {exc}"}

    if "html" not in (ctype or "").lower():
        return {"url": final_url, "status_code": status_code, "content_type": ctype,
                "note": "محتوای صفحه HTML نیست؛ تحلیل on-page انجام نشد."}

    charset = "utf-8"
    m = re.search(r"charset=([\w\-]+)", ctype or "", re.I)
    if m:
        charset = m.group(1)
    try:
        html = raw.decode(charset, errors="replace")
    except (LookupError, TypeError):
        html = raw.decode("utf-8", errors="replace")

    parser = _SeoHTMLParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    title_len = len(parser.title)
    desc_len = len(parser.meta_description)
    return {
        "url": final_url,
        "status_code": status_code,
        "title": parser.title,
        "title_length": title_len,
        "title_ok": 0 < title_len <= 60,
        "meta_description": parser.meta_description,
        "meta_description_length": desc_len,
        "meta_description_ok": 120 <= desc_len <= 160,
        "canonical": parser.canonical,
        "meta_robots": parser.meta_robots,
        "h1": parser.h1[:10],
        "h1_count": len(parser.h1),
        "h2": parser.h2[:15],
        "h2_count": len(parser.h2),
        "word_count": _visible_word_count(html),
        "link_count": parser.link_count,
        "notes": [n for n in [
            "بیش از یک H1 دارد." if len(parser.h1) > 1 else "",
            "H1 ندارد." if len(parser.h1) == 0 else "",
            "title بلندتر از ۶۰ کاراکتر است." if title_len > 60 else "",
            "title ندارد." if title_len == 0 else "",
            "meta description ندارد." if desc_len == 0 else "",
            "meta description بلندتر از ۱۶۰ کاراکتر است." if desc_len > 160 else "",
            "canonical ندارد." if not parser.canonical else "",
            "noindex دارد!" if "noindex" in parser.meta_robots.lower() else "",
            "محتوای متنی کم است (<۳۰۰ کلمه)." if _visible_word_count(html) < 300 else "",
        ] if n],
    }


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_page_seo",
            "description": (
                "واکشی یک صفحهٔ وب زنده و استخراج سیگنال‌های on-page سئو: عنوان (title) و طولش، "
                "meta description و طولش، canonical، meta robots (noindex؟)، H1 و H2ها، کد وضعیت HTTP، "
                "تعداد کلمات و لینک‌ها. وقتی کاربر می‌خواهد یک URL مشخص را آدیت کنی از این ابزار استفاده کن."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "آدرس کامل صفحه برای آدیت، مثل https://example.com/page"}
                },
                "required": ["url"],
            },
        },
    },
]


def execute_tool(name, args, conversation):
    args = args or {}
    if name == "fetch_page_seo":
        return fetch_page_seo(args.get("url", ""))
    return {"error": f"ابزار ناشناخته: {name}"}
