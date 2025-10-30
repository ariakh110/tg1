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

    class MPTTMeta:
        order_insertion_by = ['name']

    def __str__(self):
        return self.name


# ----------- محصول (تعریف کلی) -----------
class Product(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=500,blank=True)
    short_description = models.CharField(max_length=500, default="")
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = JalaliDateTimeField(auto_now_add=True)
    updated_at = JalaliDateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ----------- استاندارد -----------
class ProductStandard(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


# ----------- مشخصات فنی پایه (برای فولاد) -----------
class ProductSpecification(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='specifications')
    material_type = models.CharField(max_length=100)   # ورق، میلگرد، لوله
    steel_grade = models.CharField(max_length=50)      # St37, A36
    standard = models.ForeignKey(ProductStandard, on_delete=models.SET_NULL, null=True, blank=True)
    thickness_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    width_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    length_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
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
    city = models.CharField(max_length=100, null=True, blank=True)
    port = models.CharField(max_length=100, null=True, blank=True)

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
