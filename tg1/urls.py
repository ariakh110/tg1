
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include 
from rest_framework import routers
from core import views as core_views
router = routers.DefaultRouter()

urlpatterns = router.urls


urlpatterns += [
    path('admin/', admin.site.urls),
    path('api/', include('products.urls')),
    path('contact',core_views.ContactAPIView.as_view())
]



# اضافه کردن این قسمت در آخر فایل
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)