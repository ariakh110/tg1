from django.db import migrations, models


CRAWLABLE_NOINDEX_PATHS = {
    "/admin",
    "/account",
    "/auth",
    "/cart",
    "/checkout",
    "/orders",
    "/offers",
    "/products/*/buy",
}


def allow_noindex_routes(apps, schema_editor):
    SiteSEOSettings = apps.get_model("blog", "SiteSEOSettings")
    for settings in SiteSEOSettings.objects.all():
        kept_lines = []
        changed = False
        for line in (settings.robots_txt or "").splitlines():
            key, separator, value = line.partition(":")
            normalized_path = value.strip().rstrip("/").lower() if separator else ""
            if key.strip().lower() == "disallow" and normalized_path in CRAWLABLE_NOINDEX_PATHS:
                changed = True
                continue
            kept_lines.append(line)
        if changed:
            settings.robots_txt = "\n".join(kept_lines).strip() + "\n"
            settings.save(update_fields=["robots_txt"])


class Migration(migrations.Migration):
    dependencies = [("blog", "0009_landing")]

    operations = [
        migrations.AlterField(
            model_name="siteseosettings",
            name="robots_txt",
            field=models.TextField(default="User-agent: *\nAllow: /\nDisallow: /api/\n"),
        ),
        migrations.RunPython(allow_noindex_routes, migrations.RunPython.noop),
    ]
