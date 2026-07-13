from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .ai import SeoAssistantCancelled, _timeout, run_chat
from .models import (
    SeoAssistantSettings,
    SeoChatRequest,
    SeoConversation,
    SeoMessage,
)
from .serializers import SeoAssistantSettingsSerializer


class SeoAssistantTimeoutTests(TestCase):
    def test_timeout_defaults_to_ninety_seconds_and_is_bounded(self):
        cfg = SeoAssistantSettings.load()
        self.assertEqual(_timeout(cfg), 90)

        serializer = SeoAssistantSettingsSerializer(
            cfg,
            data={"request_timeout_seconds": 105},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(_timeout(cfg), 105)

        too_short = SeoAssistantSettingsSerializer(
            cfg,
            data={"request_timeout_seconds": 10},
            partial=True,
        )
        self.assertFalse(too_short.is_valid())
        self.assertIn("request_timeout_seconds", too_short.errors)

        too_long = SeoAssistantSettingsSerializer(
            cfg,
            data={"request_timeout_seconds": 120},
            partial=True,
        )
        self.assertFalse(too_long.is_valid())
        self.assertIn("request_timeout_seconds", too_long.errors)


class SeoAssistantCancellationTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="seo-admin",
            email="seo-admin@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(self.user)
        cfg = SeoAssistantSettings.load()
        cfg.is_enabled = True
        cfg.save(update_fields=["is_enabled"])

    @patch("seo_assistant.views.run_chat", return_value="پاسخ تست")
    def test_completed_request_is_idempotent(self, mocked_run_chat):
        request_id = uuid4()
        payload = {
            "request_id": str(request_id),
            "session_key": "seo-session",
            "message": "صفحه را بررسی کن",
        }

        first = self.client.post("/api/seo-assistant/admin/chat/", payload, format="json")
        second = self.client.post("/api/seo-assistant/admin/chat/", payload, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)
        self.assertEqual(first.data["status"], SeoChatRequest.STATUS_COMPLETED)
        self.assertEqual(first.data["reply"], "پاسخ تست")
        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        self.assertEqual(second.data["reply"], "پاسخ تست")
        self.assertEqual(mocked_run_chat.call_count, 1)
        chat_request = SeoChatRequest.objects.get(pk=request_id)
        self.assertEqual(chat_request.status, SeoChatRequest.STATUS_COMPLETED)

    @patch("seo_assistant.views.run_chat")
    def test_cancel_marker_arriving_first_prevents_chat(self, mocked_run_chat):
        request_id = uuid4()
        cancel = self.client.post(
            f"/api/seo-assistant/admin/chat/{request_id}/cancel/",
            {},
            format="json",
        )
        chat = self.client.post(
            "/api/seo-assistant/admin/chat/",
            {
                "request_id": str(request_id),
                "session_key": "cancel-first",
                "message": "این درخواست نباید اجرا شود",
            },
            format="json",
        )

        self.assertEqual(cancel.status_code, status.HTTP_200_OK, cancel.data)
        self.assertTrue(cancel.data["cancelled"])
        self.assertEqual(chat.status_code, status.HTTP_200_OK, chat.data)
        self.assertTrue(chat.data["cancelled"])
        mocked_run_chat.assert_not_called()
        self.assertFalse(SeoConversation.objects.filter(session_key="cancel-first").exists())

    def test_cancel_endpoint_removes_partial_messages(self):
        conversation = SeoConversation.objects.create(session_key="partial", user=self.user)
        chat_request = SeoChatRequest.objects.create(
            request_id=uuid4(),
            conversation=conversation,
            user=self.user,
        )
        SeoMessage.objects.create(
            conversation=conversation,
            chat_request=chat_request,
            role=SeoMessage.ROLE_USER,
            content="پیام نیمه‌کاره",
        )

        response = self.client.post(
            f"/api/seo-assistant/admin/chat/{chat_request.request_id}/cancel/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        chat_request.refresh_from_db()
        self.assertEqual(chat_request.status, SeoChatRequest.STATUS_CANCELLED)
        self.assertTrue(chat_request.cancel_requested)
        self.assertFalse(SeoMessage.objects.filter(chat_request=chat_request).exists())

    def test_cancellation_wins_race_with_late_completion(self):
        request_id = uuid4()

        def late_reply(conversation, _message, _cfg, *, chat_request, **_kwargs):
            SeoMessage.objects.create(
                conversation=conversation,
                chat_request=chat_request,
                role=SeoMessage.ROLE_ASSISTANT,
                content="پاسخ دیررس",
            )
            SeoChatRequest.objects.filter(pk=chat_request.pk).update(
                cancel_requested=True,
                status=SeoChatRequest.STATUS_CANCELLED,
            )
            return "پاسخ دیررس"

        with patch("seo_assistant.views.run_chat", side_effect=late_reply):
            response = self.client.post(
                "/api/seo-assistant/admin/chat/",
                {
                    "request_id": str(request_id),
                    "session_key": "late-completion",
                    "message": "این پاسخ باید کنار گذاشته شود",
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["cancelled"])
        self.assertEqual(response.data["reply"], "")
        chat_request = SeoChatRequest.objects.get(pk=request_id)
        self.assertEqual(chat_request.status, SeoChatRequest.STATUS_CANCELLED)
        self.assertFalse(SeoMessage.objects.filter(chat_request=chat_request).exists())

    @patch("seo_assistant.ai.retrieve", return_value=[])
    def test_run_chat_discards_messages_when_cancelled_mid_run(self, _mocked_retrieve):
        conversation = SeoConversation.objects.create(session_key="mid-run", user=self.user)
        chat_request = SeoChatRequest.objects.create(
            request_id=uuid4(),
            conversation=conversation,
            user=self.user,
        )
        states = iter([False, False, True])

        with self.assertRaises(SeoAssistantCancelled):
            run_chat(
                conversation,
                "درخواست طولانی",
                SeoAssistantSettings.load(),
                chat_request=chat_request,
                cancel_check=lambda: next(states),
            )

        self.assertFalse(SeoMessage.objects.filter(chat_request=chat_request).exists())
