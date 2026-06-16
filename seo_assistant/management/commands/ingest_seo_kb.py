"""بارگذاریِ پایگاه دانش سئو از markdownِ بسته‌بندی‌شده به مدل SeoKnowledge.

هر فایل markdown به تکه‌های سطحِ سرفصل (## / ###) شکسته می‌شود؛ هر تکه یک رکورد SeoKnowledge
(با layer = base/2026، source = نام فایل، title = سرفصل) می‌شود. اجرای دوباره idempotent است
(بر اساس source+title به‌روزرسانی می‌کند، نه ساختِ تکراری).

استفاده:
    python manage.py ingest_seo_kb                # از مسیر بسته‌بندی‌شدهٔ داخل اپ
    python manage.py ingest_seo_kb --path D:/seo  # از یک مسیر دلخواه (با زیرپوشه‌های knowledge-base[-2026])
    python manage.py ingest_seo_kb --embed        # پس از بارگذاری، embedding را هم بساز
"""
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from seo_assistant.models import SeoKnowledge

APP_KB_DIR = Path(__file__).resolve().parents[2] / "knowledge_base"


def _split_sections(text):
    """متن markdown را به (title, body) بر اساس سرفصل‌های ## و ### می‌شکند."""
    lines = text.splitlines()
    sections = []
    cur_title = ""
    cur_body = []
    for line in lines:
        m = re.match(r"^(#{2,3})\s+(.*)$", line)
        if m:
            if cur_title or "".join(cur_body).strip():
                sections.append((cur_title, "\n".join(cur_body).strip()))
            cur_title = m.group(2).strip()
            cur_body = []
        else:
            cur_body.append(line)
    if cur_title or "".join(cur_body).strip():
        sections.append((cur_title, "\n".join(cur_body).strip()))
    # تکه‌های بسیار کوتاه/خالی را دور بریز
    return [(t, b) for t, b in sections if (t or b) and len(b) >= 20]


def _layer_for(rel_dir, custom_path):
    name = rel_dir.lower()
    if "2026" in name:
        return SeoKnowledge.LAYER_2026
    return SeoKnowledge.LAYER_BASE


def _iter_md_files(base_path, custom):
    """بازگرداندن (layer, source_label, Path) برای همهٔ فایل‌های md.

    حالت بسته‌بندی‌شده: knowledge_base/base/*.md و knowledge_base/2026/*.md
    حالت --path دلخواه: <path>/knowledge-base/*.md و <path>/knowledge-base-2026/*.md
    """
    if custom:
        root = Path(custom)
        candidates = [
            (SeoKnowledge.LAYER_BASE, root / "knowledge-base"),
            (SeoKnowledge.LAYER_2026, root / "knowledge-base-2026"),
        ]
    else:
        candidates = [
            (SeoKnowledge.LAYER_BASE, base_path / "base"),
            (SeoKnowledge.LAYER_2026, base_path / "2026"),
        ]
    for layer, folder in candidates:
        if not folder.exists():
            continue
        for md in sorted(folder.glob("*.md")):
            yield layer, f"{folder.name}/{md.name}", md


class Command(BaseCommand):
    help = "بارگذاری پایگاه دانش سئو (markdown) به مدل SeoKnowledge."

    def add_arguments(self, parser):
        parser.add_argument("--path", default="", help="مسیر دلخواهِ پایگاه دانش (شامل knowledge-base[-2026]).")
        parser.add_argument("--embed", action="store_true", help="پس از بارگذاری، embedding بساز.")
        parser.add_argument("--purge", action="store_true", help="ابتدا دانش‌های base/2026 موجود را حذف کن.")

    def handle(self, *args, **options):
        custom = options["path"].strip()
        if options["purge"]:
            deleted, _ = SeoKnowledge.objects.filter(
                layer__in=[SeoKnowledge.LAYER_BASE, SeoKnowledge.LAYER_2026]
            ).delete()
            self.stdout.write(f"purged {deleted} existing base/2026 rows")

        created = updated = 0
        for layer, source, md in _iter_md_files(APP_KB_DIR, custom):
            try:
                text = md.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = md.read_text(encoding="utf-8", errors="replace")
            sections = _split_sections(text)
            for order, (title, body) in enumerate(sections):
                obj, was_created = SeoKnowledge.objects.update_or_create(
                    source=source,
                    title=title[:200],
                    defaults={
                        "layer": layer,
                        "topic": md.stem,
                        "body": body,
                        "is_active": True,
                        "sort_order": order,
                    },
                )
                created += int(was_created)
                updated += int(not was_created)

        total = SeoKnowledge.objects.count()
        self.stdout.write(f"ingested: created={created} updated={updated} total={total}")

        if options["embed"]:
            try:
                from seo_assistant.ai import SeoAssistantError, ensure_embeddings

                n = ensure_embeddings()
                self.stdout.write(f"embedded={n}")
            except SeoAssistantError as exc:
                self.stdout.write(f"embed skipped: {exc}")
