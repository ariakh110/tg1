from django.contrib import admin

from .models import KYCDocument, KYCRequest, Profile, UserRole

admin.site.register(Profile)
admin.site.register(UserRole)
admin.site.register(KYCRequest)
admin.site.register(KYCDocument)
