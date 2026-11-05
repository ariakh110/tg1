"""Compile an offline, review-only seed candidate. No database/network writes."""
from collections import Counter
from decimal import Decimal
from html import escape
import json
from pathlib import Path
import re
import sys

BRANDS = {
    "فولاد ناب تبریز": "naab-tabriz", "شکفته": "shekofteh",
    "آریان فولاد": "arian-foolad", "آونگان نوید مرکزی": "avangan-navid-markazi",
    "مشهد": "mashhad", "اصفهان": "isfahan", "تهران": "tehran",
    "فولاد تهران": "foolad-tehran", "دهشیر": "dehshir", "ماهان": "mahan",
    "صبا استیل": "saba-steel", "صدرا سازه": "sadra-sazeh", "فولاد نصر": "foolad-nasr",
    "فایکو": "faico", "انبار تهران": "unknown", "": "unknown",
}
CATEGORIES = [
    ("angle", "نبشی", None, "angle", []),
    ("angle-construction", "نبشی ساختمانی", "angle", "angle", ["width_mm", "height_mm", "thickness_mm", "length_mm"]),
    ("angle-st52", "نبشی ST52", "angle", "angle", ["width_mm", "height_mm", "thickness_mm", "length_mm", "steel_grade"]),
    ("angle-5sp", "نبشی 5SP", "angle", "angle", ["width_mm", "height_mm", "thickness_mm", "length_mm", "steel_grade"]),
    ("channel", "ناودانی", None, "channel", []),
    ("channel-construction", "ناودانی ساختمانی", "channel", "channel", ["length_mm"]),
    ("channel-europe", "ناودانی گروه اروپا", "channel", "channel", ["length_mm"]),
    ("channel-europe-equivalent", "ناودانی هم‌وزن اروپا", "channel", "channel", ["length_mm"]),
]


def number(value):
    text = str(value).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    if re.fullmatch(r"\d+/\d", text):
        text = text.replace("/", ".")
    if not re.fullmatch(r"\d+(?:\.\d+)?", text) or Decimal(text) <= 0:
        raise ValueError("Unknown positive decimal notation: " + text)
    return format(Decimal(text).normalize(), "f")


def group(heading):
    if heading == "نبشی ST52":
        return "angle", "angle-st52", "نبشی ST52"
    if heading == "نبشی 5SP":
        return "angle", "angle-5sp", "نبشی 5SP"
    if heading.startswith("نبشی ساختمانی"):
        return "angle", "angle-construction", "نبشی ساختمانی"
    if heading.startswith("ناودانی هم‌وزن اروپا"):
        return "channel", "channel-europe-equivalent", "ناودانی هم‌وزن اروپا"
    if heading.startswith("ناودانی اروپا"):
        return "channel", "channel-europe", "ناودانی گروه اروپا"
    if heading.startswith("ناودانی ساختمانی"):
        return "channel", "channel-construction", "ناودانی ساختمانی"
    raise ValueError("Out-of-scope/unknown table: " + heading)


