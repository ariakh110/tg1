from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import ProfileSerializer, SetRoleSerializer, SellerCreateFromProfileSerializer, UserSerializer
from .models import Profile
from products.models import Seller
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from products.serializers import SellerSerializer  # اگر SellerSerializer آنجاست
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class RegisterAPIView(APIView):
    """
    ثبت‌نام ساده: کاربر ساخته می‌شود و توکن JWT برگشت داده می‌شود.
    Frontend پس از دریافت توکن، کاربر را به صفحهٔ تکمیل پروفایل هدایت کند.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not username or not password:
            return Response({"detail": "username and password required."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"detail": "username already taken."}, status=status.HTTP_400_BAD_REQUEST)

        # create user as inactive until email confirmed
        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_active = False
        user.save()

        # create signed token with timestamp
        signer = TimestampSigner()
        token = signer.sign(str(user.pk))

        # build backend verify URL so clicking the link activates the account server-side
        base = request.build_absolute_uri("/").rstrip("/")
        verify_url = f"{base}/api/auth/verify-email/?token={token}"

        # send email (in DEBUG console backend will print)
        subject = "تایید ایمیل — فروشگاه"
        message = (
            "لطفا برای تایید ایمیل خود روی لینک زیر کلیک کنید:\n"
            + verify_url
            + "\n\nپس از تایید، به صفحهٔ تعیین نوع کاربری هدایت می‌شوید."
        )
        # send email and capture result (number of successfully delivered messages)
        try:
            sent = send_mail(subject, message, getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"), [user.email])
        except Exception as e:
            sent = 0

        # return 201 but do not issue tokens until verified
        resp = {
            "user": {"id": user.pk, "username": user.username, "email": user.email},
            "detail": "verification_sent",
            "email_sent": bool(sent),
            "email_sent_count": int(sent),
        }
        if not sent:
            resp["warning"] = "mail_send_failed_or_zero"
        return Response(resp, status=status.HTTP_201_CREATED)


class ProfileAPIView(APIView):
    """
    برگرداندن اطلاعات کاربر جاری و پروفایل فروشنده اگر داشته باشد.
    GET /api/auth/profile/
    """
    # ensure only JWT auth is accepted here (no session auth leakage)
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # defensive check: if not authenticated, return 401
        user = request.user
        # block access if user's email not verified
        if not user.is_active:
            return Response({"detail": "email_not_verified"}, status=status.HTTP_403_FORBIDDEN)
        if not getattr(user, "is_authenticated", False):
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        data = {
            "id": user.pk,
            "username": user.username,
            "email": user.email,
        }
        # اگر Seller profile وجود دارد اضافه شود (related name seller_profile)
        try:
            seller = getattr(user, "seller_profile", None)
            if seller:
                data["seller"] = SellerSerializer(seller).data
            else:
                data["seller"] = None
        except Exception:
            data["seller"] = None

        return Response(data)


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        token = request.query_params.get("token")
        signer = TimestampSigner()
        try:
            unsigned = signer.unsign(token, max_age=60 * 60 * 24)  # 1 day
            user_pk = int(unsigned)
            user = User.objects.get(pk=user_pk)
            user.is_active = True
            user.save()
            # Issue JWT tokens for the user so frontend can auto-login immediately
            try:
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
            except Exception:
                access_token = ""
                refresh_token = ""

            # redirect the user to frontend profile-setup page including tokens
            frontend_base = getattr(settings, "FRONTEND_BASE", "http://localhost:3000")
            qs = f"verified=1"
            if access_token:
                qs += f"&access={access_token}&refresh={refresh_token}"
            return redirect(f"{frontend_base}/auth/profile-setup?{qs}")
        except SignatureExpired:
            return Response({"detail": "token_expired"}, status=status.HTTP_400_BAD_REQUEST)
        except (BadSignature, User.DoesNotExist, ValueError):
            return Response({"detail": "invalid_token"}, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationEmailView(APIView):
    """
    Endpoint to resend verification email to the currently authenticated user.
    - Only for authenticated users who are not yet active.
    - Returns {email_sent: bool, email_sent_count: int}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.is_active:
            return Response({"detail": "already_verified"}, status=status.HTTP_400_BAD_REQUEST)

        # Rate limit: max N resends per WINDOW hours
        WINDOW_HOURS = getattr(settings, 'VERIFICATION_RESEND_WINDOW_HOURS', 24)
        MAX_RESENDS = getattr(settings, 'VERIFICATION_RESEND_MAX', 5)
        from .models import VerificationResend

        now = timezone.now()
        vr, created = VerificationResend.objects.get_or_create(user=user, defaults={
            'count': 0,
            'window_start': now,
        })

        # reset window if expired
        if not created and (now - vr.window_start) > timedelta(hours=WINDOW_HOURS):
            vr.count = 0
            vr.window_start = now

        if vr.count >= MAX_RESENDS:
            return Response({"detail": "rate_limited", "allowed": MAX_RESENDS}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # increment count and save
        vr.count += 1
        vr.save()

        signer = TimestampSigner()
        token = signer.sign(str(user.pk))
        base = request.build_absolute_uri("/").rstrip("/")
        verify_url = f"{base}/api/auth/verify-email/?token={token}"

        subject = "تایید ایمیل — فروشگاه"
        message = (
            "لطفا برای تایید ایمیل خود روی لینک زیر کلیک کنید:\n"
            + verify_url
            + "\n\nپس از تایید، به صفحهٔ تعیین نوع کاربری هدایت می‌شوید."
        )
        try:
            sent = send_mail(subject, message, getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"), [user.email])
        except Exception:
            sent = 0

        resp = {"email_sent": bool(sent), "email_sent_count": int(sent), "resend_count": vr.count}
        if not sent:
            resp["warning"] = "mail_send_failed_or_zero"
        return Response(resp, status=status.HTTP_200_OK)
    
class ProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    GET/PUT profile of current user
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user.profile

class SetRoleView(APIView):
    """
    User chooses role after login. If chooses SELLER, we can set company_requested flag
    or create Seller on demand.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SetRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        profile = request.user.profile
        profile.role = role
        if role == Profile.Role.SELLER:
            profile.company_requested = True
        profile.save()
        return Response(ProfileSerializer(profile).data, status=status.HTTP_200_OK)

class CreateSellerFromProfileView(APIView):
    """
    Create Seller (minisite) for authenticated user.
    Only allowed if profile.role in (SELLER, BOTH) or user requested seller.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = request.user.profile
        # allow creation if role allows or user requested
        if profile.role not in (Profile.Role.SELLER, Profile.Role.BOTH) and not profile.company_requested:
            return Response({"detail": "role not permitted to create seller"}, status=status.HTTP_403_FORBIDDEN)
        if hasattr(request.user, "seller_profile"):
            return Response({"detail": "seller profile already exists"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SellerCreateFromProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        seller = Seller.objects.create(user=request.user,
                                       company_name=serializer.validated_data["company_name"],
                                       business_type=serializer.validated_data.get("business_type",""),
                                       location=serializer.validated_data.get("location",""))
        # optionally set profile.role to BOTH
        profile.role = Profile.Role.BOTH
        profile.company_requested = False
        profile.save()
        return Response({"seller": {"id": seller.id, "company_name": seller.company_name}}, status=status.HTTP_201_CREATED)
