"""Shared allowlist for stored editorial HTML and historical data cleanup."""
import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_CONTENT_TAGS = [
    "a",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "figcaption",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "mark",
    "oembed",
    "ol",
    "p",
    "pre",
    "s",
    "span",
    "strong",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
]

ALLOWED_CONTENT_ATTRIBUTES = {
    "a": ["href", "rel", "target", "title"],
    "img": ["alt", "height", "src", "title", "width"],
    "oembed": ["url"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
    "*": ["class", "style"],
}

CONTENT_CSS_SANITIZER = CSSSanitizer(
    allowed_css_properties=[
        "background-color",
        "border",
        "border-color",
        "border-style",
        "border-width",
        "color",
        "height",
        "text-align",
        "vertical-align",
        "width",
    ]
)


def sanitize_content(value):
    return bleach.clean(
        value or "",
        tags=ALLOWED_CONTENT_TAGS,
        attributes=ALLOWED_CONTENT_ATTRIBUTES,
        css_sanitizer=CONTENT_CSS_SANITIZER,
        protocols=["http", "https", "mailto"],
        strip=True,
    )

