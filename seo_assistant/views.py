import uuid

from django.core.management import call_command
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrActiveAdminRole

from .ai import SeoAssistantError, ensure_embeddings, run_chat
from .models import SeoAssistantSettings, SeoConversation, SeoKnowledge
from .serializers import (
    SeoAssistantSettingsSerializer,
    SeoConversationDetailSerializer,
    SeoConversationSerializer,
    SeoKnowledgeSerializer,
)

MAX_MESSAGE_LEN = 4000


class SeoChatView(APIView):
    """گفتگوی ادمین با دستیار سئو (فقط ادمین)."""

    permission_classes = [IsAdminOrActiveAdminRole]

    def post(self, request):
        cfg = SeoAssistantSettings.load()
        if not cfg.is_enabled:
            return Response({"detail": "دستیار سئو فعال نیست."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data if isinstance(request.data, dict) else {}
        message = str(data.get("message", "")).strip()
        if not message:
            return Response({"detail": "پیام خالی است."}, status=status.HTTP_400_BAD_REQUEST)
        message = message[:MAX_MESSAGE_LEN]

        session_key = str(data.get("session_key", "")).strip()[:64] or uuid.uuid4().hex
        conversation, _created = SeoConversation.objects.get_or_create(session_key=session_key)
        if conversation.user_id is None:
            conversation.user = request.user
            conversation.save(update_fields=["user"])

        try:
            reply = run_chat(conversation, message, cfg)
        except SeoAssistantError as exc:
            return Response(
                {"session_key": session_key, "reply": str(exc), "error": True},
                status=status.HTTP_200_OK,
            )
        return Response({"session_key": session_key, "reply": reply})


class SeoAssistantSettingsView(APIView):
    """خواندن/به‌روزرسانیِ تنظیمات دستیار سئو (فقط ادمین)."""

    permission_classes = [IsAdminOrActiveAdminRole]

    def get(self, request):
        return Response(SeoAssistantSettingsSerializer(SeoAssistantSettings.load()).data)

    def patch(self, request):
        cfg = SeoAssistantSettings.load()
        serializer = SeoAssistantSettingsSerializer(cfg, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SeoAssistantSettingsSerializer(cfg).data)


class SeoKnowledgeViewSet(viewsets.ModelViewSet):
    queryset = SeoKnowledge.objects.all()
    serializer_class = SeoKnowledgeSerializer
    permission_classes = [IsAdminOrActiveAdminRole]
    pagination_class = None
    filterset_fields = ["layer", "is_active"]

    def perform_create(self, serializer):
        serializer.save(layer=serializer.validated_data.get("layer") or SeoKnowledge.LAYER_CUSTOM)

    @action(detail=False, methods=["post"], url_path="reembed")
    def reembed(self, request):
        try:
            count = ensure_embeddings()
        except SeoAssistantError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"updated": count, "detail": f"{count} مورد به‌روزرسانی شد."})

    @action(detail=False, methods=["post"], url_path="ingest")
    def ingest(self, request):
        """بارگذاریِ پایگاه دانش بسته‌بندی‌شده و سپس embedding (در صورت وجود کلید)."""
        try:
            call_command("ingest_seo_kb")
        except Exception as exc:  # noqa: BLE001 — خطای فرمان را به پیام کاربر تبدیل کن
            return Response({"detail": f"خطا در بارگذاری دانش: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        total = SeoKnowledge.objects.count()
        embedded = 0
        try:
            embedded = ensure_embeddings()
        except SeoAssistantError:
            embedded = 0
        return Response({"total": total, "embedded": embedded, "detail": f"{total} تکه دانش موجود است."})


class SeoConversationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SeoConversation.objects.all().prefetch_related("messages")
    permission_classes = [IsAdminOrActiveAdminRole]
    filterset_fields = ["status"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SeoConversationDetailSerializer
        return SeoConversationSerializer
