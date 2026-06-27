import re
from html import unescape
from urllib.parse import urljoin

from django.conf import settings
from django.utils.html import strip_tags


CHECKS = (
    ("keyword_title", "کلیدواژه در ابتدای عنوان", 15),
    ("keyword_description", "کلیدواژه در توضیحات متا", 10),
    ("keyword_slug", "کلیدواژه در آدرس صفحه", 10),
    ("keyword_h1", "یک تیتر H1 شامل کلیدواژه", 15),
    ("image_alt", "متن جایگزین تصاویر", 10),
    ("content_length", "حداقل ۳۰۰ کلمه محتوا", 10),
    ("internal_links", "حداقل دو لینک داخلی", 10),
    ("keyword_density", "تراکم کلیدواژه بین ۰.۵٪ تا ۲.۵٪", 10),
    ("schema", "داده ساخت‌یافته فعال", 10),
)


def plain_text(html):
    return " ".join(unescape(strip_tags(html or "")).split())


def post_path(post):
    category = post.categories.first()
    category_slug = category.slug if category else "general"
    return f"/blog/{category_slug}/{post.slug}"


def post_url(post):
    return urljoin(f"{settings.FRONTEND_BASE.rstrip('/')}/", post_path(post).lstrip("/"))


def analyze_post(post):
    keyword = (post.focus_keyword or "").strip().lower()
    title = (post.meta_title or post.title or "").strip().lower()
    description = (post.meta_description or post.excerpt or "").strip().lower()
    slug = (post.slug or "").replace("-", " ").replace("_", " ").lower()
    content = post.content or ""
    text = plain_text(content).lower()
    words = text.split()
    keyword_count = text.count(keyword) if keyword else 0
    density = (keyword_count / max(len(words), 1)) * 100
    h1_values = [plain_text(value).lower() for value in re.findall(r"<h1\b[^>]*>(.*?)</h1>", content, re.I | re.S)]
    images = re.findall(r"<img\b([^>]*)>", content, re.I | re.S)
    images_have_alt = all(re.search(r'\balt\s*=\s*["\'][^"\']+["\']', attrs, re.I) for attrs in images)
    thumbnail_has_alt = not post.thumbnail or bool((post.thumbnail_alt or "").strip())
    internal_links = len(re.findall(r'href\s*=\s*["\']/(?!/)', content, re.I))

    results = {
        "keyword_title": bool(keyword and title.startswith(keyword)),
        "keyword_description": bool(keyword and keyword in description),
        "keyword_slug": bool(keyword and keyword.replace("-", " ") in slug),
        "keyword_h1": bool(keyword and len(h1_values) == 1 and keyword in h1_values[0]),
        "image_alt": images_have_alt and thumbnail_has_alt,
        "content_length": len(words) >= 300,
        "internal_links": internal_links >= 2,
        "keyword_density": bool(keyword and 0.5 <= density <= 2.5),
        "schema": bool(post.schema_type),
    }
    checks = [
        {"code": code, "label": label, "points": points, "passed": results[code]}
        for code, label, points in CHECKS
    ]
    return {
        "score": sum(item["points"] for item in checks if item["passed"]),
        "checks": checks,
        "metrics": {
            "word_count": len(words),
            "internal_links": internal_links,
            "keyword_density": round(density, 2),
        },
    }


def build_article_schema(post):
    if isinstance(post.custom_schema, dict) and post.custom_schema:
        return post.custom_schema
    image = post.og_image or post.thumbnail
    author_name = post.author.get_full_name() or post.author.username
    schema = {
        "@context": "https://schema.org",
        "@type": post.schema_type or "Article",
        "headline": post.title,
        "description": post.meta_description or post.excerpt or plain_text(post.content)[:160],
        "mainEntityOfPage": post.canonical_url or post_url(post),
        "datePublished": post.published_at.isoformat() if post.published_at else None,
        "dateModified": post.updated_at.isoformat() if post.updated_at else None,
        "author": {"@type": "Person", "name": author_name},
        "publisher": {"@type": "Organization", "name": "کاوکس"},
    }
    if image:
        schema["image"] = urljoin(f"{settings.FRONTEND_BASE.rstrip('/')}/", image.url.lstrip("/"))
    return {key: value for key, value in schema.items() if value not in (None, "")}


def snapshot_post(post):
    return {
        "title": post.title,
        "slug": post.slug,
        "content": post.content,
        "content_blocks": post.content_blocks,
        "excerpt": post.excerpt,
        "thumbnail_alt": post.thumbnail_alt,
        "categories": list(post.categories.values_list("id", flat=True)),
        "meta_title": post.meta_title,
        "meta_description": post.meta_description,
        "canonical_url": post.canonical_url,
        "focus_keyword": post.focus_keyword,
        "secondary_keywords": post.secondary_keywords,
        "og_title": post.og_title,
        "og_description": post.og_description,
        "twitter_card": post.twitter_card,
        "robots_index": post.robots_index,
        "robots_follow": post.robots_follow,
        "robots_max_snippet": post.robots_max_snippet,
        "schema_type": post.schema_type,
        "custom_schema": post.custom_schema,
        "status": post.status,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
    }