def prepare(snapshot):
    candidates, rejected, factories = {}, {}, {}
    for page in snapshot["pages"]:
        for table in page["tables"]:
            family, category, label = group(table["heading"])
            for index, row in enumerate(table["rows"], 1):
                brand = row.get("برند", "")
                brand_code = BRANDS[brand]  # Unrecognized manufacturers fail closed.
                grade = row.get("استاندارد", "")
                if grade not in ("", "ST52", "5SP"):
                    raise ValueError("Unknown grade/standard requires review: " + grade)
                sizes = [number(part) for part in row["سایز"].split("*")]
                if len(sizes) != (2 if family == "angle" else 1):
                    raise ValueError("Unexpected size notation")
                thickness = number(row["ضخامت"]) if family == "angle" else None
                length_match = re.fullmatch(r"(\d+) متری", row["حالت"])
                length_m = length_match.group(1) if length_match else None
                key = "-".join([category, brand_code, "x".join(sizes), thickness or "na", length_m or "invalid-length"])
                observation = {"url": page["url"], "table": table["heading"], "row": index, "raw": row}
                issues = []
                if row["واحد"] != "کیلوگرم":
                    issues.append("source_unit_invalid")
                if length_m not in ("6", "12"):
                    issues.append("source_length_invalid")
                if issues:
                    entry = rejected.setdefault(key, {"key": key, "issues": issues, "source_observations": []})
                    entry["source_observations"].append(observation)
                    continue
                if key in candidates:
                    candidates[key]["source_observations"].append(observation)
                    continue
                factory = "" if brand_code == "unknown" else family + "-" + brand_code
                if factory:
                    factories[factory] = {"group": "factory", "product_kind": family, "value": factory, "label": brand}
                size_text = "×".join(sizes)
                name = f"{label} سایز {size_text}"
                if thickness:
                    name += f" ضخامت {thickness} میلی‌متر"
                if factory:
                    name += " " + brand
                name += f" طول {length_m} متر"
                facts = [("گروه",label),("سایز درج‌شده در فهرست",size_text),
                         ("طول شاخه",length_m+" متر"),("ضخامت",(thickness+" میلی‌متر") if thickness else "اعلام نشده"),
                         ("سازنده",brand if factory else "تأیید نشده"),
                         ("گرید درج‌شده",grade or "اعلام نشده"),
                         ("استاندارد فنی / وزن", "در فهرست منبع اعلام نشده؛ نیازمند تأیید")]
                description = "<h2>مشخصات ثبت‌شده</h2><table>" + "".join(
                    "<tr><th>"+escape(k)+"</th><td>"+escape(v)+"</td></tr>" for k,v in facts) + "</table>"
                description += "<h2>پیش از سفارش</h2><p>قیمت، موجودی، وزن، استاندارد و محل تحویل این کالا باید پیش از خرید با پیش‌فاکتور و مدارک سازنده تأیید شود. درج کالا به معنی موجودی قطعی یا تأیید اصالت نیست.</p>"
                short = f"مشخصات {name}؛ برای بررسی موجودی، وزن و شرایط تحویل استعلام بگیرید. قیمت فروش تأییدشده‌ای برای این ردیف ثبت نشده است."
                slug = "km-" + key.replace(".", "p")
                candidates[key] = {
                    "key": key, "category_code": category,
                    "product": {"name": name, "slug": slug, "short_description": short,
                        "description": description, "page_h1": name, "seo_title": name+" | استعلام خرید",
                        "meta_description": f"بررسی {name}؛ استعلام موجودی و شرایط خرید و تحویل. وزن، گرید و استاندارد پیش از سفارش باید تأیید شوند.",
                        "seo_index_mode": "noindex", "is_active": False, "availability_status": "inquiry",
                        "seo_faqs": [{"question": "آیا این کالا قیمت و موجودی قطعی دارد؟", "answer": "خیر؛ این ردیف برای معرفی مشخصات است. قیمت و موجودی باید پیش از سفارش استعلام و تأیید شوند."},
                                     {"question": "چه مشخصاتی باید پیش از خرید تأیید شود؟", "answer": "نام سازنده، اندازه‌ها، ضخامت، طول، وزن، گرید، استاندارد و محل تحویل را با پیش‌فاکتور و مدارک محصول تطبیق دهید."}]},
                    "specifications": {"material_type": family, "factory": factory, "length_mm": str(int(length_m)*1000),
                        "length_type": "fixed", "width_mm": sizes[0] if family == "angle" else None,
                        "height_mm": sizes[1] if family == "angle" else None, "thickness_mm": thickness,
                        "diameter_mm": None, "weight_kg_per_unit": None, "steel_grade": grade,
                        "manufacturing_process": "", "surface_finish": "", "cut_type": "", "standard": None},
                    "dynamic_specs": [{"name":"سایز اسمی ناودانی", "unit":"", "value":sizes[0]}] if family == "channel" else [],
                    "canonical_path": "/products/"+slug,
                    "review_flags": ["angle_leg_units_assumed_mm"] if family == "angle" else ["nominal_size_not_converted_to_height"],
                    "source_observations": [observation],
                }
                if not factory:
                    candidates[key]["review_flags"].append("manufacturer_not_identified_by_source")
    products = sorted(candidates.values(), key=lambda p:p["key"])
    return {"schema_version":1, "status":"review_candidate_not_django_fixture", "collected_on":snapshot["collected_on"],
        "policies":{"create_only":True,"network_during_deploy":False,"copy_prices":False,"copy_images":False,"automatic_publication":False},
        "categories":[{"code":c,"name":n,"parent_code":p,"product_kind":k,"spec_defaults":{"material_type":k,**({"steel_grade":c.split("-")[-1].upper()} if c in ("angle-st52","angle-5sp") else {})},"required_spec_fields":r,"icon_key":"profile","is_active":False} for c,n,p,k,r in CATEGORIES],
        "factory_options":sorted(factories.values(),key=lambda f:f["value"]), "products":products,
        "grade_options":[{"group":"steel_grade","product_kind":"angle","value":v,"label":v} for v in ("ST52","5SP")],
        "quarantine": sorted(rejected.values(),key=lambda p:p["key"]),
        "empty_source_pages":[p["url"] for p in snapshot["pages"] if not p["tables"]],
        "summary":{"products":len(products),"by_category":dict(Counter(p["category_code"] for p in products)),"quarantined_combinations":len(rejected)}}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    source = Path(__file__).with_name("source-catalog.json")
    print(json.dumps(prepare(json.loads(source.read_text(encoding="utf-8"))), ensure_ascii=False))
