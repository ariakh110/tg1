from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from products.external_markets import MarketSyncError, import_global_metals_csv


class Command(BaseCommand):
    help = "Import reviewed global metal observations from a UTF-8 CSV file."

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *args, **options):
        path = Path(options["path"])
        try:
            count = import_global_metals_csv(path.read_bytes())
        except (OSError, MarketSyncError, UnicodeDecodeError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Imported {count} global metal observations."))
