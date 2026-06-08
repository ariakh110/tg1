
from django.contrib import admin
from .models import Category, FeaturedLoad, FeaturedLoadAlert, FeaturedLoadAlertMatch, HomepageSlide, MediaAsset, Post, PostRevision, SiteSEOSettings, SlugRedirect

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


@admin.register(FeaturedLoad)
class FeaturedLoadAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'sort_order', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    list_editable = ('sort_order', 'is_active')
    search_fields = ('title', 'specification', 'origin')


@admin.register(FeaturedLoadAlert)
class FeaturedLoadAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'keyword', 'origin', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('keyword', 'origin', 'user__username', 'user__email')


@admin.register(FeaturedLoadAlertMatch)
class FeaturedLoadAlertMatchAdmin(admin.ModelAdmin):
    list_display = ('alert', 'load', 'channel', 'status', 'created_at')
    list_filter = ('channel', 'status')
    search_fields = ('alert__keyword', 'alert__user__username', 'load__title')


admin.site.register(MediaAsset)
admin.site.register(PostRevision)
admin.site.register(SlugRedirect)
admin.site.register(SiteSEOSettings)
