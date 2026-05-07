from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PostViewSet, CategoryListView

# استفاده از SimpleRouter برای تمیزی URLها در API
router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='posts')
router.register(r'categories', CategoryListView, basename='categories')

app_name = 'blog' # تعریف Namespace برای سئو و دسترسی‌های داخلی

urlpatterns = [
    path('', include(router.urls)),
]