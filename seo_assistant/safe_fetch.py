"""Only fetch HTTPS pages on explicitly trusted sites; never follow redirects."""
import ipaddress
import socket
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

from django.conf import settings


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_target(url):
    parsed = urlsplit(url)
    default_host = urlsplit(getattr(settings, "FRONTEND_BASE", "")).hostname
    allowed = getattr(settings, "SEO_FETCH_ALLOWED_HOSTS", (default_host,))
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.hostname not in allowed
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ValueError("SEO fetch is restricted to configured HTTPS sites.")
    # The allowlist must contain domains controlled by the operator. Arbitrary
    # user-controlled domains are deliberately unsupported (DNS rebinding).
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Private or non-public network targets are not allowed.")


def open_trusted_page(request, timeout):
    validate_target(request.full_url)
    # Disable environment proxies as well as redirects to unchecked hosts.
    return build_opener(ProxyHandler({}), NoRedirects()).open(request, timeout=timeout)
