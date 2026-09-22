import socket
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .safe_fetch import NoRedirects, validate_target


@override_settings(SEO_FETCH_ALLOWED_HOSTS=("example.com",))
class SafeFetchTests(SimpleTestCase):
    def test_untrusted_targets_are_rejected_before_dns(self):
        with patch("seo_assistant.safe_fetch.socket.getaddrinfo") as lookup:
            for url in ("http://example.com/", "https://127.0.0.1/", "https://example.com:5432/", "https://evil.test/", "https://user:pass@example.com/"):
                with self.assertRaises(ValueError):
                    validate_target(url)
            lookup.assert_not_called()

    def test_private_dns_answer_is_rejected(self):
        with patch("seo_assistant.safe_fetch.socket.getaddrinfo", return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))
        ]):
            with self.assertRaises(ValueError):
                validate_target("https://example.com/")

    def test_public_trusted_site_is_allowed(self):
        with patch("seo_assistant.safe_fetch.socket.getaddrinfo", return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ]):
            validate_target("https://example.com/products")

    def test_redirect_to_metadata_is_not_followed(self):
        self.assertIsNone(NoRedirects().redirect_request(None, None, 302, "Found", {}, "http://169.254.169.254/"))
