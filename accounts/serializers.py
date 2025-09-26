from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile
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
