from django.contrib import admin
from .models import Contact, SiteSettings



@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('id','title', 'description','email')


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'google_oauth_client_id', 'google_tag_manager_id', 'openai_content_model', 'marketplace_enabled', 'featured_loads_enabled', 'export_enabled', 'offers_enabled', 'blog_enabled', 'updated_at')