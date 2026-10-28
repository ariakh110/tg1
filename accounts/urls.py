from django.urls import path
from .mobile_login import MobileCodeView, MobileVerifyView, BindCodeView, BindVerifyView, MobileBindingView
from .views import (
    ProfileDetailView,
    RegisterAPIView,
    GoogleAuthAPIView,
    ProfileAPIView,
    VerifyEmailView,
    ResendVerificationEmailView,
)
from products.views import SellerDetailView
# Define auth-related routes without the top-level `api/` prefix. The project
# `tg1/urls.py` includes this file under `path('api/', include('accounts.urls'))`
# so the final routes become /api/auth/register/ and /api/auth/profile/.
urlpatterns = [
    path("auth/mobile/code/", MobileCodeView.as_view()),
    path("auth/mobile/verify/", MobileVerifyView.as_view()),
    path("auth/mobile/bind/code/", BindCodeView.as_view()),
    path("auth/mobile/bind/verify/", BindVerifyView.as_view()),
    path("auth/mobile/binding/", MobileBindingView.as_view()),
    path("me/", ProfileDetailView.as_view(), name="profile-me"),
    path("auth/register/", RegisterAPIView.as_view(), name="api_register"),
    path("auth/google/", GoogleAuthAPIView.as_view(), name="api_google_auth"),
    path("auth/profile/", ProfileAPIView.as_view(), name="api_profile"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("auth/resend-verification/", ResendVerificationEmailView.as_view(), name="resend-verification"),
    path('sellers/<int:pk>/', SellerDetailView.as_view(), name='seller-detail'),
]
