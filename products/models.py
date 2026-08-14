import datetime
import re

from django.db import models
from django.conf import settings
from mptt.models import MPTTModel, TreeForeignKey
from django.utils import timezone
from django.utils.html import strip_tags
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
    ICON_CHOICES = [
        ("layers", "Layers"),
        ("sheet", "Sheet"),
        ("rebar", "Rebar"),
        ("beam", "Beam"),
        ("pipe", "Pipe"),
        ("profile", "Profile"),
        ("billet", "Billet"),
        ("coil", "Coil"),
        ("ore", "Ore"),
        ("scrap", "Scrap"),
        ("recycle", "Recycle"),
        ("factory", "Factory"),
        ("cubes", "Cubes"),
        ("package", "Package"),
    ]

    name = models.CharField(max_length=255, unique=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    hscode = models.CharField(max_length=20, unique=True, null=True, blank=True)
    code = models.CharField(max_length=80, unique=True, null=True, blank=True)
    product_kind = models.CharField(max_length=50, blank=True, default="")
    spec_defaults = models.JSONField(default=dict, blank=True)
    required_spec_fields = models.JSONField(default=list, blank=True)
    icon_key = models.CharField(max_length=32, choices=ICON_CHOICES, blank=True, default="")
    icon_image = models.ImageField(upload_to="products/category-icons/", null=True, blank=True)
    show_in_navigation = models.BooleanField(default=True)
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
    SEO_INDEX_AUTO = "auto"
    SEO_INDEX_INDEX = "index"
    SEO_INDEX_NOINDEX = "noindex"
    SEO_INDEX_CHOICES = [
        (SEO_INDEX_AUTO, "Automatic"),
        (SEO_INDEX_INDEX, "Index"),
        (SEO_INDEX_NOINDEX, "No index"),
    ]

    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=500,blank=True)
    short_description = models.CharField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    seo_title = models.CharField(max_length=255, blank=True, default="")
    meta_description = models.CharField(max_length=320, blank=True, default="")
    page_h1 = models.CharField(max_length=255, blank=True, default="")
    seo_faqs = models.JSONField(default=list, blank=True)
    seo_index_mode = models.CharField(
        max_length=16,
        choices=SEO_INDEX_CHOICES,
        default=SEO_INDEX_AUTO,
    )
    related_products = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="related_by_products",
    )
    is_active = models.BooleanField(default=True)
    availability_status = models.CharField(
        max_length=32,
        choices=AVAILABILITY_CHOICES,
        default=AVAILABILITY_IN_STOCK,
    )
    purchase_terms = models.JSONField(default=list, blank=True)
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

    def is_search_indexable(self):
        """Resolve the effective index state used by feeds such as Sitemap."""
        if not self.is_active:
            return False
        if self.seo_index_mode == self.SEO_INDEX_INDEX:
            return True
        if self.seo_index_mode == self.SEO_INDEX_NOINDEX:
            return False

        try:
            specifications = self.specifications
        except ProductSpecification.DoesNotExist:
            specifications = None

        category = self.category
        family = ""
        if specifications and specifications.material_type:
            family = specifications.material_type
        elif category:
            family = category.product_kind or category.code or ""

        fact_values = [family]
        if specifications:
            fact_values.extend(
                [
                    specifications.steel_grade,
                    specifications.thickness_mm,
                    specifications.width_mm,
                    specifications.length_mm,
                    specifications.diameter_mm,
                    specifications.factory,
                    specifications.manufacturing_process,
                    specifications.surface_finish,
                ]
            )
        fact_count = sum(value is not None and str(value).strip() != "" for value in fact_values)

        description_html = self.description or ""
        description_text = re.sub(r"\s+", " ", strip_tags(description_html)).strip()
        comparisons = {
            re.sub(r"\s+", " ", strip_tags(value or "")).strip().casefold()
            for value in (self.name, self.short_description)
            if value
        }
        has_structured_content = bool(re.search(r"<(p|h2|h3|table|ul|ol)\b", description_html, re.I))
        has_substantive_content = has_structured_content or (
            len(description_text) >= 120 and description_text.casefold() not in comparisons
        )

        score = (2 if len((self.name or "").strip()) >= 8 else 0) + fact_count
        score += 3 if has_substantive_content else 0
        score += 1 if self.images.exists() else 0
        return score >= 6


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
    SALES_MODE_SHEET = "sheet"
    SALES_MODE_COIL_FULL = "coil_full"
    SALES_MODE_COIL_CUTTABLE = "coil_cuttable"
    SALES_MODE_COIL_MUST_CUT = "coil_must_cut"
    SALES_MODE_CHOICES = [
        (SALES_MODE_SHEET, "Sheet"),
        (SALES_MODE_COIL_FULL, "Full coil"),
        (SALES_MODE_COIL_CUTTABLE, "Cuttable coil"),
        (SALES_MODE_COIL_MUST_CUT, "Must-cut coil"),
    ]

    HEAD_TAIL_OPTIONAL = "optional"
    HEAD_TAIL_INCLUDED = "included"
    HEAD_TAIL_SURCHARGE_IF_EXCLUDED = "surcharge_if_excluded"
    HEAD_TAIL_POLICY_CHOICES = [
        (HEAD_TAIL_OPTIONAL, "Optional"),
        (HEAD_TAIL_INCLUDED, "Included"),
        (HEAD_TAIL_SURCHARGE_IF_EXCLUDED, "Surcharge if excluded"),
    ]

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
    sales_mode = models.CharField(max_length=32, choices=SALES_MODE_CHOICES, blank=True, default="")
    head_tail_policy = models.CharField(
        max_length=32,
        choices=HEAD_TAIL_POLICY_CHOICES,
        blank=True,
        default=HEAD_TAIL_OPTIONAL,
    )

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
class PricingBasis(models.TextChoices):
    TON = "ton", "Price per ton"
    KG = "kg", "Price per kilogram"
    SHEET = "sheet", "Price per sheet"


class PricingTier(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='pricing_tiers')
    tier_name = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    price_basis = models.CharField(
        max_length=20,
        choices=PricingBasis.choices,
        default=PricingBasis.KG,
        db_index=True,
    )
    minimum_quantity = models.IntegerField()
    maximum_quantity = models.IntegerField(null=True, blank=True)
    condition_label = models.CharField(max_length=160, blank=True, default="")
    dimension_width_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dimension_length_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_negotiable = models.BooleanField(default=False)
    price_verified_at = models.DateTimeField(null=True, blank=True, db_index=True)

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        price_changed = self._state.adding
        if not self._state.adding and update_fields is not None:
            price_changed = "unit_price" in update_fields
        elif not self._state.adding:
            previous_price = type(self).objects.filter(pk=self.pk).values_list("unit_price", flat=True).first()
            price_changed = previous_price != self.unit_price
        if price_changed:
            self.price_verified_at = timezone.now()
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"price_verified_at"}
        super().save(*args, **kwargs)

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

    class Meta:
        ordering = ('-is_featured', 'id')

class ProductDocument(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='products/documents/')
