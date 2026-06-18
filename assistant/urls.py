from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminAssistantSettingsView,
    AdminConversationViewSet,
    AdminInquiryViewSet,
    AdminKnowledgeViewSet,
    AssistantChatView,
    AssistantConfigView,
)

router = DefaultRouter()
router.register(r"admin/knowledge", AdminKnowledgeViewSet, basename="assistant-knowledge")
router.register(r"admin/conversations", AdminConversationViewSet, basename="assistant-conversations")
router.register(r"admin/inquiries", AdminInquiryViewSet, basename="assistant-inquiries")

app_name = "assistant"

urlpatterns = [
    path("chat/", AssistantChatView.as_view(), name="chat"),
    path("config/", AssistantConfigView.as_view(), name="config"),
    path("admin/settings/", AdminAssistantSettingsView.as_view(), name="admin-settings"),
    path("", include(router.urls)),
]
