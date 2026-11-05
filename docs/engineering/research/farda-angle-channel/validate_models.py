"""Check candidate field names/types against installed Django models, without SQL."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tg1.settings_test")
import django
django.setup()
from products.models import Product, ProductCategory, ProductSpecification, ProductAttributeOption


def validate(model, values):
    for name, value in values.items():
        field = model._meta.get_field(name)
        if field.is_relation:
            if value is not None:
                raise ValueError("A database-independent candidate cannot contain foreign IDs")
        else:
            field.clean(value, None)


if __name__ == "__main__":
    data = json.loads(Path(__file__).with_name("seed-candidate.json").read_text(encoding="utf-8"))
    for row in data["products"]:
        validate(Product, row["product"])
        validate(ProductSpecification, row["specifications"])
    for category in data["categories"]:
        validate(ProductCategory, {k:v for k,v in category.items() if k != "parent_code"})
    for option in data["factory_options"] + data["grade_options"]:
        validate(ProductAttributeOption, option)
    print(json.dumps({"status":"pass","candidate_products":len(data["products"]),"categories":len(data["categories"]),
                      "controlled_options":len(data["factory_options"])+len(data["grade_options"]),
                      "scope":"Model field names, value types, choices and lengths only; no database writes, relation lookup or seed-import execution"}))
