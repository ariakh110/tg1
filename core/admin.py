from django.contrib import admin
from .models import Contact, SiteSettings



@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('id','title', 'description','email')


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
	list_display = ('site_name', 'global_metals_enabled', 'global_metals_provider', 'global_metals_refresh_hours', 'google_oauth_client_id', 'google_tag_manager_id', 'openai_content_model', 'marketplace_enabled', 'featured_loads_enabled', 'export_enabled', 'offers_enabled', 'blog_enabled', 'updated_at')
	fieldsets = (
		(None, {'fields': ('site_name',)}),
		('بازار جهانی فلزات', {'fields': ('global_metals_enabled', 'global_metals_provider', 'global_metals_api_key', 'global_metals_refresh_hours')}),
		('ورود و سرویس‌ها', {'fields': ('google_oauth_client_id', 'google_tag_manager_id', 'openai_api_key', 'openai_content_model')}),
		('بخش‌های سایت', {'fields': ('marketplace_enabled', 'featured_loads_enabled', 'export_enabled', 'offers_enabled', 'blog_enabled')}),
		('اسکریپت‌های سفارشی', {'fields': ('head_scripts', 'footer_scripts')}),
	)
