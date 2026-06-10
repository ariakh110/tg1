from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminCategoryViewSet,
    AdminFAQViewSet,
    AdminFeaturedLoadViewSet,
    AdminHomepageSlideViewSet,
    AdminPostViewSet,
    AdminRobotsView,
    CategoryListView,
    FAQViewSet,
    FeaturedLoadAlertViewSet,
    FeaturedLoadViewSet,
    HomepageSlideViewSet,
    MediaAssetViewSet,
    PostViewSet,
    RobotsView,
    SchemaView,
    SEOAnalyzeView,
    SitemapView,
)

# استفاده از SimpleRouter برای تمیزی URLها در API
router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='posts')
router.register(r'categories', CategoryListView, basename='categories')
router.register(r'admin/posts', AdminPostViewSet, basename='admin-posts')
router.register(r'admin/categories', AdminCategoryViewSet, basename='admin-categories')
router.register(r'admin/media', MediaAssetViewSet, basename='admin-media')
router.register(r'homepage-slides', HomepageSlideViewSet, basename='homepage-slides')
router.register(r'admin/homepage-slides', AdminHomepageSlideViewSet, basename='admin-homepage-slides')
router.register(r'featured-loads', FeaturedLoadViewSet, basename='featured-loads')
router.register(r'admin/featured-loads', AdminFeaturedLoadViewSet, basename='admin-featured-loads')
router.register(r'featured-load-alerts', FeaturedLoadAlertViewSet, basename='featured-load-alerts')
router.register(r'faqs', FAQViewSet, basename='faqs')
router.register(r'admin/faqs', AdminFAQViewSet, basename='admin-faqs')

app_name = 'blog' # تعریف Namespace برای سئو و دسترسی‌های داخلی

urlpatterns = [
    path('seo/analyze/<str:slug>/', SEOAnalyzeView.as_view(), name='seo-analyze'),
    path('schema/<str:slug>/', SchemaView.as_view(), name='schema'),
    path('sitemap/', SitemapView.as_view(), name='sitemap'),
    path('robots.txt', RobotsView.as_view(), name='robots'),
    path('admin/robots/', AdminRobotsView.as_view(), name='admin-robots'),
    path('', include(router.urls)),
]
