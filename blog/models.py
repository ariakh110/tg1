from django.db import models
from django.contrib.auth.models import User
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
        ('published', 'منتشر شده'),
    )

    title = models.CharField(max_length=255, verbose_name="عنوان خبر")
    slug = models.SlugField(unique=True, max_length=255, allow_unicode=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    content = CKEditor5Field(verbose_name="محتوا", config_name="default")
    thumbnail = models.ImageField(upload_to='blog/thumbs/', verbose_name="تصویر شاخص")
    categories = models.ManyToManyField(Category, related_name='posts', verbose_name="دسته‌بندی‌ها")

    # SEO Fields (WordPress-like)
    meta_title = models.CharField(max_length=70, blank=True, null=True, help_text="حداکثر ۷۰ کاراکتر")
    meta_description = models.TextField(max_length=160, blank=True, null=True, help_text="حداکثر ۱۶۰ کاراکتر")
    canonical_url = models.URLField(blank=True, null=True)

    # Status & Scheduling
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Metrics
    reading_time = models.PositiveIntegerField(editable=False, default=0)

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
            self.slug = slugify(self.title, allow_unicode=True)
            
        # حتما ستاره‌ها را در خط پایین هم قرار بده
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
