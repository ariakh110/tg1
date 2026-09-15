"""Local development settings: python manage.py runserver --settings=tg1.settings_local."""

from .settings import *  # noqa: F403,F401

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.local.sqlite3",  # noqa: F405
    }
}
MEDIA_ROOT = BASE_DIR / "media-local"  # noqa: F405

CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy()
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
FRONTEND_BASE = "http://localhost:3000"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Execute queued work immediately during local development without Redis/worker setup.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
