"""Shared, atomic fixed-window quotas before any public AI work.

Production uses the authentication Redis cache. Gunicorn must remain behind the
trusted proxy configured by REST_FRAMEWORK.NUM_PROXIES; Nginx must overwrite XFF.
Fixed windows can admit up to twice the minute limit across a window boundary.
"""
import hashlib
import logging
import time

from django.conf import settings
from django.core.cache import caches
from rest_framework.exceptions import APIException
from rest_framework.throttling import BaseThrottle

logger = logging.getLogger(__name__)


class QuotaStorageUnavailable(APIException):
    status_code = 503
    default_detail = "دستیار موقتاً در دسترس نیست. کمی بعد دوباره تلاش کنید."
    default_code = "assistant_quota_unavailable"


class AssistantChatThrottle(BaseThrottle):
    def allow_request(self, request, view):
        self.retry_after = 60
        identities = ["ip:" + self.get_ident(request)]
        if request.user.is_authenticated:
            identities.append("user:" + str(request.user.pk))
        windows = [
            (60, int(getattr(settings, "ASSISTANT_CHAT_MINUTE_LIMIT", 10))),
            (86400, int(getattr(settings, "ASSISTANT_CHAT_DAILY_LIMIT", 100))),
        ]
        now = int(time.time())
        try:
            cache = caches["authentication"]
            for identity in identities:
                digest = hashlib.sha256(identity.encode()).hexdigest()
                for duration, limit in windows:
                    bucket = now // duration
                    ttl = duration - now % duration
                    key = f"assistant-chat:v1:{digest}:{duration}:{bucket}"
                    # Redis ADD is SET NX; INCR is atomic across workers.
                    count = 1 if cache.add(key, 1, timeout=ttl + 1) else cache.incr(key)
                    if count > limit:
                        self.retry_after = ttl
                        return False
        except Exception:
            # Never allow an unmetered paid AI request if Redis is unavailable.
            logger.warning("Assistant request denied: quota cache unavailable")
            raise QuotaStorageUnavailable() from None
        return True

    def wait(self):
        return self.retry_after
