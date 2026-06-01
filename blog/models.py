from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field
import math


class Category(models.Model):
    title = models.CharField(max_length=100, verbose_name="عنوان دسته")
    slug = models.SlugField(unique=True, allow_unicode=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title


class Post(models.Model):
    STATUS_CHOICES = (
        ('draft', 'پیش‌نویس'),
        ('in_review', 'در حال بررسی'),
        ('approved', 'تایید شده'),
        ('scheduled', 'زمان‌بندی شده'),
        ('published', 'منتشر شده'),
        ('updated', 'به‌روزرسانی شده'),
        ('archived', 'بایگانی شده'),
    )
    SCHEMA_CHOICES = (
        ('Article', 'Article'),
        ('BlogPosting', 'BlogPosting'),
        ('FAQPage', 'FAQPage'),
        ('WebPage', 'WebPage'),
    )
    TWITTER_CARD_CHOICES = (
        ('summary', 'summary'),
        ('summary_large_image', 'summary_large_image'),
    )

    title = models.CharField(max_length=255, verbose_name="عنوان خبر")
    slug = models.SlugField(unique=True, max_length=255, allow_unicode=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    content = CKEditor5Field(verbose_name="محتوا", config_name="default")
    content_blocks = models.JSONField(default=dict, blank=True)
    excerpt = models.TextField(blank=True, default="")
    thumbnail = models.ImageField(upload_to='blog/thumbs/', verbose_name="تصویر شاخص", blank=True)
    thumbnail_alt = models.CharField(max_length=255, blank=True, default="")
    categories = models.ManyToManyField(Category, related_name='posts', verbose_name="دسته‌بندی‌ها")

    # SEO Fields (WordPress-like)
    meta_title = models.CharField(max_length=70, blank=True, null=True, help_text="حداکثر ۷۰ کاراکتر")
    meta_description = models.TextField(max_length=160, blank=True, null=True, help_text="حداکثر ۱۶۰ کاراکتر")
    canonical_url = models.URLField(blank=True, null=True)
    focus_keyword = models.CharField(max_length=100, blank=True, default="")
    secondary_keywords = models.JSONField(default=list, blank=True)
    og_title = models.CharField(max_length=95, blank=True, default="")
    og_description = models.CharField(max_length=200, blank=True, default="")
    og_image = models.ImageField(upload_to='blog/og/', blank=True, null=True)
    twitter_card = models.CharField(max_length=32, choices=TWITTER_CARD_CHOICES, default='summary_large_image')
    robots_index = models.BooleanField(default=True)
    robots_follow = models.BooleanField(default=True)
    robots_max_snippet = models.IntegerField(default=-1)
    schema_type = models.CharField(max_length=32, choices=SCHEMA_CHOICES, default='Article')
    custom_schema = models.JSONField(blank=True, null=True)
    seo_score = models.PositiveSmallIntegerField(default=0)

    # Status & Scheduling
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='draft', db_index=True)
    published_at = models.DateTimeField(default=timezone.now)
    scheduled_at = models.DateTimeField(blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Metrics
    reading_time = models.PositiveIntegerField(editable=False, default=0)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['published_at']),
        ]

    def save(self, *args, **kwargs):
        # محاسبه زمان مطالعه
        if self.content:
            from django.utils.html import strip_tags
            plain_text = strip_tags(self.content)
            word_count = len(plain_text.split())
            self.reading_time = math.ceil(word_count / 200) or 1
            
        # تولید خودکار اسلاگ (slug)
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True) or "article"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class MediaAsset(models.Model):
    file = models.ImageField(upload_to='blog/media/')
    alt_text = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True, default="")
    caption = models.TextField(blank=True, default="")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blog_media_assets')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.alt_text


class PostRevision(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='revisions')
    snapshot = models.JSONField(default=dict)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blog_post_revisions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class SlugRedirect(models.Model):
    old_slug = models.SlugField(unique=True, max_length=255, allow_unicode=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='slug_redirects')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.old_slug} -> {self.post.slug}"


class SiteSEOSettings(models.Model):
    robots_txt = models.TextField(
        default="User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /api/\n"
    )
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def load(cls):
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance
