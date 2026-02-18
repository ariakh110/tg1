from django.urls import path
from .views import (
    ProfileDetailView,
    RegisterAPIView,
    ProfileAPIView,
    VerifyEmailView,
    ResendVerificationEmailView,
)
from products.views import SellerDetailView
# Define auth-related routes without the top-level `api/` prefix. The project
# `tg1/urls.py` includes this file under `path('api/', include('accounts.urls'))`
# so the final routes become /api/auth/register/ and /api/auth/profile/.
urlpatterns = [
    path("me/", ProfileDetailView.as_view(), name="profile-me"),
    path("auth/register/", RegisterAPIView.as_view(), name="api_register"),
    path("auth/profile/", ProfileAPIView.as_view(), name="api_profile"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("auth/resend-verification/", ResendVerificationEmailView.as_view(), name="resend-verification"),
    path('sellers/<int:pk>/', SellerDetailView.as_view(), name='seller-detail'),
]
