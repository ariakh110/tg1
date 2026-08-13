from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit


ALLOWED_TAGS = {
    "section",
    "article",
    "div",
    "p",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "strong",
    "b",
    "em",
    "i",
    "a",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "blockquote",
    "figure",
    "figcaption",
    "img",
    "br",
    "hr",
}
VOID_TAGS = {"br", "hr", "img"}
BLOCKED_TAGS = {"script", "style", "iframe", "object", "embed", "form"}
ALLOWED_ATTRIBUTES = {
    "section": {"id"},
    "article": {"id"},
    "div": {"id"},
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height", "loading"},
    "th": {"colspan", "rowspan", "scope"},
    "td": {"colspan", "rowspan"},
}


def _safe_url(value):
    value = str(value or "").strip()
    if not value:
        return ""
    if value.startswith("#") or (value.startswith("/") and not value.startswith("//")):
        return value
    parsed = urlsplit(value)
    if parsed.scheme.lower() in {"http", "https", "mailto", "tel"}:
        return value
    return ""


class _ProductContentSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.blocked_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in BLOCKED_TAGS:
            self.blocked_depth += 1
            return
        if self.blocked_depth:
            return
        if tag == "h1":
            tag = "h2"
        if tag not in ALLOWED_TAGS:
            return

        clean_attrs = []
        allowed = ALLOWED_ATTRIBUTES.get(tag, set())
        for key, value in attrs:
            key = key.lower()
            if key not in allowed or key.startswith("on"):
                continue
            value = str(value or "").strip()
            if key in {"href", "src"}:
                value = _safe_url(value)
                if not value:
                    continue
            if key == "target" and value != "_blank":
                continue
            if key in {"colspan", "rowspan"} and not value.isdigit():
                continue
            if key in {"width", "height"} and not value.isdigit():
                continue
            if key == "loading" and value not in {"lazy", "eager"}:
                continue
            clean_attrs.append(f' {key}="{escape(value, quote=True)}"')
        if tag == "a" and any(key == "target" and value == "_blank" for key, value in attrs):
            clean_attrs.append(' rel="noopener noreferrer"')
        self.parts.append(f"<{tag}{''.join(clean_attrs)}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        normalized = "h2" if tag.lower() == "h1" else tag.lower()
        if normalized not in VOID_TAGS and normalized in ALLOWED_TAGS:
            self.parts.append(f"</{normalized}>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in BLOCKED_TAGS:
            self.blocked_depth = max(0, self.blocked_depth - 1)
            return
        if self.blocked_depth:
            return
        if tag == "h1":
            tag = "h2"
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.blocked_depth:
            self.parts.append(escape(data))


def sanitize_product_content_html(value):
    parser = _ProductContentSanitizer()
    parser.feed(str(value or ""))
    parser.close()
    return "".join(parser.parts).strip()


def sanitize_plain_text(value, max_length):
    text = " ".join(str(value or "").replace("\u200c", " ").split())
    if "<" in text or ">" in text:
        parser = _ProductContentSanitizer()
        parser.feed(text)
        text = " ".join("".join(parser.parts).replace("<", " <").split())
        while "<" in text and ">" in text:
            start = text.find("<")
            end = text.find(">", start)
            if end < 0:
                break
            text = text[:start] + " " + text[end + 1 :]
        text = " ".join(text.split())
    return text[:max_length]
