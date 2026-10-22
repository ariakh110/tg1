"""Catalog-driven domestic market grouping; display labels never become filter identifiers."""
from collections import defaultdict
from decimal import Decimal

from .models import ProductAttributeOption, ProductCategory


KIND_LABELS = {
    "sheet": "ورق", "rebar": "میلگرد", "beam": "تیرآهن", "pipe": "لوله",
    "profile": "قوطی و پروفیل", "billet": "شمش", "coil": "رول", "ore": "سنگ آهن",
    "scrap": "ضایعات", "angle": "نبشی", "channel": "ناودانی",
}
FINISH_LABELS = {"black": "سیاه", "alloy": "آلیاژی", "oiled": "روغنی", "galvanized": "گالوانیزه", "color": "رنگی", "painted": "رنگی", "acid_washed": "اسیدشویی"}
MISSING = "__unspecified__"


class MarketTaxonomy:
    def __init__(self):
        self.categories = {item.id: item for item in ProductCategory.objects.all()}
        self.options = list(ProductAttributeOption.objects.filter(is_active=True).select_related("parent"))

    def describe(self, product, spec):
        chain, category = [], self.categories.get(product.category_id)
        while category and category not in chain:
            chain.append(category)
            category = self.categories.get(category.parent_id)
        defaults = {}
        for category in reversed(chain):
            defaults.update(category.spec_defaults or {})
        kind = next((item.product_kind for item in chain if item.product_kind), "")
        kind = kind or (getattr(spec, "material_type", "") or defaults.get("material_type") or "").strip()
        # Recognize Persian material values stored by older catalog imports.
        kind = next((code for code, label in KIND_LABELS.items() if label == kind), kind)
        kind = kind or (f"category:{chain[-1].id}" if chain else MISSING)
        kind_label = KIND_LABELS.get(kind) or (chain[-1].name if chain else "نوع محصول ثبت نشده")
        finish = (getattr(spec, "surface_finish", "") or defaults.get("surface_finish") or "").strip()
        factory = (getattr(spec, "factory", "") or defaults.get("factory") or "").strip()

        def label(group, value):
            candidates = [option for option in self.options if option.group == group and
                          option.value.casefold() == value.casefold() and
                          (not option.product_kind or option.product_kind == kind) and
                          (not option.category_id or option.category_id in [item.id for item in chain]) and
                          (not option.parent_id or option.parent.group != "surface_finish" or option.parent.value == finish)]
            candidates.sort(key=lambda option: (
                next((index for index, item in enumerate(chain) if item.id == option.category_id), len(chain)),
                not bool(option.product_kind), not bool(option.parent_id), option.sort_order, option.id,
            ))
            if candidates:
                return candidates[0].label
            return FINISH_LABELS.get(value, value) if group == "surface_finish" else value

        if finish:
            subtype, subtype_label = finish, label("surface_finish", finish)
            if kind == "sheet" and not subtype_label.startswith("ورق"):
                subtype_label = f"ورق {subtype_label}"
        else:
            # Custom children without a finish are still usable; do not infer from product names/grades.
            child = next((item for item in reversed(chain) if item.parent_id and item.product_kind in ("", kind)), None)
            subtype = f"category:{child.id}" if child else MISSING
            subtype_label = child.name if child else "نوع ثبت نشده"
        return {
            "product_kind": kind, "product_kind_label": kind_label,
            "subtype": subtype, "subtype_label": subtype_label,
            "factory": factory, "factory_label": label("factory", factory) if factory else "کارخانه ثبت نشده",
        }


def filter_market_scope(rows, scope):
    fields = {"kind": "product_kind", "subtype": "subtype", "factory": "factory", "product_id": "product_id"}
    for parameter, field in fields.items():
        value = scope.get(parameter, "")
        if value:
            value = "" if parameter == "factory" and value == MISSING else str(value)
            rows = [row for row in rows if str(row.get(field, "")) == value]
    return rows


def build_market_hierarchy(rows, depth=0, scope=None):
    scope = scope or {}
    levels = [("product_kind", "product_kind_label", "kind"), ("subtype", "subtype_label", "subtype"),
              ("factory", "factory_label", "factory")]
    if depth == len(levels):
        return [{"name": row["name"], "value": 1, "count": 1, "product_id": row["product_id"],
                 "scope": {**scope, "product_id": str(row["product_id"])},
                 "average_change": str(row["percent_change"]) if row["percent_change"] is not None else None,
                 "direction": row["direction"]} for row in rows]
    field, label_field, parameter = levels[depth]
    groups = defaultdict(list)
    for row in rows:
        groups[row[field]].append(row)
    nodes = []
    for key, items in groups.items():
        next_scope = {**scope, parameter: key or MISSING}
        changes = [row["percent_change"] for row in items if row["percent_change"] is not None]
        average = sum(changes, Decimal(0)) / len(changes) if changes else None
        nodes.append({"name": items[0][label_field], "value": len(items), "count": len(items),
                      "scope": next_scope, "average_change": str(average.quantize(Decimal("0.01"))) if average is not None else None,
                      "direction": ("up" if average > 0 else "down" if average < 0 else "flat") if average is not None else "new",
                      "children": build_market_hierarchy(items, depth + 1, next_scope)})
    return sorted(nodes, key=lambda node: (-node["count"], node["name"]))
