# products/management/commands/seed_products.py
"""
Management command to seed the database with sample data for products marketplace.

Features:
- Idempotent creation (safe to run multiple times).
- Handles existing ProductCategory rows by looking up 'hscode' first to avoid unique constraint errors.
- --clean option to remove previously created sample data (sellers created by this script, products with names containing '#', standards created by script, categories with sample hscodes).
- --count option to specify how many products to create (default 30).
- Uses transactions where appropriate.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
from django.utils.text import slugify
from django.utils import timezone
import random

from products.models import (
    Seller, ProductCategory, Product, ProductSpecification,
    ProductStandard, PricingTier, Offer, DeliveryLocation
)

User = get_user_model()


# ----- helper functions -----
def get_or_create_category(name, parent=None, hscode=None):
    """
    Try to find category by hscode first (if provided). If found, optionally update name/parent.
    Otherwise fallback to get_or_create by (name, parent) and set hscode if creating.
    Returns (category, created_bool).
    """
    if hscode:
        cat = ProductCategory.objects.filter(hscode=hscode).first()
        if cat:
            updated = False
            if cat.name != name:
                cat.name = name
                updated = True
            # parent may be a model instance or None
            if parent and cat.parent_id != parent.id:
                cat.parent = parent
                updated = True
            if updated:
                cat.save()
            return cat, False

    defaults = {}
    if hscode:
        defaults["hscode"] = hscode

    try:
        cat, created = ProductCategory.objects.get_or_create(name=name, parent=parent, defaults=defaults)
    except Exception:
        # fallback: try to return any category with this hscode if available
        if hscode:
            cat = ProductCategory.objects.filter(hscode=hscode).first()
            if cat:
                return cat, False
        # re-raise if truly cannot create
        raise
    return cat, created


def create_or_update_spec(product, spec_data):
    """
    Create or update ProductSpecification for given product.
    """
    ProductSpecification.objects.update_or_create(product=product, defaults=spec_data)


# ----- management command -----
class Command(BaseCommand):
    help = "Seed the database with sample categories, sellers, products, offers, pricing tiers and delivery locations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=30,
            help="Number of products to create (default: 30)."
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="If set, remove previously created sample data (sellers created by this script, products with '#', sample categories/standards)."
        )

    def handle(self, *args, **options):
        count = options.get("count", 30)
        do_clean = options.get("clean", False)

        try:
            if do_clean:
                self.stdout.write(self.style.WARNING("Cleaning previously generated sample data..."))
                self._clean_sample_data()
                self.stdout.write(self.style.SUCCESS("Clean complete."))

            self.stdout.write(self.style.NOTICE(f"Starting seeding sample data (products={count})..."))

            with transaction.atomic():
                # --- Sellers (create 3) ---
                sellers = []
                seller_data = [
                    {"username": "seller_kaveh", "company_name": "Kaveh Metal"},
                    {"username": "seller_mobarakeh", "company_name": "Mobarakeh Steel"},
                    {"username": "seller_persia", "company_name": "Persia Steel Trading"},
                ]
                for s in seller_data:
                    user, created = User.objects.get_or_create(
                        username=s["username"],
                        defaults={"email": f"{s['username']}@example.com"}
                    )
                    if created:
                        user.set_password("sellerpass")
                        user.save()
                        self.stdout.write(self.style.SUCCESS(f"Created user {user.username}"))
                    seller, _ = Seller.objects.get_or_create(
                        user=user,
                        defaults={
                            "company_name": s["company_name"],
                            "business_type": "Supplier",
                            "location": random.choice(["Tehran", "Isfahan", "Tabriz"]),
                            "is_verified": True
                        }
                    )
                    sellers.append(seller)

                # --- Categories (hierarchy) ---
                # Use helper to avoid unique hscode conflicts
                metals, _ = get_or_create_category(name="Metals & Alloys", parent=None, hscode="7200")
                steel, _ = get_or_create_category(name="Steel", parent=metals, hscode="7201")
                carbon, _ = get_or_create_category(name="Carbon Steel", parent=steel, hscode="7202")
                stainless, _ = get_or_create_category(name="Stainless Steel", parent=steel, hscode="7203")
                pipe_cat, _ = get_or_create_category(name="Pipes & Tubes", parent=steel, hscode="7306")
                beam_cat, _ = get_or_create_category(name="Beams & Profiles", parent=steel, hscode="7208")

                categories = [carbon, stainless, pipe_cat, beam_cat]

                # --- Standards ---
                std_names = [
                    ("DIN", "Germany Standard"),
                    ("ASTM", "American Standard"),
                    ("EN", "European Norm"),
                ]
                standards = []
                for code, desc in std_names:
                    st, _ = ProductStandard.objects.get_or_create(name=code, defaults={"description": desc})
                    standards.append(st)

                # --- Steel grades & types for variety ---
                steel_grades = ["ST37", "ST52", "A36", "S235", "S355"]
                material_types = ["sheet", "rebar", "beam", "pipe", "coil"]

                # --- Generate products ---
                created_products = []
                for i in range(1, count + 1):
                    mat = random.choice(material_types)
                    grade = random.choice(steel_grades)
                    cat = random.choice(categories)
                    name = f"{grade} {mat.capitalize()} #{i}"
                    slug = slugify(name)
                    short_desc = f"{mat.capitalize()} {grade} suitable for structural applications. Sample #{i}"
                    description = f"{name} - Detailed spec and use cases. Produced for demo data. Generated at {timezone.now()}."

                    product, created = Product.objects.get_or_create(
                        name=name,
                        defaults={
                            "category": cat,
                            "slug": slug,
                            "short_description": short_desc,
                            "description": description,
                            "is_active": True
                        }
                    )
                    if not created:
                        # update some fields to reflect seed run if existed
                        changed = False
                        if product.category_id != cat.id:
                            product.category = cat
                            changed = True
                        if not product.slug:
                            product.slug = slug
                            changed = True
                        if changed:
                            product.save()

                    # Specification (OneToOne)
                    spec_defaults = {
                        "material_type": mat,
                        "steel_grade": grade,
                        "standard": random.choice(standards),
                        "thickness_mm": Decimal(str(round(random.uniform(2.0, 50.0), 2))),
                        "width_mm": Decimal(str(round(random.uniform(10.0, 2000.0), 2))),
                        "length_mm": Decimal(str(round(random.uniform(100.0, 12000.0), 2))),
                        "weight_kg_per_unit": Decimal(str(round(random.uniform(5.0, 2000.0), 2))),
                        "surface_finish": random.choice(["black", "galvanized", "painted"]),
                        "manufacturing_process": random.choice(["hot rolled", "cold rolled", "welded", "seamless"])
                    }
                    create_or_update_spec(product, spec_defaults)
                    created_products.append(product)

                self.stdout.write(self.style.SUCCESS(f"Created/updated {len(created_products)} products."))

                # --- For each product create offers, tiers, delivery locations ---
                incoterms = ["FOB", "CIF", "EXW", "DDP"]
                for p in created_products:
                    # create 1-2 offers
                    offer_count = random.choice([1, 1, 2])
                    for _ in range(offer_count):
                        seller = random.choice(sellers)
                        offer, offer_created = Offer.objects.get_or_create(
                            product=p,
                            seller=seller,
                            defaults={"is_active": True}
                        )
                        if offer_created:
                            self.stdout.write(self.style.SUCCESS(f"  Offer created for product {p.name} by {seller.company_name}"))

                        # create pricing tiers
                        base_price = Decimal(str(random.randint(400, 900)))
                        ranges = [(1, 50), (51, 200), (201, None)]
                        for idx, r in enumerate(ranges):
                            # decide whether to create this tier
                            if random.random() < 0.8 or idx == 0:
                                min_q = r[0]
                                max_q = r[1]
                                unit_price = base_price - Decimal(str(idx * random.randint(5, 30)))
                                if unit_price < Decimal("10.00"):
                                    unit_price = Decimal("10.00")
                                # ensure we don't duplicate identical tier entry
                                pt, pt_created = PricingTier.objects.get_or_create(
                                    offer=offer,
                                    tier_name=f"Tier {idx+1}",
                                    defaults={
                                        "unit_price": unit_price,
                                        "minimum_quantity": min_q,
                                        "maximum_quantity": max_q if max_q else None,
                                        "is_negotiable": False
                                    }
                                )
                                if pt_created:
                                    pass  # optionally log

                        # create delivery locations
                        dl_count = random.choice([1, 1, 2])
                        for __ in range(dl_count):
                            inc = random.choice(incoterms)
                            country = random.choice(["Iran", "Turkey", "China", "UAE", "Iraq"])
                            city = random.choice(["Tehran", "Bandar Abbas", "Shanghai", "Dubai", "Basra"])
                            port = f"{city} Port"
                            DeliveryLocation.objects.get_or_create(
                                offer=offer,
                                incoterm=inc,
                                country=country,
                                city=city,
                                port=port
                            )

                self.stdout.write(self.style.SUCCESS("Offers, PricingTiers and DeliveryLocations created or updated."))

            self.stdout.write(self.style.SUCCESS("Seeding completed successfully."))

        except Exception as exc:
            raise CommandError(f"Seeding failed: {exc}")

    # ----- cleaning helper -----
    def _clean_sample_data(self):
        """
        Remove sample data created by this script:
        - users with usernames used by this script
        - sellers linked to those users
        - products whose name contains the pattern '#' used by this script
        - offers/pricing/delivery related to those products
        - product standards created by script (DIN/ASTM/EN)
        - categories with sample hscodes used in this script
        """
        # sellers/users
        usernames = ["seller_kaveh", "seller_mobarakeh", "seller_persia"]
        users = User.objects.filter(username__in=usernames)
        # remove sellers pointing to these users
        Seller.objects.filter(user__in=users).delete()
        # delete the users themselves
        users.delete()

        # delete products created by script (we used '#' in their names)
        prods = Product.objects.filter(name__contains="#")
        # delete related specs, offers (cascade should remove tiers & deliveries if FK with cascade)
        prods_count = prods.count()
        prods.delete()

        # delete ProductStandards created by script if they match names
        ProductStandard.objects.filter(name__in=["DIN", "ASTM", "EN"]).delete()

        # delete categories with the sample hscodes
        ProductCategory.objects.filter(hscode__in=["7200", "7201", "7202", "7203", "7306", "7208"]).delete()

        # Also cleanup any offers/pricing tiers/delivery that might remain for safety
        PricingTier.objects.filter(offer__isnull=False).filter(offer__product__name__icontains="#").delete()
        DeliveryLocation.objects.filter(offer__isnull=False).filter(offer__product__name__icontains="#").delete()
        Offer.objects.filter(product__name__contains="#").delete()

        self.stdout.write(self.style.WARNING(f"Removed sample users, {prods_count} sample products, standards and categories."))
