from django.db import migrations


CANONICAL_SITEMAP = "https://kavehmetal.com/sitemap.xml"


def canonicalize_robots_sitemap(apps, schema_editor):
    SiteSEOSettings = apps.get_model("blog", "SiteSEOSettings")
    for settings in SiteSEOSettings.objects.all():
        kept_lines = []
        for line in (settings.robots_txt or "").splitlines():
            key, separator, _value = line.partition(":")
            if separator and key.strip().lower() == "sitemap":
                continue
            kept_lines.append(line)
        kept_lines.append(f"Sitemap: {CANONICAL_SITEMAP}")
        normalized = "\n".join(kept_lines).strip() + "\n"
        if settings.robots_txt != normalized:
            settings.robots_txt = normalized
            settings.save(update_fields=["robots_txt"])


class Migration(migrations.Migration):
    dependencies = [("blog", "0010_allow_noindex_routes_in_robots")]

    operations = [
        migrations.RunPython(
            canonicalize_robots_sitemap,
            migrations.RunPython.noop,
        ),
    ]
