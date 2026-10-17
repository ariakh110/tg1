from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from django.db.models import Prefetch
from django.utils import timezone

from .models import (
    Offer,
    PricingBasis,
    PricingTier,
    Product,
    ProductPriceSnapshot,
    ProductSpecification,
)


TEHRAN_TZ = ZoneInfo("Asia/Tehran")
ZERO = Decimal("0")
HUNDRED = Decimal("100")
THOUSAND = Decimal("1000")


def tehran_localdate(value=None):
    value = value or timezone.now()
    if timezone.is_naive(value):
        value = timezone.make_aware(value, TEHRAN_TZ)
    return value.astimezone(TEHRAN_TZ).date()


def decimal_or_none(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number > ZERO else None


def product_unit_weight(product):
    try:
        return decimal_or_none(product.specifications.weight_kg_per_unit)
    except ProductSpecification.DoesNotExist:
        return None


def normalize_price_per_kg(price, pricing_basis, weight_kg_per_unit=None):
    price = decimal_or_none(price)
    if price is None:
        return None
    if pricing_basis == PricingBasis.KG:
        return price
    if pricing_basis == PricingBasis.TON:
        return price / THOUSAND
    if pricing_basis == PricingBasis.SHEET:
        weight = decimal_or_none(weight_kg_per_unit)
        return price / weight if weight else None
    return None


def _active_tiers_for_product(product_id):
    return (
        PricingTier.objects.filter(
            offer__product_id=product_id,
            offer__product__is_active=True,
            offer__is_active=True,
            unit_price__gt=0,
        )
        .select_related("offer__product", "offer__product__specifications")
        .order_by("price_basis", "unit_price", "id")
    )


def capture_product_price_snapshots(product_id, observed_at=None):
    """Persist the current best price in every active basis for one product."""

    observed_at = observed_at or timezone.now()
    observed_on = tehran_localdate(observed_at)
    tiers = list(_active_tiers_for_product(product_id))
    if not tiers:
        return []

    product = tiers[0].offer.product
    weight = product_unit_weight(product)
    best_by_basis = {}
    for tier in tiers:
        current = best_by_basis.get(tier.price_basis)
        if current is None or tier.unit_price < current.unit_price:
            best_by_basis[tier.price_basis] = tier

    snapshots = []
    for basis, tier in best_by_basis.items():
        normalized = normalize_price_per_kg(tier.unit_price, basis, weight)
        snapshot, _created = ProductPriceSnapshot.objects.update_or_create(
            product_id=product_id,
            pricing_basis=basis,
            observed_on=observed_on,
            defaults={
                "price": tier.unit_price,
                "normalized_price_kg": normalized,
                "observed_at": observed_at,
                "source": "catalog",
            },
        )
        snapshots.append(snapshot)
    return snapshots


def _market_products_queryset():
    active_tiers = PricingTier.objects.filter(unit_price__gt=0).order_by("unit_price", "id")
    active_offers = Offer.objects.filter(is_active=True).prefetch_related(
        Prefetch("pricing_tiers", queryset=active_tiers)
    )
    return (
        Product.objects.filter(
            is_active=True,
            offers__is_active=True,
            offers__pricing_tiers__unit_price__gt=0,
        )
        .select_related("category", "specifications")
        .prefetch_related(Prefetch("offers", queryset=active_offers))
        .distinct()
        .order_by("category__name", "name", "id")
    )


def _previous_snapshot(product_id, pricing_basis, observed_on):
    return (
        ProductPriceSnapshot.objects.filter(
            product_id=product_id,
            pricing_basis=pricing_basis,
            observed_on__lt=observed_on,
        )
        .order_by("-observed_on", "-observed_at")
        .first()
    )


def _select_effective_tier(product):
    weight = product_unit_weight(product)
    candidates = []
    for offer in product.offers.all():
        for tier in offer.pricing_tiers.all():
            normalized = normalize_price_per_kg(tier.unit_price, tier.price_basis, weight)
            candidates.append((tier, normalized))
    if not candidates:
        return None, None
    comparable = [item for item in candidates if item[1] is not None]
    if comparable:
        return min(comparable, key=lambda item: (item[1], item[0].id))
    tier, normalized = min(candidates, key=lambda item: (item[0].unit_price, item[0].id))
    return tier, normalized


def build_market_rows(search=""):
    observed_on = tehran_localdate()
    needle = (search or "").strip().casefold()
    rows = []
    for product in _market_products_queryset():
        tier, normalized = _select_effective_tier(product)
        if tier is None:
            continue
        try:
            specification = product.specifications
        except ProductSpecification.DoesNotExist:
            specification = None
        category_name = product.category.name if product.category_id else "سایر"
        factory = (getattr(specification, "factory", "") or "").strip()
        grade = (getattr(specification, "steel_grade", "") or "").strip()
        haystack = " ".join((product.name, category_name, factory, grade)).casefold()
        if needle and needle not in haystack:
            continue

        previous = _previous_snapshot(product.id, tier.price_basis, observed_on)
        previous_normalized = previous.normalized_price_kg if previous else None
        absolute_change = None
        percent_change = None
        direction = "new"
        if normalized is not None and previous_normalized is not None and previous_normalized > ZERO:
            absolute_change = normalized - previous_normalized
            percent_change = (absolute_change / previous_normalized * HUNDRED).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            direction = "up" if absolute_change > ZERO else "down" if absolute_change < ZERO else "flat"

        # Tile area communicates the magnitude of a real recorded movement.
        # New/flat products stay at the minimum size; the cap keeps the map usable.
        tile_weight = 1
        if percent_change:
            tile_weight = min(4, max(1, int(abs(percent_change)) + 1))

        verified_at = tier.price_verified_at or timezone.now()
        rows.append(
            {
                "product_id": product.id,
                "name": product.name,
                "slug": product.slug,
                "category": category_name,
                "factory": factory,
                "grade": grade,
                "price": tier.unit_price,
                "pricing_basis": tier.price_basis,
                "normalized_price_kg": normalized,
                "previous_price_kg": previous_normalized,
                "absolute_change": absolute_change,
                "percent_change": percent_change,
                "direction": direction,
                "observed_at": verified_at,
                "comparable": normalized is not None,
                "comparison_note": "" if normalized is not None else "وزن واحد برای تبدیل قیمت این کالا ثبت نشده است.",
                "tile_weight": tile_weight,
            }
        )
    return rows


def build_market_summary(rows=None):
    rows = list(rows if rows is not None else build_market_rows())
    counts = {"up": 0, "down": 0, "flat": 0, "new": 0}
    for row in rows:
        counts[row["direction"]] = counts.get(row["direction"], 0) + 1

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    groups = []
    for name, items in grouped.items():
        changes = [item["percent_change"] for item in items if item["percent_change"] is not None]
        average = (sum(changes, ZERO) / len(changes)).quantize(Decimal("0.01")) if changes else None
        groups.append(
            {
                "name": name,
                "product_count": len(items),
                "average_change": average,
                "advances": sum(item["direction"] == "up" for item in items),
                "declines": sum(item["direction"] == "down" for item in items),
            }
        )
    groups.sort(key=lambda item: (-item["product_count"], item["name"]))

    movers = [row for row in rows if row["percent_change"] is not None]
    latest = max((row["observed_at"] for row in rows), default=None)
    is_stale = bool(latest and timezone.now() - latest > timedelta(hours=48))
    return {
        "total": len(rows),
        "advances": counts["up"],
        "declines": counts["down"],
        "unchanged": counts["flat"],
        "new": counts["new"],
        "comparable": sum(row["comparable"] for row in rows),
        "latest_observed_at": latest,
        "is_stale": is_stale,
        "groups": groups,
        "top_gainers": sorted(movers, key=lambda row: row["percent_change"], reverse=True)[:5],
        "top_losers": sorted(movers, key=lambda row: row["percent_change"])[:5],
        "tiles": sorted(rows, key=lambda row: (-row["tile_weight"], row["name"])),
        "external_market": {
            "available": False,
            "message": "منبع مورد تأیید برای قیمت جهانی هنوز تنظیم نشده است.",
        },
    }


def history_start_date(range_name):
    days = {"7d": 7, "30d": 30, "90d": 90}.get(range_name, 30)
    return tehran_localdate() - timedelta(days=days - 1), days
