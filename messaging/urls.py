from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BaleUserBindingViewSet,
    BaleSetWebhookView,
    BaleWebhookView,
    KavenegarIncomingWebhook,
    KavenegarStatusWebhook,
    MessagingBulkSendView,
    MessagingAudiencePreviewView,
    MessagingContactGroupViewSet,
    MessagingNotifyStepView,
    MessagingSendView,
    MessagingSettingsView,
    MessagingTestAlertView,
    OutboundMessageViewSet,
)

router = DefaultRouter()
router.register(r"messages", OutboundMessageViewSet, basename="outbound-message")
router.register(r"bale-bindings", BaleUserBindingViewSet, basename="bale-user-binding")
router.register(r"groups", MessagingContactGroupViewSet, basename="messaging-contact-group")

app_name = "messaging"

urlpatterns = [
    path("settings/", MessagingSettingsView.as_view(), name="settings"),
    path("send/", MessagingSendView.as_view(), name="send"),
    path("send-bulk/", MessagingBulkSendView.as_view(), name="send-bulk"),
    path("audience-preview/", MessagingAudiencePreviewView.as_view(), name="audience-preview"),
    path("notify-step/", MessagingNotifyStepView.as_view(), name="notify-step"),
    path("test-alert/", MessagingTestAlertView.as_view(), name="test-alert"),
    # ربات دوطرفهٔ بله
    path("bale/set-webhook/", BaleSetWebhookView.as_view(), name="bale-set-webhook"),
    path("bale/webhook/<str:secret>/", BaleWebhookView.as_view(), name="bale-webhook"),
    # وب‌هوک‌های ورودیِ کاوه‌نگار (عمومی؛ کلیدِ مخفی در مسیر).
    path("kavenegar/status/<str:secret>/", KavenegarStatusWebhook.as_view(), name="kavenegar-status"),
    path("kavenegar/incoming/<str:secret>/", KavenegarIncomingWebhook.as_view(), name="kavenegar-incoming"),
    path("", include(router.urls)),
]
