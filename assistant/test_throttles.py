from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import AssistantSettings


class AssistantQuotaTests(APITestCase):
    def setUp(self):
        caches["authentication"].clear()
        cfg = AssistantSettings.load()
        cfg.is_enabled = True
        cfg.save()

    def send(self, key="session"):
        return self.client.post("/api/assistant/chat/", {"message": "hello", "session_key": key}, format="json")

    @override_settings(ASSISTANT_CHAT_MINUTE_LIMIT=2, ASSISTANT_CHAT_DAILY_LIMIT=3)
    @patch("assistant.views.run_chat", return_value="reply")
    @patch("assistant.throttles.time.time", return_value=1800000000)
    def test_burst_cannot_be_bypassed_with_new_session(self, clock, chat):
        self.assertEqual(self.send("one").status_code, 200)
        self.assertEqual(self.send("two").status_code, 200)
        response = self.send("three")
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
        self.assertEqual(chat.call_count, 2)
        clock.return_value += 61
        self.assertEqual(self.send("four").status_code, 200)
        self.assertEqual(self.send("five").status_code, 429)
        self.assertEqual(chat.call_count, 3)
        clock.return_value += 86400
        self.assertEqual(self.send("six").status_code, 200)

    @override_settings(ASSISTANT_CHAT_MINUTE_LIMIT=1)
    @patch("assistant.views.run_chat", return_value="reply")
    def test_ip_quota_survives_login_changes(self, chat):
        self.assertEqual(self.send().status_code, 200)
        user = get_user_model().objects.create_user("quota-user")
        self.client.force_authenticate(user)
        self.assertEqual(self.send("new-session").status_code, 429)
        self.assertEqual(chat.call_count, 1)

    @patch("assistant.views.run_chat", return_value="reply")
    @patch("assistant.throttles.caches")
    def test_cache_error_does_not_call_ai(self, cache_registry, chat):
        cache_registry.__getitem__.return_value.add.side_effect = ConnectionError("offline")
        self.assertEqual(self.send().status_code, 503)
        chat.assert_not_called()

    @override_settings(ASSISTANT_CHAT_MINUTE_LIMIT=1)
    @patch("assistant.views.run_chat", return_value="reply")
    def test_user_quota_survives_ip_changes(self, chat):
        user = get_user_model().objects.create_user("mobile-quota-user")
        self.client.force_authenticate(user)
        self.assertEqual(self.send().status_code, 200)
        self.client.defaults["REMOTE_ADDR"] = "192.0.2.2"
        self.assertEqual(self.send("another-ip").status_code, 429)
        self.assertEqual(chat.call_count, 1)

    @override_settings(ASSISTANT_CHAT_MINUTE_LIMIT=3)
    def test_concurrent_requests_cannot_exceed_quota(self):
        from concurrent.futures import ThreadPoolExecutor
        from types import SimpleNamespace
        from .throttles import AssistantChatThrottle
        from rest_framework.test import APIRequestFactory
        request = APIRequestFactory().post("/api/assistant/chat/", REMOTE_ADDR="192.0.2.3")
        request.user = SimpleNamespace(is_authenticated=False)
        with ThreadPoolExecutor(max_workers=8) as pool:
            allowed = list(pool.map(lambda _: AssistantChatThrottle().allow_request(request, None), range(24)))
        self.assertEqual(sum(allowed), 3)
