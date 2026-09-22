"""Production settings; load secrets from the service environment."""
from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F401,F403

if not os.environ.get("DJANGO_SECRET_KEY") or SECRET_KEY == "change-me-local-dev-key":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set for production.")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must contain at least 50 characters.")
if not os.environ.get("DJANGO_ALLOWED_HOSTS") or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Explicit DJANGO_ALLOWED_HOSTS are required.")
if not os.environ.get("DB_PASSWORD"):
    raise ImproperlyConfigured("DB_PASSWORD must be set for production.")

DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# Gunicorn must bind to loopback, and Nginx must overwrite X-Forwarded-For
# with $remote_addr. Do not expose Gunicorn directly with this proxy count.
REST_FRAMEWORK = {**REST_FRAMEWORK, "NUM_PROXIES": 1}
CACHES = {
    **CACHES,
    "authentication": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("AUTH_THROTTLE_REDIS_URL", "redis://127.0.0.1:6379/2"),
        "KEY_PREFIX": "tirexa-auth",
    },
}
