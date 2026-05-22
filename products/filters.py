from django_filters import rest_framework as filters
from .models import Product, ProductCategory, ProductAttributeOption, Offer

class ProductFilter(filters.FilterSet):
    category = filters.NumberFilter(method='filter_category_tree')
    category_code = filters.CharFilter(method='filter_category_code')
    product_kind = filters.CharFilter(method='filter_product_kind')
    # allow filtering by category name (case-insensitive)
    category_name = filters.CharFilter(field_name='category__name', lookup_expr='iexact')
    is_active = filters.BooleanFilter(field_name='is_active')

    # filters on specifications (related one-to-one)
    steel_grade = filters.CharFilter(field_name='specifications__steel_grade', lookup_expr='iexact')
    material_type = filters.CharFilter(field_name='specifications__material_type', lookup_expr='iexact')
    surface_finish = filters.CharFilter(field_name='specifications__surface_finish', lookup_expr='iexact')
    manufacturing_process = filters.CharFilter(field_name='specifications__manufacturing_process', lookup_expr='iexact')
    factory = filters.CharFilter(field_name='specifications__factory', lookup_expr='iexact')
    cut_type = filters.CharFilter(field_name='specifications__cut_type', lookup_expr='iexact')
    availability_status = filters.CharFilter(field_name='availability_status', lookup_expr='iexact')
    min_thickness = filters.NumberFilter(field_name='specifications__thickness_mm', lookup_expr='gte')
    max_thickness = filters.NumberFilter(field_name='specifications__thickness_mm', lookup_expr='lte')
    min_width = filters.NumberFilter(field_name='specifications__width_mm', lookup_expr='gte')
    max_width = filters.NumberFilter(field_name='specifications__width_mm', lookup_expr='lte')
    min_length = filters.NumberFilter(field_name='specifications__length_mm', lookup_expr='gte')
    max_length = filters.NumberFilter(field_name='specifications__length_mm', lookup_expr='lte')
    diameter = filters.NumberFilter(field_name='specifications__diameter_mm', lookup_expr='exact')
    origin_province = filters.CharFilter(field_name='offers__delivery_options__province', lookup_expr='iexact')
    origin_city = filters.CharFilter(field_name='offers__delivery_options__city', lookup_expr='iexact')

    def filter_category_tree(self, queryset, name, value):
        try:
            category = ProductCategory.objects.get(pk=value)
        except ProductCategory.DoesNotExist:
            return queryset.none()
        categories = list(category.get_descendants(include_self=True))
        categories.extend(category.get_ancestors())
        return queryset.filter(category__in=categories)

    def filter_category_code(self, queryset, name, value):
        try:
            category = ProductCategory.objects.get(code=value)
        except ProductCategory.DoesNotExist:
            return queryset.none()
        categories = list(category.get_descendants(include_self=True))
        categories.extend(category.get_ancestors())
        return queryset.filter(category__in=categories)

    def filter_product_kind(self, queryset, name, value):
        category_ids = [
            category.id
            for category in ProductCategory.objects.filter(is_active=True)
            if category.resolved_product_kind() == value
        ]
        if not category_ids:
            return queryset.none()
        return queryset.filter(category_id__in=category_ids)

    class Meta:
        model = Product
        fields = [
            'category',
            'category_code',
            'category_name',
            'product_kind',
            'is_active',
            'steel_grade',
            'material_type',
            'surface_finish',
            'manufacturing_process',
            'factory',
            'cut_type',
            'availability_status',
            'min_thickness',
            'max_thickness',
            'min_width',
            'max_width',
            'min_length',
            'max_length',
            'diameter',
            'origin_province',
            'origin_city',
        ]


class ProductAttributeOptionFilter(filters.FilterSet):
    group = filters.CharFilter(field_name="group", lookup_expr="iexact")
    product_kind = filters.CharFilter(field_name="product_kind", lookup_expr="iexact")
    category = filters.NumberFilter(field_name="category", lookup_expr="exact")
    parent = filters.NumberFilter(field_name="parent", lookup_expr="exact")
    is_active = filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = ProductAttributeOption
        fields = ["group", "product_kind", "category", "parent", "is_active"]


class OfferFilter(filters.FilterSet):
    product = filters.NumberFilter(field_name='product', lookup_expr='exact')
    seller = filters.NumberFilter(field_name='seller', lookup_expr='exact')
    is_active = filters.BooleanFilter(field_name='is_active')

    # price-range (checks pricing_tiers related field; matches offers that have at least one tier in range)
    min_price = filters.NumberFilter(field_name='pricing_tiers__unit_price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='pricing_tiers__unit_price', lookup_expr='lte')

    class Meta:
        model = Offer
        fields = ['product', 'seller', 'is_active', 'min_price', 'max_price']
