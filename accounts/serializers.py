from django.contrib.auth import get_user_model
from rest_framework import serializers

from products.serializers import SellerSerializer

from .models import KYCDocument, KYCRequest, KYCStatus, RoleCode, Profile, UserRole

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    seller = SellerSerializer(source="user.seller_profile", read_only=True)

    class Meta:
        model = Profile
        fields = ("id", "user", "phone", "country", "language", "vat_number", "seller")


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = ("id", "role", "is_active", "assigned_at", "activated_at")


class KYCDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = KYCDocument
        fields = ("id", "name", "file", "file_url", "uploaded_at")
        read_only_fields = ("file_url", "uploaded_at")

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file:
            try:
                url = obj.file.url
            except ValueError:
                return None
            return request.build_absolute_uri(url) if request else url
        return None


class KYCRequestSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    requested_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=RoleCode.choices)
    )
    documents = KYCDocumentSerializer(many=True, required=False)

    class Meta:
        model = KYCRequest
        fields = (
            "id",
            "user",
            "requested_roles",
            "status",
            "submitted_at",
            "reviewed_at",
            "reject_reason",
            "documents",
        )
        read_only_fields = ("user", "status", "submitted_at", "reviewed_at", "reject_reason")

    def validate_requested_roles(self, roles):
        if not roles:
            raise serializers.ValidationError("At least one role is required.")
        disallowed = {RoleCode.BUYER, RoleCode.ADMIN}
        invalid = [role for role in roles if role in disallowed]
        if invalid:
            raise serializers.ValidationError("Requested role does not require KYC.")
        return roles

    def create(self, validated_data):
        documents_data = validated_data.pop("documents", [])
        user = self.context["request"].user
        kyc = KYCRequest.objects.create(user=user, **validated_data)
        for doc in documents_data:
            KYCDocument.objects.create(kyc_request=kyc, **doc)
        return kyc


class KYCRequestAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCRequest
        fields = ("status", "reviewed_at", "reject_reason")


class UserMeSerializer(serializers.ModelSerializer):
    roles = UserRoleSerializer(many=True, read_only=True)
    kyc_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "is_staff",
            "is_superuser",
            "roles",
            "kyc_status",
        )

    def get_kyc_status(self, obj):
        latest = obj.kyc_requests.order_by("-submitted_at").first()
        return latest.status if latest else None


class AdminUserSummarySerializer(serializers.ModelSerializer):
    roles = UserRoleSerializer(many=True, read_only=True)
    kyc_status = serializers.SerializerMethodField()
    pending_kyc_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "roles",
            "kyc_status",
            "pending_kyc_count",
        )

    def get_kyc_status(self, obj):
        latest = obj.kyc_requests.order_by("-submitted_at").first()
        return latest.status if latest else None

    def get_pending_kyc_count(self, obj):
        return obj.kyc_requests.filter(status=KYCStatus.PENDING).count()


class AdminSetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, write_only=True, trim_whitespace=False)


class AdminSetRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=RoleCode.choices)
    is_active = serializers.BooleanField(default=True)


class AdminSetActiveSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()
