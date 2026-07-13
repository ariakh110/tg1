import logging
import uuid

from django.core.management import call_command
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrActiveAdminRole

from .ai import SeoAssistantCancelled, SeoAssistantError, ensure_embeddings, run_chat
from .models import SeoAssistantSettings, SeoChatRequest, SeoConversation, SeoKnowledge
from .serializers import (
    SeoAssistantSettingsSerializer,
    SeoConversationDetailSerializer,
    SeoConversationSerializer,
    SeoKnowledgeSerializer,
)

logger = logging.getLogger(__name__)

MAX_MESSAGE_LEN = 4000


def _chat_request_payload(chat_request, session_key=""):
    return {
        "request_id": str(chat_request.request_id),
        "session_key": chat_request.conversation.session_key if chat_request.conversation_id else session_key,
        "status": chat_request.status,
        "cancelled": chat_request.status == SeoChatRequest.STATUS_CANCELLED,
        "reply": chat_request.reply or chat_request.error,
        "error": chat_request.status == SeoChatRequest.STATUS_FAILED,
    }


def _finish_chat_request(chat_request, run_status, *, reply="", error=""):
    chat_request.status = run_status
    chat_request.reply = reply
    chat_request.error = error
    chat_request.finished_at = timezone.now()
    chat_request.save(update_fields=["status", "reply", "error", "finished_at", "updated_at"])


def _finish_active_chat_request(chat_request, run_status, *, reply="", error=""):
    finished_at = timezone.now()
    updated = SeoChatRequest.objects.filter(
        pk=chat_request.pk,
        status=SeoChatRequest.STATUS_RUNNING,
        cancel_requested=False,
    ).update(
        status=run_status,
        reply=reply,
        error=error,
        finished_at=finished_at,
        updated_at=finished_at,
    )
    chat_request.refresh_from_db()
    return bool(updated)


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

        raw_request_id = str(data.get("request_id", "")).strip()
        try:
            request_id = uuid.UUID(raw_request_id) if raw_request_id else uuid.uuid4()
        except ValueError:
            return Response({"detail": "شناسه درخواست معتبر نیست."}, status=status.HTTP_400_BAD_REQUEST)

        session_key = str(data.get("session_key", "")).strip()[:64] or uuid.uuid4().hex
        existing_request = SeoChatRequest.objects.select_related("conversation").filter(pk=request_id).first()
        if existing_request:
            if existing_request.user_id != request.user.id:
                return Response({"detail": "درخواست پیدا نشد."}, status=status.HTTP_404_NOT_FOUND)
            if existing_request.status != SeoChatRequest.STATUS_RUNNING or existing_request.cancel_requested:
                return Response(_chat_request_payload(existing_request, session_key))
            return Response(
                {"detail": "این درخواست هم‌اکنون در حال پردازش است.", "request_id": str(request_id)},
                status=status.HTTP_409_CONFLICT,
            )

        conversation, _created = SeoConversation.objects.get_or_create(session_key=session_key)
        if conversation.user_id is None:
            conversation.user = request.user
            conversation.save(update_fields=["user"])

        chat_request, created = SeoChatRequest.objects.get_or_create(
            request_id=request_id,
            defaults={"conversation": conversation, "user": request.user},
        )
        if not created:
            if chat_request.user_id != request.user.id:
                return Response({"detail": "درخواست پیدا نشد."}, status=status.HTTP_404_NOT_FOUND)
            return Response(_chat_request_payload(chat_request, session_key))

        def is_cancelled():
            state = SeoChatRequest.objects.filter(pk=request_id).values_list(
                "cancel_requested", "status"
            ).first()
            return not state or state[0] or state[1] == SeoChatRequest.STATUS_CANCELLED

        try:
            reply = run_chat(
                conversation,
                message,
                cfg,
                chat_request=chat_request,
                cancel_check=is_cancelled,
            )
        except SeoAssistantCancelled:
            chat_request.messages.all().delete()
            _finish_chat_request(chat_request, SeoChatRequest.STATUS_CANCELLED)
            return Response(_chat_request_payload(chat_request, session_key))
        except SeoAssistantError as exc:
            if not _finish_active_chat_request(chat_request, SeoChatRequest.STATUS_FAILED, error=str(exc)):
                chat_request.messages.all().delete()
                return Response(_chat_request_payload(chat_request, session_key))
            return Response(
                {
                    "request_id": str(request_id),
                    "session_key": session_key,
                    "reply": str(exc),
                    "status": SeoChatRequest.STATUS_FAILED,
                    "error": True,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:  # noqa: BLE001 — ادمین‌محور؛ خطای واقعی را به‌جای ۵۰۰ مبهم («{}») نشان بده
            logger.exception("run_chat failed for session %s", session_key)
            detail = f"خطای داخلی هنگام پردازش: {type(exc).__name__}: {exc}"
            if not _finish_active_chat_request(chat_request, SeoChatRequest.STATUS_FAILED, error=detail):
                chat_request.messages.all().delete()
                return Response(_chat_request_payload(chat_request, session_key))
            return Response(
                {
                    "request_id": str(request_id),
                    "session_key": session_key,
                    "reply": detail,
                    "status": SeoChatRequest.STATUS_FAILED,
                    "error": True,
                },
                status=status.HTTP_200_OK,
            )
        if not _finish_active_chat_request(chat_request, SeoChatRequest.STATUS_COMPLETED, reply=reply):
            chat_request.messages.all().delete()
        return Response(_chat_request_payload(chat_request, session_key))


class SeoChatCancelView(APIView):
    """لغو idempotent یک نوبت گفتگو و حذف پیام‌های نیمه‌کارهٔ همان نوبت."""

    permission_classes = [IsAdminOrActiveAdminRole]

    def post(self, request, request_id):
        chat_request, created = SeoChatRequest.objects.get_or_create(
            request_id=request_id,
            defaults={
                "user": request.user,
                "status": SeoChatRequest.STATUS_CANCELLED,
                "cancel_requested": True,
                "finished_at": timezone.now(),
            },
        )
        if not created and chat_request.user_id != request.user.id:
            return Response({"detail": "درخواست پیدا نشد."}, status=status.HTTP_404_NOT_FOUND)

        chat_request.cancel_requested = True
        chat_request.status = SeoChatRequest.STATUS_CANCELLED
        chat_request.reply = ""
        chat_request.error = ""
        chat_request.finished_at = timezone.now()
        chat_request.save(
            update_fields=["cancel_requested", "status", "reply", "error", "finished_at", "updated_at"]
        )
        chat_request.messages.all().delete()
        return Response(_chat_request_payload(chat_request))


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
