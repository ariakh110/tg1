"""Amount-only editing of existing sale tiers. Never call the catalog importer."""
import re
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import PricingTier, ProductAuditLog

DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def parse_amount(raw, *, expected=False):
    if raw is None or isinstance(raw, bool):
        raise ValidationError('قیمت معتبر وارد کنید؛ مبلغ خالی به معنی حذف نیست.')
    value = str(raw).strip().translate(DIGITS).replace('٫', '.')
    if ',' in value or '٬' in value:
        if not re.fullmatch(r'[0-9]{1,3}([,٬][0-9]{3})+(\.[0-9]{1,2})?', value):
            raise ValidationError('جداکننده‌های قیمت معتبر نیستند.')
        value = value.replace(',', '').replace('٬', '')
    if not re.fullmatch(r'[0-9]+(\.[0-9]{1,2})?', value):
        raise ValidationError('قیمت باید عدد با حداکثر دو رقم اعشار باشد.')
    amount = Decimal(value)
    if amount >= Decimal('10000000000') or amount < 0 or (amount == 0 and not expected):
        raise ValidationError('قیمت باید مثبت و در محدودهٔ مجاز باشد.')
    return amount


def _id(value):
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]{1,18}', str(value or '')) or int(value) < 1:
        raise ValidationError('شناسهٔ قیمت یا کالا معتبر نیست.')
    return int(value)


def price_row(tier):
    return {
        'tier_id': tier.pk, 'product_id': tier.offer.product_id,
        'product_name': tier.offer.product.name, 'slug': tier.offer.product.slug,
        'seller_name': tier.offer.seller.company_name, 'seller_id': tier.offer.seller_id,
        'tier_name': tier.tier_name, 'condition_label': tier.condition_label,
        'price_basis': tier.price_basis, 'unit_price': format(tier.unit_price, '.2f'),
        'minimum_quantity': tier.minimum_quantity, 'maximum_quantity': tier.maximum_quantity,
        'price_verified_at': tier.price_verified_at.isoformat() if tier.price_verified_at else None,
        'product_active': tier.offer.product.is_active, 'offer_active': tier.offer.is_active,
    }


def update_prices(items, actor):
    if not isinstance(items, list) or not 1 <= len(items) <= 500:
        raise ValidationError('بین ۱ تا ۵۰۰ ردیف قیمت ارسال کنید.')
    prepared = []
    for row in items:
        if not isinstance(row, dict) or set(row) - {'tier_id', 'product_id', 'price', 'expected_price'}:
            raise ValidationError('فقط شناسهٔ قیمت، مبلغ و مبلغ قبلی مجاز است؛ مشخصات کالا را اینجا نفرستید.')
        if ('tier_id' in row) == ('product_id' in row) or 'price' not in row:
            raise ValidationError('یک شناسهٔ دقیق قیمت و مبلغ لازم است.')
        prepared.append((row, parse_amount(row['price']),
                         parse_amount(row['expected_price'], expected=True) if 'expected_price' in row else None))
    with transaction.atomic():
        targets = []
        for row, amount, expected in prepared:
            if 'tier_id' in row:
                tier_id = _id(row['tier_id'])
            else:
                ids = list(PricingTier.objects.filter(offer__product_id=_id(row['product_id']))
                           .values_list('pk', flat=True)[:2])
                if len(ids) != 1:
                    raise ValidationError('کالا قیمت یکتای موجود ندارد؛ ردیف دقیق قیمت را انتخاب کنید.')
                tier_id = ids[0]
            targets.append((tier_id, amount, expected))
        ids = [t[0] for t in targets]
        if len(set(ids)) != len(ids):
            raise ValidationError('یک ردیف قیمت بیش از یک‌بار ارسال شده است.')
        # Lock the tier only; select_related locks on nullable unrelated relations
        # can be unsupported on PostgreSQL. No catalog or seller is written.
        locked = {tier.pk: tier for tier in PricingTier.objects.select_for_update()
                  .filter(pk__in=ids).order_by('pk')}
        if len(locked) != len(ids):
            raise ValidationError('یکی از ردیف‌های قیمت حذف شده یا موجود نیست؛ فهرست را تازه کنید.')
        for tier_id, amount, expected in targets:
            if expected is not None and locked[tier_id].unit_price != expected:
                raise ValidationError('قیمت در این فاصله تغییر کرده است؛ فهرست را تازه کنید.')
        results = []
        for tier_id, amount, expected in targets:
            tier = locked[tier_id]
            previous = tier.unit_price
            tier.unit_price = amount
            tier.save(update_fields=['unit_price'])
            ProductAuditLog.objects.create(product_id=tier.offer.product_id,
                product_name=tier.offer.product.name, action='PRODUCT_PRICE_UPDATED', actor_user=actor,
                payload={'tier_id': tier.pk, 'previous_price': str(previous), 'price': str(amount),
                         'price_basis': tier.price_basis, 'source': 'amount_only_bulk'})
            results.append({'tier_id': tier.pk, 'product_id': tier.offer.product_id, 'price': str(amount)})
        return {'total_rows': len(items), 'created_products': 0, 'updated_prices': len(results),
                'failed_rows': 0, 'errors': [], 'results': results}
