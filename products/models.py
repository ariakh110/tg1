import datetime

from django.db import models
from django.conf import settings
from mptt.models import MPTTModel, TreeForeignKey
from django.utils.text import slugify

# Optional Jalali support using the `jdatetime` package
try:
    import jdatetime
except Exception:
    jdatetime = None


class JalaliDateTimeField(models.DateTimeField):
    """A DateTimeField wrapper that returns jdatetime.datetime on read when
    the `jdatetime` package is available, and accepts jdatetime values on write
    (converting them back to Gregorian datetimes for DB storage).

    If `jdatetime` is not installed this behaves exactly like a normal
    DateTimeField.
    """

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        if jdatetime is None:
            return value
        try:
            return jdatetime.datetime.fromgregorian(datetime=value)
        except Exception:
            return value

    def to_python(self, value):
        # value can be jdatetime.datetime, datetime.datetime or string
        if value is None:
            return None
        if jdatetime is None:
            return super().to_python(value)
        if isinstance(value, jdatetime.datetime):
            return value
        # If it's a native datetime, convert to jdatetime
        try:
            return jdatetime.datetime.fromgregorian(datetime=value)
        except Exception:
            return super().to_python(value)

    def get_prep_value(self, value):
        # Convert jdatetime to gregorian datetime for DB storage
        if value is None:
            return None
        if jdatetime is None:
            return super().get_prep_value(value)
        if isinstance(value, jdatetime.datetime):
            try:
                return value.togregorian()
            except Exception:
                return super().get_prep_value(value)
        if isinstance(value, datetime.datetime):
            return value
        return super().get_prep_value(value)


# ----------- فروشنده -----------
class Seller(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller_profile')
    company_name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False)
    created_at = JalaliDateTimeField(auto_now_add=True)
    updated_at = JalaliDateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name


# ----------- دسته‌بندی سلسله مراتبی -----------
class ProductCategory(MPTTModel):
    name = models.CharField(max_length=255, unique=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    hscode = models.CharField(max_length=20, unique=True, null=True, blank=True)
    code = models.CharField(max_length=80, unique=True, null=True, blank=True)
    product_kind = models.CharField(max_length=50, blank=True, default="")
    spec_defaults = models.JSONField(default=dict, blank=True)
    required_spec_fields = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class MPTTMeta:
        order_insertion_by = ['sort_order', 'name']

    def spec_chain(self):
        return self.get_ancestors(include_self=True)

    def merged_spec_defaults(self):
        defaults = {}
        for category in self.spec_chain():
            defaults.update(category.spec_defaults or {})
        return defaults

    def merged_required_spec_fields(self):
        fields = []
        for category in self.spec_chain():
            for field in category.required_spec_fields or []:
                if field not in fields:
                    fields.append(field)
        return fields

    def resolved_product_kind(self):
        for category in reversed(list(self.spec_chain())):
            if category.product_kind:
                return category.product_kind
        return ""

    def __str__(self):
        return self.name


# ----------- محصول (تعریف کلی) -----------
class Product(models.Model):
    AVAILABILITY_IN_STOCK = "in_stock"
    AVAILABILITY_INQUIRY = "inquiry"
    AVAILABILITY_OUT_OF_STOCK = "out_of_stock"
    AVAILABILITY_CHOICES = [
        (AVAILABILITY_IN_STOCK, "In stock"),
        (AVAILABILITY_INQUIRY, "Price inquiry"),
        (AVAILABILITY_OUT_OF_STOCK, "Out of stock"),
    ]

    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=500,blank=True)
    short_description = models.CharField(max_length=500, default="")
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    availability_status = models.CharField(
        max_length=32,
        choices=AVAILABILITY_CHOICES,
        default=AVAILABILITY_IN_STOCK,
    )
    created_at = JalaliDateTimeField(auto_now_add=True)
    updated_at = JalaliDateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True) or "product"
            candidate = base_slug
            suffix = 2
            while Product.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductAuditLog(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    product_name = models.CharField(max_length=255)
    action = models.CharField(max_length=64)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"ProductAuditLog({self.product_id})-{self.action}"


# ----------- استاندارد -----------
class ProductStandard(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class ProductAttributeOption(models.Model):
    group = models.CharField(max_length=80)
    value = models.CharField(max_length=120)
    label = models.CharField(max_length=160)
    product_kind = models.CharField(max_length=50, blank=True, default="")
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, null=True, blank=True, related_name="attribute_options")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("group", "sort_order", "label")
        constraints = [
            models.UniqueConstraint(
                fields=["group", "value", "parent"],
                name="uniq_product_option_group_value_parent",
            )
        ]

    def __str__(self):
        return f"{self.group}: {self.label}"


# ----------- مشخصات فنی پایه (برای فولاد) -----------
class ProductSpecification(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='specifications')
    material_type = models.CharField(max_length=100, blank=True, default="")   # ورق، میلگرد، لوله
    steel_grade = models.CharField(max_length=50, blank=True, default="")      # St37, A36
    standard = models.ForeignKey(ProductStandard, on_delete=models.SET_NULL, null=True, blank=True)
    thickness_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    width_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    length_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    diameter_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    factory = models.CharField(max_length=120, blank=True, default="")
    cut_type = models.CharField(max_length=120, blank=True, default="")
    weight_kg_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    surface_finish = models.CharField(max_length=100, null=True, blank=True)
    manufacturing_process = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Specs for {self.product.name}"


# ----------- ویژگی‌های داینامیک (برای آینده) -----------
class SpecificationAttribute(models.Model):
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20, null=True, blank=True)  # مثلا mm, kg, mpa

    def __str__(self):
        return self.name


class SpecificationValue(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="dynamic_specs")
    attribute = models.ForeignKey(SpecificationAttribute, on_delete=models.CASCADE)
    value = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.product.name} - {self.attribute.name}: {self.value}"


# ----------- پیشنهاد فروش (Offer) -----------
class Offer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="offers")
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="offers")
    is_active = models.BooleanField(default=True)
    created_at = JalaliDateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - by {self.seller.company_name}"


# ----------- قیمت‌گذاری حجمی و توافقی -----------
class PricingTier(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='pricing_tiers')
    tier_name = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    minimum_quantity = models.IntegerField()
    maximum_quantity = models.IntegerField(null=True, blank=True)
    is_negotiable = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.offer.product.name} - {self.tier_name}"


# ----------- شرایط تحویل (Delivery / Incoterm) -----------
class DeliveryLocation(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='delivery_options')
    incoterm = models.CharField(max_length=10, choices=[("FOB", "FOB"), ("CIF", "CIF"), ("EXW", "EXW")])
    country = models.CharField(max_length=100)
    province = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    port = models.CharField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.incoterm} - {self.country}"


# ----------- تصاویر و اسناد -----------
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/images/')
    is_featured = models.BooleanField(default=False)

class ProductDocument(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='products/documents/')
