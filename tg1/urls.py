
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include 
from rest_framework import routers
from core import views as core_views
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.auth_views import ActiveUserTokenObtainPairView

router = routers.DefaultRouter()

urlpatterns = router.urls


urlpatterns += [
    path('admin/', admin.site.urls),
    path('api/', include('products.urls')),
    # expose contact API under /api/contact so frontend requests to `${API_BASE}/contact` work
    path('api/contact', core_views.ContactAPIView.as_view()),
    # include accounts URL patterns directly under /api/ so routes like
    # /api/auth/profile/ and /api/auth/register/ match frontend expectations
    path("api/", include("accounts.urls")),
    path("api/token/", ActiveUserTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

]



# اضافه کردن این قسمت در آخر فایل
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)