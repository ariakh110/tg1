from django.core.cache import caches
from rest_framework.throttling import SimpleRateThrottle


class AuthenticationThrottle(SimpleRateThrottle):
    scope = "authentication"
    rate = "10/min"

    @property
    def cache(self):
        return caches["authentication"]

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
