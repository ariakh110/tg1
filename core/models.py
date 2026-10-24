
from django.db import models
from utils.model_abstracts import Model
from django_extensions.db.models import (
	TimeStampedModel, 
	ActivatorModel,
	TitleDescriptionModel
)

class Contact(
	TimeStampedModel, 
	ActivatorModel,
	TitleDescriptionModel,
	Model
	):

	class Meta:
		verbose_name_plural = "Contacts"

	email = models.EmailField(verbose_name="Email")

	def __str__(self):
		return f'{self.title}'


class SiteSettings(models.Model):
	"""تنظیمات سراسری سایت (تک‌نمونه‌ای) — نام سایت و کلیدهای فعال/غیرفعال بخش‌ها."""

	GLOBAL_METALS_PROVIDER_METALS_DEV = "metals_dev"
	GLOBAL_METALS_PROVIDER_CHOICES = [
		(GLOBAL_METALS_PROVIDER_METALS_DEV, "Metals.Dev"),
	]

	# خالی یعنی «از پیش‌فرض فرانت استفاده کن»؛ ادمین می‌تواند نام دلخواه را اینجا بگذارد.
	site_name = models.CharField(max_length=120, blank=True, default="")
	marketplace_enabled = models.BooleanField(default=False)   # بارانداز کاربران (/orders)
	featured_loads_enabled = models.BooleanField(default=True)  # بارانداز ویژه (/barandaz)
	export_enabled = models.BooleanField(default=True)          # صادرات (/export)
	offers_enabled = models.BooleanField(default=True)          # پیشنهادهای ویژه (/offers)
	blog_enabled = models.BooleanField(default=True)            # وبلاگ (/blog)
	google_oauth_client_id = models.CharField(max_length=255, blank=True, default="")  # Client ID گوگل (مدیریت از پنل)
	google_tag_manager_id = models.CharField(max_length=20, blank=True, default="")  # GTM-XXXXXXX (تزریق در فرانت)
	openai_api_key = models.CharField(max_length=255, blank=True, default="")  # کلید OpenAI (محرمانه؛ در API عمومی برنمی‌گردد)
	openai_content_model = models.CharField(max_length=80, blank=True, default="")  # مدل OpenAI برای سئو
	global_metals_enabled = models.BooleanField(default=True)
	global_metals_auto_refresh = models.BooleanField(default=True)
	ime_auto_refresh = models.BooleanField(default=True)
	ime_refresh_minutes = models.PositiveSmallIntegerField(default=30)
	global_metals_provider = models.CharField(
		max_length=32,
		choices=GLOBAL_METALS_PROVIDER_CHOICES,
		default=GLOBAL_METALS_PROVIDER_METALS_DEV,
	)
	global_metals_api_key = models.CharField(max_length=255, blank=True, default="")
	global_metals_refresh_hours = models.PositiveSmallIntegerField(default=20)
	global_metals_visible_codes = models.JSONField(null=True, blank=True, default=None)
	head_scripts = models.TextField(blank=True, default="")  # اسکریپت‌های هدر: داخل <head> تزریق می‌شوند (Analytics/Clarity/verification)
	footer_scripts = models.TextField(blank=True, default="")  # اسکریپت‌های فوتر: پیش از پایان <body> تزریق می‌شوند
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Site Settings"
		verbose_name_plural = "Site Settings"

	def __str__(self):
		return self.site_name

	def save(self, *args, **kwargs):
		# همیشه یک رکورد (singleton)
		self.pk = 1
		super().save(*args, **kwargs)

	@classmethod
	def load(cls):
		obj, _created = cls.objects.get_or_create(pk=1)
		return obj
