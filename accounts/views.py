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

        user = User.objects.create_user(username=username, email=email, password=password)
        # optionally: user.is_active = False -> email confirm flow

        refresh = RefreshToken.for_user(user)
        return Response({
            "user": {"id": user.pk, "username": user.username, "email": user.email},
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_201_CREATED)


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
