import math
import shutil
import tempfile
from urllib.parse import quote

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Category, Post

TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class BlogAPITests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()
        self.author = User.objects.create_user(username="editor", password="pass")
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
