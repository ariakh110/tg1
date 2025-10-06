from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import status
from rest_framework.response import Response


class ActiveUserTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        if not user.is_active:
            raise Exception("inactive_account")
        return data


class ActiveUserTokenObtainPairView(TokenObtainPairView):
    serializer_class = ActiveUserTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            # return a friendly 401 JSON
            return Response({"detail": "Account inactive or credentials invalid."}, status=status.HTTP_401_UNAUTHORIZED)
