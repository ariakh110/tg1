from . import models
from django.conf import settings
from rest_framework import serializers
from rest_framework.fields import CharField, EmailField



class ContactSerializer(serializers.ModelSerializer):

	name = CharField(source="title", required=True)
	message = CharField(source="description", required=True)
	email = EmailField(required=True)
	
	class Meta:
		model = models.Contact
		fields = (
			'name',
			'email',
			'message'
		)


class SiteSettingsSerializer(serializers.ModelSerializer):
	sections = serializers.SerializerMethodField()
	openai_configured = serializers.SerializerMethodField()
	global_metals = serializers.SerializerMethodField()

	class Meta:
		model = models.SiteSettings
		fields = ('site_name', 'google_oauth_client_id', 'google_tag_manager_id', 'openai_content_model', 'openai_configured', 'head_scripts', 'footer_scripts', 'sections', 'global_metals')

	def get_openai_configured(self, obj):
		return bool(obj.openai_api_key)

	def get_global_metals(self, obj):
		from products.external_markets import available_global_metals
		return {
			'enabled': obj.global_metals_enabled,
			'provider': obj.global_metals_provider,
			'provider_label': obj.get_global_metals_provider_display(),
			'api_key_configured': bool(obj.global_metals_api_key or getattr(settings, 'METALS_DEV_API_KEY', '')),
			'refresh_hours': obj.global_metals_refresh_hours,
			'visible_codes': obj.global_metals_visible_codes,
			'available_instruments': available_global_metals(),
		}

	def get_sections(self, obj):
		return {
			'marketplace': obj.marketplace_enabled,
			'featured_loads': obj.featured_loads_enabled,
			'export': obj.export_enabled,
			'offers': obj.offers_enabled,
			'blog': obj.blog_enabled,
		}
