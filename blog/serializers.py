
from django.contrib.auth.models import User
from django.utils.text import slugify
import bleach
from bleach.css_sanitizer import CSSSanitizer
from rest_framework import serializers

from .editorjs import normalize_editor_data, render_editor_data
from .models import Category, FeaturedLoad, FeaturedLoadAlert, HomepageSlide, MediaAsset, Post, PostRevision, SiteSEOSettings, SlugRedirect
from .seo import analyze_post, build_article_schema, snapshot_post


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


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'title', 'slug', 'description']
        extra_kwargs = {
            'slug': {'required': False, 'allow_blank': True},
        }

    def _unique_slug(self, title, requested_slug=''):
        base = slugify(requested_slug or title, allow_unicode=True) or 'category'
        slug = base
        index = 2
        queryset = Category.objects.all()
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        while queryset.filter(slug=slug).exists():
            slug = f'{base}-{index}'
            index += 1
        return slug

    def create(self, validated_data):
        validated_data['slug'] = self._unique_slug(
            validated_data.get('title', ''),
            validated_data.get('slug', ''),
        )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'title' in validated_data or 'slug' in validated_data:
            validated_data['slug'] = self._unique_slug(
                validated_data.get('title', instance.title),
                validated_data.get('slug', instance.slug),
            )
        return super().update(instance, validated_data)


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']


class PostListSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True)
    author = AuthorSerializer()

    class Meta:
        model = Post

        fields = [
            'id',
            'title',
            'slug',
            'excerpt',
            'thumbnail',
            'thumbnail_alt',
            'categories',
            'author',
            'published_at',
            'reading_time',
            'meta_description',
        ]


class PostDetailSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True)
    author = AuthorSerializer()
    content = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()
    schema = serializers.SerializerMethodField()

    def get_content(self, obj):
        return sanitize_content(obj.content)

    def get_seo(self, obj):
        return {
            "title": obj.meta_title or obj.title,
            "meta_description": obj.meta_description or obj.excerpt,
            "focus_keyword": obj.focus_keyword,
            "canonical_url": obj.canonical_url,
            "og_title": obj.og_title or obj.meta_title or obj.title,
            "og_description": obj.og_description or obj.meta_description or obj.excerpt,
            "og_image": obj.og_image.url if obj.og_image else "",
            "twitter_card": obj.twitter_card,
            "robots": {
                "index": obj.robots_index,
                "follow": obj.robots_follow,
                "max_snippet": obj.robots_max_snippet,
            },
            "score": obj.seo_score,
        }

    def get_schema(self, obj):
        return build_article_schema(obj)

    class Meta:
        model = Post
        fields = [
            'id',
            'title',
            'slug',
            'content',
            'excerpt',
            'thumbnail',
            'thumbnail_alt',
            'categories',
            'author',
            'published_at',
            'updated_at',
            'reading_time',
            'meta_title',
            'meta_description',
            'canonical_url',
            'status',
            'seo',
            'schema',
        ]


class AdminPostSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    categories = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), many=True, required=False)
    seo_analysis = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Post
        fields = [
            'id',
            'title',
            'slug',
            'author',
            'content',
            'content_blocks',
            'excerpt',
            'thumbnail',
            'thumbnail_alt',
            'categories',
            'meta_title',
            'meta_description',
            'canonical_url',
            'focus_keyword',
            'secondary_keywords',
            'og_title',
            'og_description',
            'og_image',
            'twitter_card',
            'robots_index',
            'robots_follow',
            'robots_max_snippet',
            'schema_type',
            'custom_schema',
            'seo_score',
            'seo_analysis',
            'status',
            'published_at',
            'scheduled_at',
            'created_at',
            'updated_at',
            'reading_time',
            'view_count',
        ]
        read_only_fields = ['seo_score', 'created_at', 'updated_at', 'reading_time', 'view_count']
        extra_kwargs = {
            'slug': {'required': False, 'allow_blank': True},
            'content': {'required': False},
            'thumbnail': {'required': False, 'allow_null': True},
            'og_image': {'required': False, 'allow_null': True},
        }

    def get_seo_analysis(self, obj):
        return analyze_post(obj)

    def validate_content(self, value):
        return sanitize_content(value)

    def validate_content_blocks(self, value):
        try:
            return normalize_editor_data(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if 'content_blocks' in attrs:
            attrs['content'] = sanitize_content(render_editor_data(attrs['content_blocks']))
        elif self.instance is None and 'content' not in attrs:
            attrs['content'] = ''
        status = attrs.get('status', getattr(self.instance, 'status', Post.STATUS_CHOICES[0][0]))
        scheduled_at = attrs.get('scheduled_at', getattr(self.instance, 'scheduled_at', None))
        if status == 'scheduled' and not scheduled_at:
            raise serializers.ValidationError({'scheduled_at': 'برای انتشار زمان‌بندی‌شده، تاریخ انتشار الزامی است.'})
        return attrs

    def _unique_slug(self, title, requested_slug=''):
        base = slugify(requested_slug or title, allow_unicode=True) or 'article'
        slug = base
        index = 2
        queryset = Post.objects.all()
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        while queryset.filter(slug=slug).exists():
            slug = f'{base}-{index}'
            index += 1
        return slug

    def _update_score(self, post):
        score = analyze_post(post)['score']
        if post.seo_score != score:
            Post.objects.filter(pk=post.pk).update(seo_score=score)
            post.seo_score = score
        return post

    def create(self, validated_data):
        request = self.context['request']
        validated_data['author'] = request.user
        validated_data['slug'] = self._unique_slug(validated_data.get('title', ''), validated_data.get('slug', ''))
        post = super().create(validated_data)
        return self._update_score(post)

    def update(self, instance, validated_data):
        request = self.context['request']
        PostRevision.objects.create(post=instance, snapshot=snapshot_post(instance), created_by=request.user)
        old_slug = instance.slug
        if 'slug' in validated_data or 'title' in validated_data:
            validated_data['slug'] = self._unique_slug(
                validated_data.get('title', instance.title),
                validated_data.get('slug', instance.slug),
            )
        post = super().update(instance, validated_data)
        if old_slug != post.slug:
            SlugRedirect.objects.update_or_create(old_slug=old_slug, defaults={'post': post})
        return self._update_score(post)


class PostRevisionSerializer(serializers.ModelSerializer):
    created_by = AuthorSerializer(read_only=True)

    class Meta:
        model = PostRevision
        fields = ['id', 'snapshot', 'created_by', 'created_at']


class MediaAssetSerializer(serializers.ModelSerializer):
    uploaded_by = AuthorSerializer(read_only=True)

    class Meta:
        model = MediaAsset
        fields = ['id', 'file', 'alt_text', 'title', 'caption', 'uploaded_by', 'created_at']
        read_only_fields = ['uploaded_by', 'created_at']


class HomepageSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomepageSlide
        fields = ['id', 'title', 'subtitle', 'image', 'link_url', 'link_label',
                  'sort_order', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class FeaturedLoadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturedLoad
        fields = ['id', 'title', 'specification', 'image', 'available_quantity',
                  'min_order_quantity', 'origin', 'delivery_time', 'quality_grade',
                  'loading_cost_note', 'settlement_method', 'price', 'description',
                  'cta_label', 'sort_order', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class FeaturedLoadAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturedLoadAlert
        fields = ['id', 'keyword', 'origin', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_keyword(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("این فیلد الزامی است.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        return FeaturedLoadAlert.objects.create(user=user, **validated_data)


class SiteSEOSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSEOSettings
        fields = ['robots_txt', 'updated_at']
        read_only_fields = ['updated_at']


