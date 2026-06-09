import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from products.serializers import SellerSerializer

from .models import Profile, VerificationResend
from .serializers import ProfileSerializer

User = get_user_model()


def _build_verification_url(request, user_pk):
    signer = TimestampSigner()
    token = signer.sign(str(user_pk))
    base = request.build_absolute_uri("/").rstrip("/")
    return f"{base}/api/auth/verify-email/?token={token}"


def _send_verification_email(user, verify_url):
    subject = "Email verification"
    message = (
        "Please click this link to verify your email address:\n"
        f"{verify_url}\n\n"
        "After verification, sign in to your account."
    )
    try:
        return send_mail(
            subject,
            message,
            getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
            [user.email],
        )
    except Exception:
        return 0


class RegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = (request.data.get("username") or "").strip()
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password")
        phone = (request.data.get("phone") or "").strip()

        # ایمیل اختیاری است؛ فقط نام‌کاربری و رمز اجباری‌اند.
        if not username or not password:
            return Response(
                {"detail": "username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not re.match(r"^[a-zA-Z0-9_]{3,}$", username):
            return Response(
                {"detail": "username must use English letters, digits or underscore (min 3 chars)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {"detail": "username already taken."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if email and User.objects.filter(email__iexact=email).exists():
            return Response(
                {"detail": "email already registered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # با ایمیل: همان جریان غیرفعال + ایمیل تأیید. بدون ایمیل: چون کانال
        # تأیید دیگری نیست، حساب فوراً فعال می‌شود تا کاربر بتواند وارد شود.
        has_email = bool(email)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=not has_email,
        )

        if phone:
            Profile.objects.update_or_create(user=user, defaults={"phone": phone})

        sent = 0
        if has_email:
            verify_url = _build_verification_url(request, user.pk)
            sent = _send_verification_email(user, verify_url)

        resp = {
            "user": {
                "id": user.pk,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
            },
            "detail": "verification_sent" if has_email else "registered_active",
        }
        if has_email:
            resp["email_sent"] = bool(sent)
            resp["email_sent_count"] = int(sent)
            if not sent:
                resp["warning"] = "mail_send_failed_or_zero"
        return Response(resp, status=status.HTTP_201_CREATED)


class GoogleAuthAPIView(APIView):
    """ورود/ثبت‌نام با گوگل: ID token را تأیید و JWT برمی‌گرداند."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
        if not client_id:
            return Response(
                {"detail": "google_login_unconfigured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        credential = request.data.get("credential")
        if not credential:
            return Response(
                {"detail": "credential is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            info = google_id_token.verify_oauth2_token(
                credential, google_requests.Request(), client_id
            )
        except Exception:
            return Response(
                {"detail": "invalid_google_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = (info.get("email") or "").strip()
        sub = info.get("sub") or ""

        user = User.objects.filter(email__iexact=email).first() if email else None

        if user is None:
            base = email.split("@")[0] if email else f"g_{sub}"
            base = re.sub(r"[^a-zA-Z0-9_]", "", base)[:20] or f"g_{sub}"
            username = base
            suffix = 0
            while User.objects.filter(username=username).exists():
                suffix += 1
                username = f"{base}_{suffix}"
            user = User.objects.create_user(username=username, email=email, is_active=True)
            Profile.objects.get_or_create(user=user)
        elif not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])

        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.pk,
                    "username": user.username,
                    "email": user.email,
                    "is_active": user.is_active,
                },
            },
            status=status.HTTP_200_OK,
        )


class ProfileAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.is_active:
            return Response(
                {"detail": "email_not_verified"},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = {
            "id": user.pk,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        }
        seller = getattr(user, "seller_profile", None)
        data["seller"] = SellerSerializer(seller).data if seller else None
        return Response(data)


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        token = request.query_params.get("token")
        if not token:
            return Response(
                {"detail": "invalid_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        signer = TimestampSigner()
        try:
            unsigned = signer.unsign(token, max_age=60 * 60 * 24)
            user_pk = int(unsigned)
            user = User.objects.get(pk=user_pk)
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active"])

            frontend_base = getattr(settings, "FRONTEND_BASE", "http://localhost:3000")
            return redirect(f"{frontend_base}/auth/login?verified=1")
        except SignatureExpired:
            return Response({"detail": "token_expired"}, status=status.HTTP_400_BAD_REQUEST)
        except (BadSignature, User.DoesNotExist, ValueError):
            return Response({"detail": "invalid_token"}, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user = None

        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            email = (request.data.get("email") or "").strip()
            if not email:
                return Response(
                    {"detail": "email_required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                return Response(
                    {"detail": "user_not_found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if user.is_active:
            return Response(
                {"detail": "already_verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.email:
            return Response(
                {"detail": "email_missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        window_hours = getattr(settings, "VERIFICATION_RESEND_WINDOW_HOURS", 24)
        max_resends = getattr(settings, "VERIFICATION_RESEND_MAX", 5)

        now = timezone.now()
        resend, created = VerificationResend.objects.get_or_create(
            user=user,
            defaults={"count": 0, "window_start": now},
        )

        if not created and (now - resend.window_start) > timedelta(hours=window_hours):
            resend.count = 0
            resend.window_start = now

        if resend.count >= max_resends:
            return Response(
                {"detail": "rate_limited", "allowed": max_resends},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        resend.count += 1
        resend.save(update_fields=["count", "window_start"])

        verify_url = _build_verification_url(request, user.pk)
        sent = _send_verification_email(user, verify_url)

        resp = {
            "email_sent": bool(sent),
            "email_sent_count": int(sent),
            "resend_count": resend.count,
        }
        if not sent:
            resp["warning"] = "mail_send_failed_or_zero"
        return Response(resp, status=status.HTTP_200_OK)


class ProfileDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        profile, _created = Profile.objects.get_or_create(user=self.request.user)
        return profile
