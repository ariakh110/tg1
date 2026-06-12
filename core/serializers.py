from . import models
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

	class Meta:
		model = models.SiteSettings
		fields = ('site_name', 'google_oauth_client_id', 'google_tag_manager_id', 'openai_content_model', 'openai_configured', 'sections')

	def get_openai_configured(self, obj):
		return bool(obj.openai_api_key)

	def get_sections(self, obj):
		return {
			'marketplace': obj.marketplace_enabled,
			'featured_loads': obj.featured_loads_enabled,
			'export': obj.export_enabled,
			'offers': obj.offers_enabled,
			'blog': obj.blog_enabled,
		}