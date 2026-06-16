from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    SeoAssistantSettingsView,
    SeoChatView,
    SeoConversationViewSet,
    SeoKnowledgeViewSet,
)

router = DefaultRouter()
router.register(r"admin/knowledge", SeoKnowledgeViewSet, basename="seo-knowledge")
router.register(r"admin/conversations", SeoConversationViewSet, basename="seo-conversations")

app_name = "seo_assistant"

urlpatterns = [
    path("admin/chat/", SeoChatView.as_view(), name="admin-chat"),
    path("admin/settings/", SeoAssistantSettingsView.as_view(), name="admin-settings"),
    path("", include(router.urls)),
]
