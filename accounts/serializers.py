from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile, UserRole, RoleCode, KYCRequest, KYCDocument
from products.models import Seller
from products.serializers import SellerSerializer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id","username","email","first_name","last_name")

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    # expose the related Seller (if any) so /me/ contains company fields
    seller = SellerSerializer(source='user.seller_profile', read_only=True)
    class Meta:
        model = Profile
        fields = ("id","user","role","phone","country","language","company_requested","vat_number","seller")
        read_only_fields = ("company_requested",)

class SetRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Profile.Role.choices)

class SellerCreateFromProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = ("company_name","business_type","location")


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
    requested_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=RoleCode.choices)
    )
    documents = KYCDocumentSerializer(many=True, required=False)

    class Meta:
        model = KYCRequest
        fields = (
            "id",
            "requested_roles",
            "status",
            "submitted_at",
            "reviewed_at",
            "reject_reason",
            "documents",
        )
        read_only_fields = ("status", "submitted_at", "reviewed_at", "reject_reason")

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
        fields = ("id", "username", "email", "roles", "kyc_status")

    def get_kyc_status(self, obj):
        latest = obj.kyc_requests.order_by("-submitted_at").first()
        return latest.status if latest else None
