from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminPostViewSet,
    AdminCategoryViewSet,
    AdminRobotsView,
    CategoryListView,
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

app_name = 'blog' # تعریف Namespace برای سئو و دسترسی‌های داخلی

urlpatterns = [
    path('seo/analyze/<str:slug>/', SEOAnalyzeView.as_view(), name='seo-analyze'),
    path('schema/<str:slug>/', SchemaView.as_view(), name='schema'),
    path('sitemap/', SitemapView.as_view(), name='sitemap'),
    path('robots.txt', RobotsView.as_view(), name='robots'),
    path('admin/robots/', AdminRobotsView.as_view(), name='admin-robots'),
    path('', include(router.urls)),
]
