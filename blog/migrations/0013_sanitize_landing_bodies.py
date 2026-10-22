from django.db import migrations


def sanitize_existing_bodies(apps, schema_editor):
    from blog.content_sanitizer import sanitize_content

    Landing = apps.get_model("blog", "Landing")
    queryset = Landing.objects.using(schema_editor.connection.alias)
    for landing in queryset.only("pk", "body").iterator(chunk_size=200):
        clean = sanitize_content(landing.body)
        if clean != landing.body:
            queryset.filter(pk=landing.pk).update(body=clean)


class Migration(migrations.Migration):
    dependencies = [("blog", "0012_landing_expert_fields")]
    # Removed executable HTML cannot be reconstructed on rollback.
    operations = [migrations.RunPython(sanitize_existing_bodies, migrations.RunPython.noop)]
