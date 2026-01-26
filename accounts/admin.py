from django.contrib import admin

from .models import KYCDocument, KYCRequest, Profile, UserRole


class KYCDocumentInline(admin.TabularInline):
    model = KYCDocument
    extra = 0
    fields = ("name", "file", "uploaded_at")
    readonly_fields = ("uploaded_at",)


@admin.register(KYCRequest)
class KYCRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "submitted_at", "reviewed_at", "documents_count")
    list_filter = ("status", "submitted_at", "reviewed_at")
    search_fields = ("user__username", "user__email")
    inlines = [KYCDocumentInline]

    def documents_count(self, obj):
        return obj.documents.count()

    documents_count.short_description = "Documents"


admin.site.register(Profile)
admin.site.register(UserRole)
admin.site.register(KYCDocument)
