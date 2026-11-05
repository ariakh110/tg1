"""Create-only, pinned, offline catalog bootstrap. Not a generic fixture loader.

The durable batch receipt prevents replays from undoing admin edits/deletions.
Keep receipts when removing products. Preview does not execute any writes.
"""
import hashlib
import json
from decimal import Decimal
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q

from .content_sanitizer import sanitize_product_content_html
from .models import (
    Product, ProductCategory, ProductSpecification, ProductAttributeOption,
    SpecificationAttribute, SpecificationValue, ProductAuditLog,
)
from .serializers import ProductSpecificationSerializer

SEED_ID = 'farda-sections-2026-11-05-v1'
PACKAGE_SHA256 = 'e9d903b8fe338bee4d72767311e9e236daf73f949280449af9fb750f19affa57'
PACKAGE_PATH = Path(__file__).parent / 'data' / 'farda_sections_v1.json'
BATCH_ACTION = 'CATALOG_SEED_BATCH'
ITEM_ACTION = 'CATALOG_SEED_CREATED'
NOMINAL_NAME = 'سایز اسمی ناودانی'
IDENTITY_FIELDS = (
    'material_type', 'factory', 'steel_grade', 'standard_id', 'thickness_mm',
    'width_mm', 'height_mm', 'length_mm', 'length_type', 'diameter_mm',
    'cut_type', 'manufacturing_process', 'surface_finish',
)
DECIMAL_FIELDS = {'thickness_mm', 'width_mm', 'height_mm', 'length_mm', 'diameter_mm'}


class SeedError(ValueError):
    def __init__(self, message, report=None):
        super().__init__(message)
        self.report = report


def load_package(expected_sha256=None):
    if expected_sha256 is not None and expected_sha256 != PACKAGE_SHA256:
        raise SeedError('Requested SHA256 does not match the reviewed package.')
    try:
        raw = PACKAGE_PATH.read_bytes()
    except OSError as exc:
        raise SeedError('Pinned catalog package is unavailable.') from exc
    digest = hashlib.sha256(raw).hexdigest()
    if digest != PACKAGE_SHA256:
        raise SeedError('Catalog package SHA256 mismatch; refusing to import.')
    return json.loads(raw), digest


def _normal(field, value):
    if field in DECIMAL_FIELDS:
        return None if value in (None, '') else Decimal(str(value))
    if field == 'standard_id':
        return value
    return str(value or '').strip().casefold()


def _identity(category_code, specs, nominal):
    values = tuple(_normal(field, specs.get(field)) for field in IDENTITY_FIELDS)
    return (category_code, *values, nominal)


def _row_identity(row):
    specs = {**row['specifications'], 'standard_id': row['specifications']['standard']}
    nominal = tuple(sorted((v['name'], v['unit'] or '', v['value']) for v in row['dynamic_specs']))
    return _identity(row['category_code'], specs, nominal)


def _product_identity(product):
    try:
        spec = product.specifications
    except ProductSpecification.DoesNotExist:
        return None
    # Extra enrichment is not a reason to duplicate a product. Nominal size is
    # an identity component, but unrelated dynamic attributes and weight aren't.
    nominal = tuple(sorted((v.attribute.name, v.attribute.unit or '', v.value)
                           for v in product.dynamic_specs.all() if v.attribute.name == NOMINAL_NAME))
    return _identity(product.category.code if product.category else None,
                     {f: getattr(spec, f) for f in IDENTITY_FIELDS}, nominal)


def _receipt(digest):
    receipts = list(ProductAuditLog.objects.filter(action=BATCH_ACTION, payload__seed_id=SEED_ID))
    if len(receipts) > 1 or (receipts and receipts[0].payload.get('sha256') != digest):
        raise SeedError('Conflicting catalog batch receipts; manual review required.')
    return bool(receipts)


