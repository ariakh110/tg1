import math
import shutil
import tempfile
from io import BytesIO
from urllib.parse import quote
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from .models import Category, MediaAsset, Post, SiteSEOSettings

TEST_MEDIA_ROOT = tempfile.mkdtemp()


def make_test_blog_image(filename="article.png", image_format="PNG", padding=0):
    content = BytesIO()
    Image.new("RGB", (32, 18), color=(31, 78, 121)).save(content, format=image_format)
    payload = content.getvalue() + (b"\0" * padding)
    return SimpleUploadedFile(filename, payload, content_type=f"image/{image_format.lower()}")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class BlogAPITests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()
        self.author = User.objects.create_user(username="editor", password="pass")
        self.admin = User.objects.create_user(username="content_admin", password="pass", is_staff=True)
        self.market = Category.objects.create(title="بازار فولاد", slug="steel-market")
        self.company = Category.objects.create(title="اخبار شرکت", slug="company-news")

    def make_post(self, **overrides):
        categories = overrides.pop("categories", [self.market])
        title = overrides.pop("title", "تحلیل بازار فولاد")
        slug = overrides.pop("slug", "steel-market-analysis")
        content = overrides.pop("content", "<p>متن تستی مقاله</p>")
        post = Post.objects.create(
            title=title,
            slug=slug,
            author=self.author,
            content=content,
            thumbnail=SimpleUploadedFile(
                f"{slug}.jpg",
                b"test-image-content",
                content_type="image/jpeg",
            ),
            status=overrides.pop("status", "published"),
            published_at=overrides.pop("published_at", timezone.now()),
            meta_description=overrides.pop("meta_description", "خلاصه مقاله تستی"),
            **overrides,
        )
        post.categories.set(categories)
        return post

    def test_posts_list_only_returns_published_posts_that_are_not_future_dated(self):
        visible = self.make_post(slug="visible")
        self.make_post(slug="draft", status="draft")
        self.make_post(
            slug="future",
            published_at=timezone.now() + timezone.timedelta(days=1),
        )

        response = self.client.get("/api/blog/posts/")

        self.assertEqual(response.status_code, 200)
        slugs = [item["slug"] for item in response.data["results"]]
        self.assertEqual(slugs, [visible.slug])

    def test_posts_list_filters_by_category_slug(self):
        market_post = self.make_post(slug="market", categories=[self.market])
        self.make_post(slug="company", categories=[self.company])

        response = self.client.get("/api/blog/posts/?category=steel-market")

        self.assertEqual(response.status_code, 200)
        slugs = [item["slug"] for item in response.data["results"]]
        self.assertEqual(slugs, [market_post.slug])

    def test_posts_list_supports_page_size_pagination(self):
        for index in range(3):
            self.make_post(
                slug=f"post-{index}",
                published_at=timezone.now() - timezone.timedelta(minutes=index),
            )

        response = self.client.get("/api/blog/posts/?page_size=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIsNotNone(response.data["next"])

    def test_detail_supports_unicode_slug(self):
        post = self.make_post(
            title="خبر فارسی",
            slug="خبر-فارسی",
            categories=[self.company],
        )

        response = self.client.get(f"/api/blog/posts/{quote(post.slug)}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], post.slug)
        self.assertEqual(response.data["categories"][0]["slug"], self.company.slug)

    def test_detail_does_not_return_draft_or_future_posts(self):
        draft = self.make_post(slug="hidden-draft", status="draft")
        future = self.make_post(
            slug="hidden-future",
            published_at=timezone.now() + timezone.timedelta(days=1),
        )

        draft_response = self.client.get(f"/api/blog/posts/{draft.slug}/")
        future_response = self.client.get(f"/api/blog/posts/{future.slug}/")

        self.assertEqual(draft_response.status_code, 404)
        self.assertEqual(future_response.status_code, 404)

    def test_reading_time_is_calculated_from_plain_content(self):
        words = " ".join(["کلمه"] * 401)
        post = self.make_post(content=f"<p>{words}</p>")

        self.assertEqual(post.reading_time, math.ceil(401 / 200))

    def test_categories_endpoint_is_not_paginated(self):
        response = self.client.get("/api/blog/categories/")

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual({item["slug"] for item in response.data}, {"steel-market", "company-news"})

    def test_detail_content_is_sanitized(self):
        post = self.make_post(
            slug="unsafe-html",
            content=(
                '<p>متن امن</p><script>alert("x")</script>'
                '<a href="javascript:alert(1)">لینک بد</a><strong>تاکید</strong>'
            ),
        )

        response = self.client.get(f"/api/blog/posts/{post.slug}/")

        self.assertEqual(response.status_code, 200)
        content = response.data["content"]
        self.assertNotIn("<script", content)
        self.assertNotIn("javascript:", content)
        self.assertIn("<strong>تاکید</strong>", content)

    def test_scheduled_post_becomes_public_after_effective_time(self):
        visible = self.make_post(
            slug="scheduled-visible",
            status="scheduled",
            scheduled_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        self.make_post(
            slug="scheduled-future",
            status="scheduled",
            scheduled_at=timezone.now() + timezone.timedelta(minutes=10),
        )

        response = self.client.get("/api/blog/posts/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["slug"] for item in response.data["results"]], [visible.slug])

    def test_admin_can_create_draft_with_sanitized_html_and_seo_score(self):
        self.client.force_authenticate(self.admin)
        content = (
            "<h1>بازار فولاد امروز</h1>"
            "<p>بازار فولاد امروز برای خریداران اهمیت دارد.</p>"
            '<script>alert("x")</script>'
        )

        response = self.client.post(
            "/api/blog/admin/posts/",
            {
                "title": "بازار فولاد امروز",
                "slug": "بازار-فولاد-امروز",
                "content": content,
                "excerpt": "تحلیل بازار فولاد امروز",
                "categories": [self.market.id],
                "focus_keyword": "بازار فولاد",
                "meta_title": "بازار فولاد امروز",
                "meta_description": "تحلیل بازار فولاد امروز برای فعالان بازار",
                "thumbnail_alt": "بازار فولاد امروز",
                "status": "draft",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        post = Post.objects.get(pk=response.data["id"])
        self.assertNotIn("<script", post.content)
        self.assertGreater(post.seo_score, 0)
        self.assertEqual(self.client.get("/api/blog/posts/").data["count"], 0)

    def test_admin_can_create_category_with_generated_slug(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/blog/admin/categories/",
            {"title": "گزارش ویژه"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["slug"], "گزارش-ویژه")
        self.assertTrue(Category.objects.filter(pk=response.data["id"]).exists())

    def test_admin_editor_blocks_are_rendered_to_sanitized_html(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/blog/admin/posts/",
            {
                "title": "خبر بلوکی",
                "categories": [self.market.id],
                "content_blocks": {
                    "blocks": [
                        {"type": "header", "data": {"level": 1, "text": "عنوان خبر"}},
                        {"type": "paragraph", "data": {"text": 'متن امن<script>alert("x")</script>'}},
                    ]
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        post = Post.objects.get(pk=response.data["id"])
        self.assertIn("<h1>عنوان خبر</h1>", post.content)
        self.assertNotIn("<script", post.content)
        self.assertEqual(post.content_blocks["blocks"][0]["type"], "header")

    def test_admin_editor_preserves_inline_image_position_and_fallback_alt(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/blog/admin/posts/",
            {
                "title": "مطلب تصویری",
                "content_blocks": {
                    "blocks": [
                        {"type": "paragraph", "data": {"text": "متن قبل تصویر"}},
                        {
                            "type": "image",
                            "data": {
                                "file": {"url": "https://example.com/media/blog/media/article.webp", "alt": "تصویر ورق فولادی"},
                                "caption": "",
                            },
                        },
                        {"type": "paragraph", "data": {"text": "متن بعد تصویر"}},
                    ]
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        content = Post.objects.get(pk=response.data["id"]).content
        before_index = content.index("متن قبل تصویر")
        image_index = content.index("<figure>")
        after_index = content.index("متن بعد تصویر")
        self.assertLess(before_index, image_index)
        self.assertLess(image_index, after_index)
        self.assertIn('alt="تصویر ورق فولادی"', content)

    def test_admin_can_upload_replace_and_remove_featured_image(self):
        post = self.make_post(slug="featured-image")
        old_name = post.thumbnail.name
        storage = post.thumbnail.storage
        self.client.force_authenticate(self.admin)

        uploaded = self.client.patch(
            f"/api/blog/admin/posts/{post.id}/",
            {
                "thumbnail": make_test_blog_image(),
                "thumbnail_alt": "تصویر اصلی بازار فولاد",
            },
            format="multipart",
        )

        self.assertEqual(uploaded.status_code, 200, uploaded.data)
        post.refresh_from_db()
        uploaded_name = post.thumbnail.name
        self.assertNotEqual(uploaded_name, old_name)
        self.assertFalse(storage.exists(old_name))
        self.assertTrue(storage.exists(uploaded_name))
        self.assertEqual(post.thumbnail_alt, "تصویر اصلی بازار فولاد")

        rejected = self.client.patch(
            f"/api/blog/admin/posts/{post.id}/",
            {
                "thumbnail": make_test_blog_image("unsafe.gif", "GIF"),
                "thumbnail_alt": "تصویر نامعتبر",
            },
            format="multipart",
        )
        self.assertEqual(rejected.status_code, 400, rejected.data)
        post.refresh_from_db()
        self.assertEqual(post.thumbnail.name, uploaded_name)

        removed = self.client.patch(
            f"/api/blog/admin/posts/{post.id}/",
            {"thumbnail": None},
            format="json",
        )
        self.assertEqual(removed.status_code, 200, removed.data)
        self.assertIsNone(removed.data["thumbnail"])
        self.assertFalse(storage.exists(uploaded_name))

    def test_featured_image_storage_failure_returns_json_and_rolls_back(self):
        post = self.make_post(slug="featured-storage-failure")
        original_name = post.thumbnail.name
        self.client.force_authenticate(self.admin)

        with patch(
            "django.core.files.storage.FileSystemStorage.save",
            side_effect=PermissionError("read-only media directory"),
        ):
            response = self.client.patch(
                f"/api/blog/admin/posts/{post.id}/",
                {
                    "thumbnail": make_test_blog_image(),
                    "thumbnail_alt": "تصویر اصلی بازار فولاد",
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, 503, response.data)
        self.assertIn("ذخیره تصویر", str(response.data["detail"]))
        post.refresh_from_db()
        self.assertEqual(post.thumbnail.name, original_name)
        self.assertEqual(post.revisions.count(), 0)

    def test_featured_image_success_is_not_lost_when_old_file_cleanup_fails(self):
        post = self.make_post(slug="featured-cleanup-failure")
        storage = post.thumbnail.storage
        self.client.force_authenticate(self.admin)

        with patch.object(storage, "delete", side_effect=PermissionError("cannot delete old file")):
            response = self.client.patch(
                f"/api/blog/admin/posts/{post.id}/",
                {
                    "thumbnail": make_test_blog_image("replacement.webp", "WEBP"),
                    "thumbnail_alt": "تصویر جایگزین بازار فولاد",
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, 200, response.data)
        post.refresh_from_db()
        self.assertTrue(post.thumbnail.name.endswith(".webp"))
        self.assertEqual(post.thumbnail_alt, "تصویر جایگزین بازار فولاد")

    def test_admin_media_upload_validates_format_and_size(self):
        self.client.force_authenticate(self.admin)

        uploaded = self.client.post(
            "/api/blog/admin/media/",
            {"file": make_test_blog_image("inline.webp", "WEBP"), "alt_text": "تصویر داخل مطلب"},
            format="multipart",
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.data)
        self.assertEqual(MediaAsset.objects.count(), 1)

        invalid_format = self.client.post(
            "/api/blog/admin/media/",
            {"file": make_test_blog_image("inline.gif", "GIF"), "alt_text": "تصویر نامعتبر"},
            format="multipart",
        )
        self.assertEqual(invalid_format.status_code, 400, invalid_format.data)

        oversized = self.client.post(
            "/api/blog/admin/media/",
            {
                "file": make_test_blog_image("large.png", padding=(5 * 1024 * 1024)),
                "alt_text": "تصویر بزرگ",
            },
            format="multipart",
        )
        self.assertEqual(oversized.status_code, 400, oversized.data)
        self.assertEqual(MediaAsset.objects.count(), 1)

    @override_settings(OPENAI_API_KEY="")
    def test_ai_suggestions_endpoint_reports_missing_api_key_in_persian(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/blog/admin/posts/ai-suggestions/",
            {"title": "خبر بازار", "content": "<p>متن خبر بازار فولاد</p>"},
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("OPENAI_API_KEY", response.data["detail"])

    @patch("blog.views.generate_content_suggestions")
    def test_ai_suggestions_endpoint_returns_reviewable_metadata(self, suggest):
        suggest.return_value = {
            "excerpt": "خلاصه پیشنهادی",
            "focus_keyword": "بازار فولاد",
            "secondary_keywords": ["قیمت آهن", "خرید فولاد"],
        }
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/blog/admin/posts/ai-suggestions/",
            {
                "title": "خبر بازار",
                "content_blocks": {
                    "blocks": [{"type": "paragraph", "data": {"text": "متن خبر بازار فولاد"}}]
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["focus_keyword"], "بازار فولاد")
        suggest.assert_called_once()

    def test_admin_update_creates_revision_and_revision_can_be_restored(self):
        post = self.make_post(slug="revision-source", title="نسخه اول")
        self.client.force_authenticate(self.admin)

        update = self.client.patch(
            f"/api/blog/admin/posts/{post.id}/",
            {"title": "نسخه دوم"},
            format="json",
        )

        self.assertEqual(update.status_code, 200, update.data)
        revision = post.revisions.get()
        self.assertEqual(revision.snapshot["title"], "نسخه اول")

        restore = self.client.post(
            f"/api/blog/admin/posts/{post.id}/revisions/{revision.id}/restore/",
            {},
            format="json",
        )

        self.assertEqual(restore.status_code, 200, restore.data)
        post.refresh_from_db()
        self.assertEqual(post.title, "نسخه اول")

    def test_schema_sitemap_and_robots_endpoints_expose_crawl_metadata(self):
        post = self.make_post(slug="seo-public", title="تحلیل فولاد")
        hidden = self.make_post(slug="seo-noindex", title="مقاله خصوصی")
        hidden.robots_index = False
        hidden.save(update_fields=["robots_index"])
        SiteSEOSettings.load()

        schema = self.client.get(f"/api/blog/schema/{post.slug}/")
        sitemap = self.client.get("/api/blog/sitemap/")
        robots = self.client.get("/api/blog/robots.txt")

        self.assertEqual(schema.status_code, 200)
        self.assertEqual(schema.data["@type"], "Article")
        self.assertEqual(sitemap.status_code, 200)
        urls = [item["url"] for item in sitemap.data["results"]]
        self.assertTrue(any(post.slug in url for url in urls))
        self.assertFalse(any(hidden.slug in url for url in urls))
        self.assertEqual(robots.status_code, 200)
        self.assertIn("Disallow: /admin/", robots.content.decode("utf-8"))
