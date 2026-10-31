from .channel_posts import ChannelPostViewSet
from .market_views import MarketTelegramConnectionView, MarketChannelResolveView
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .market_views import MarketChannelDraftsView, MarketChannelPublishView
from .google_relay import RelayClaimView, RelayAckView

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
router.register(r"channel-posts", ChannelPostViewSet, basename="channel-post")
router.register(r"messages", OutboundMessageViewSet, basename="outbound-message")
router.register(r"bale-bindings", BaleUserBindingViewSet, basename="bale-user-binding")
router.register(r"groups", MessagingContactGroupViewSet, basename="messaging-contact-group")

app_name = "messaging"

urlpatterns = [
    path('market-relay/claim/', RelayClaimView.as_view(), name='market-relay-claim'),
    path('market-relay/ack/', RelayAckView.as_view(), name='market-relay-ack'),
    path("market-drafts/<int:pk>/resolve/", MarketChannelResolveView.as_view(), name="market-resolve"),
    path("market-telegram/test/", MarketTelegramConnectionView.as_view(), name="market-telegram-test"),
    path("market-drafts/", MarketChannelDraftsView.as_view(), name="market-drafts"),
    path("market-drafts/<int:pk>/publish/", MarketChannelPublishView.as_view(), name="market-publish"),
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
