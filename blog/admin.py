
from django.contrib import admin
from .models import Category, MediaAsset, Post, PostRevision, SiteSEOSettings, SlugRedirect

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'seo_score', 'published_at')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('status', 'categories')


admin.site.register(MediaAsset)
admin.site.register(PostRevision)
admin.site.register(SlugRedirect)
admin.site.register(SiteSEOSettings)
