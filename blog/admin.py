
from django.contrib import admin
from .models import Category, HomepageSlide, MediaAsset, Post, PostRevision, SiteSEOSettings, SlugRedirect

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'seo_score', 'published_at')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('status', 'categories')


@admin.register(HomepageSlide)
class HomepageSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'sort_order', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    list_editable = ('sort_order', 'is_active')


admin.site.register(MediaAsset)
admin.site.register(PostRevision)
admin.site.register(SlugRedirect)
admin.site.register(SiteSEOSettings)
