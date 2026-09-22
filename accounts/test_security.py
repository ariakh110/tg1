from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import caches
from rest_framework.test import APITestCase

from core.models import SiteSettings


class AuthenticationSecurityTests(APITestCase):
    def setUp(self):
        caches["authentication"].clear()
        config = SiteSettings.load()
        config.google_oauth_client_id = "test-client"
        config.save()

    def tearDown(self):
        caches["authentication"].clear()

    def google_login(self, **claims):
        token = {"sub": "test-sub", "email": "member@gmail.com", "email_verified": True}
        token.update(claims)
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=token):
            return self.client.post("/api/auth/google/", {"credential": "test"}, format="json")

    def test_google_does_not_reactivate_suspended_account(self):
        user = get_user_model().objects.create_user(
            username="member", email="member@gmail.com", is_active=False
        )
        response = self.google_login()
        self.assertEqual(response.status_code, 403)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertNotIn("access", response.data)

    def test_google_rejects_unverified_email(self):
        self.assertEqual(self.google_login(email_verified=False).status_code, 403)
        self.assertFalse(get_user_model().objects.exists())

    def test_google_rejects_third_party_email_without_linking_proof(self):
        self.assertEqual(self.google_login(email="member@example.com").status_code, 403)

    def test_verified_active_google_user_can_login(self):
        get_user_model().objects.create_user(username="member", email="member@gmail.com")
        self.assertEqual(self.google_login().status_code, 200)

    def test_registration_rejects_weak_password(self):
        response = self.client.post(
            "/api/auth/register/", {"username": "new_member", "password": "123"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username="new_member").exists())

    def test_repeated_login_attempts_are_throttled(self):
        for _ in range(10):
            response = self.client.post("/api/token/", {"username": "missing", "password": "bad"})
            self.assertEqual(response.status_code, 401)
        response = self.client.post("/api/token/", {"username": "missing", "password": "bad"})
        self.assertEqual(response.status_code, 429)