def _preflight(package, digest):
    report = dict(seed_id=SEED_ID, sha256=digest, valid=True, applied=False,
                  already_applied=False, new_count=0, created_count=0, skipped_count=0,
                  quarantined_count=len(package['quarantine']), conflicts=[], rows=[])
    if _receipt(digest):
        report['already_applied'] = True
        return report
    # An incomplete/missing batch receipt must never resurrect deleted items.
    if ProductAuditLog.objects.filter(action=ITEM_ACTION, payload__seed_id=SEED_ID).exists():
        raise SeedError('Item receipts exist without a batch receipt; manual review required.')

    def conflict(kind, key):
        report['conflicts'].append({'kind': kind, 'key': key})

    for item in package['categories']:
        matches = list(ProductCategory.objects.select_related('parent').filter(
            Q(code=item['code']) | Q(name=item['name'])))
        if matches:
            c = matches[0]
            compatible = len(matches) == 1 and all((
                c.code == item['code'], c.name == item['name'],
                (c.parent.code if c.parent else None) == item['parent_code'],
                c.product_kind == item['product_kind'],
                c.spec_defaults == item['spec_defaults'],
                c.required_spec_fields == item['required_spec_fields'],
            ))
            if not compatible:
                conflict('category', item['code'])
    for item in package['factory_options'] + package['grade_options']:
        matches = list(ProductAttributeOption.objects.filter(
            group=item['group'], value=item['value'], product_kind=item['product_kind'],
            parent__isnull=True))
        if matches and (len(matches) != 1 or any((
            matches[0].label != item['label'], matches[0].product_kind != item['product_kind'],
            matches[0].category_id is not None, not matches[0].is_active,
        ))):
            conflict('option', f"{item['group']}:{item['value']}")
    attrs = list(SpecificationAttribute.objects.filter(name=NOMINAL_NAME))
    if len(attrs) > 1 or (attrs and attrs[0].unit not in ('', None)):
        conflict('nominal_attribute', NOMINAL_NAME)

    products = list(Product.objects.select_related('category', 'specifications')
                    .prefetch_related('dynamic_specs__attribute').filter(
                        Q(category__code__in=[c['code'] for c in package['categories']]) |
                        Q(slug__in=[r['product']['slug'] for r in package['products']])))
    by_identity, by_slug = {}, {}
    for product in products:
        nominal_values = [v for v in product.dynamic_specs.all() if v.attribute.name == NOMINAL_NAME]
        if len(nominal_values) > 1 or any(v.attribute.unit not in ('', None) for v in nominal_values):
            conflict('ambiguous_product_nominal_size', str(product.pk))
        by_identity.setdefault(_product_identity(product), []).append(product)
        by_slug[product.slug] = product
    seen = set()
    for row in package['products']:
        key = _row_identity(row)
        if key in seen:
            conflict('duplicate_package_identity', row['key'])
        seen.add(key)
        matches = by_identity.get(key, [])
        slug_match = by_slug.get(row['product']['slug'])
        if len(matches) > 1 or (slug_match and (not matches or slug_match.pk != matches[0].pk)):
            conflict('product_identity_or_slug', row['key'])
            status = 'conflict'
        elif matches:
            report['skipped_count'] += 1
            status = 'existing'
        else:
            report['new_count'] += 1
            status = 'new'
        # Field-level model validation is read-only. The saved category-aware
        # serializer is also checked on apply, within the atomic transaction.
        try:
            Product(**row['product']).full_clean(exclude=['category'], validate_unique=False,
                                                validate_constraints=False)
            ProductSpecification(**row['specifications']).full_clean(
                exclude=['product'], validate_unique=False, validate_constraints=False)
        except ValidationError as exc:
            conflict('invalid_fields', row['key'])
            report.setdefault('validation_errors', {})[row['key']] = exc.message_dict
        report['rows'].append({'key': row['key'], 'status': status,
                               'existing_id': matches[0].pk if len(matches) == 1 else None})
    report['valid'] = not report['conflicts']
    if not report['valid']:
        detail = report.get('validation_errors') or report['conflicts'][:3]
        raise SeedError(f'Catalog conflicts; no data was changed: {detail}', report)
    return report


def _create(package, report, actor):
    categories = {}
    for item in package['categories']:
        category = ProductCategory.objects.filter(code=item['code']).first()
        if category is None:
            data = {k: v for k, v in item.items() if k != 'parent_code'}
            category = ProductCategory.objects.create(**data, parent=categories.get(item['parent_code']))
        categories[item['code']] = category
    for item in package['factory_options'] + package['grade_options']:
        if not ProductAttributeOption.objects.filter(
            group=item['group'], value=item['value'], product_kind=item['product_kind'],
            parent__isnull=True).exists():
            ProductAttributeOption.objects.create(**item)
    attribute = SpecificationAttribute.objects.filter(name=NOMINAL_NAME).first()
    if attribute is None:
        attribute = SpecificationAttribute.objects.create(name=NOMINAL_NAME, unit='')
    for row, decision in zip(package['products'], report['rows'], strict=True):
        if decision['status'] != 'new':
            continue
        data = {**row['product'], 'is_active': False, 'seo_index_mode': 'noindex',
                'availability_status': 'inquiry'}
        data['description'] = sanitize_product_content_html(data['description'])
        product = Product.objects.create(**data, category=categories[row['category_code']])
        serializer = ProductSpecificationSerializer(data={'product': product.pk, **row['specifications']})
        if not serializer.is_valid():
            raise SeedError(f"Invalid native specifications for {row['key']}: {serializer.errors}")
        serializer.save()
        for value in row['dynamic_specs']:
            SpecificationValue.objects.create(product=product, attribute=attribute, value=value['value'])
        ProductAuditLog.objects.create(product=product, product_name=product.name,
            action=ITEM_ACTION, payload={'seed_id': SEED_ID, 'sha256': report['sha256'],
                'key': row['key'], 'actor': actor, 'source_observations': row['source_observations'],
                'review_flags': row['review_flags']})
        report['created_count'] += 1
    report['applied'] = True
    ProductAuditLog.objects.create(product_name=SEED_ID, action=BATCH_ACTION,
        payload={'seed_id': SEED_ID, 'sha256': report['sha256'], 'actor': actor,
                 'created_count': report['created_count'], 'skipped_count': report['skipped_count']})
    return report


def seed_sections(apply=False, actor='', expected_sha256=None):
    package, digest = load_package(expected_sha256)
    actor = str(actor or '').strip()
    if apply and (not actor or len(actor) > 120):
        raise SeedError('Explicit --apply requires an actor label of 1–120 characters.')
    if not apply:
        return _preflight(package, digest)
    try:
        with transaction.atomic():
            # Existing taxonomy rows serialize repeats on databases with row
            # locks. Concurrent empty-database runs race on unique category
            # codes; the loser rolls back completely and can safely retry.
            list(ProductCategory.objects.select_for_update().filter(
                code__in=[c['code'] for c in package['categories']]).order_by('pk'))
            report = _preflight(package, digest)
            return report if report['already_applied'] else _create(package, report, actor)
    except IntegrityError as exc:
        raise SeedError('Concurrent catalog change or database constraint; import rolled back. Retry preview.') from exc
