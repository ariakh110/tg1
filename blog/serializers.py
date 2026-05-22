
from django.contrib.auth.models import User
import bleach
from bleach.css_sanitizer import CSSSanitizer
from rest_framework import serializers

from .models import Category, Post


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

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'title', 'slug']

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']

class PostListSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True)
    author = AuthorSerializer()

    class Meta:
        model = Post

        fields = ['id', 'title', 'slug', 'thumbnail', 'categories', 'author', 'published_at', 'reading_time','meta_description']

class PostDetailSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True)
    author = AuthorSerializer()
    content = serializers.SerializerMethodField()

    def get_content(self, obj):
        return bleach.clean(
            obj.content or "",
            tags=ALLOWED_CONTENT_TAGS,
            attributes=ALLOWED_CONTENT_ATTRIBUTES,
            css_sanitizer=CONTENT_CSS_SANITIZER,
            protocols=["http", "https", "mailto"],
            strip=True,
        )

    class Meta:
        model = Post
        fields = '__all__'


