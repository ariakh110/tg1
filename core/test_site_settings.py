from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import SiteSettings


class SiteSettingsMarketConfigurationTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            "settings-admin", password="pass", is_staff=True
        )

    def test_admin_can_store_global_market_secret_without_exposing_it(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            "/api/site-settings/",
            {
                "global_metals": {
                    "enabled": True,
                    "provider": "metals_dev",
                    "api_key": "secret-market-key",
                    "refresh_hours": 12,
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["global_metals"]["api_key_configured"])
        self.assertNotIn("secret-market-key", str(response.data))
        config = SiteSettings.load()
        self.assertEqual(config.global_metals_api_key, "secret-market-key")
        self.assertEqual(config.global_metals_refresh_hours, 12)

    def test_non_admin_cannot_update_global_market_settings(self):
        user = get_user_model().objects.create_user("ordinary-user", password="pass")
        self.client.force_authenticate(user)

        response = self.client.patch(
            "/api/site-settings/",
            {"global_metals": {"api_key": "forbidden"}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(SiteSettings.load().global_metals_api_key, "")
