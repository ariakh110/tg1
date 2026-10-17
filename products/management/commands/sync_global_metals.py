from django.core.management.base import BaseCommand, CommandError

from products.external_markets import MarketSyncError, sync_global_metals


class Command(BaseCommand):
    help = "Synchronize licensed global metal observations from the configured provider."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Ignore the minimum refresh interval.")

    def handle(self, *args, **options):
        try:
            count = sync_global_metals(force=options["force"])
        except MarketSyncError as exc:
            raise CommandError(str(exc)) from exc
        if count:
            self.stdout.write(self.style.SUCCESS(f"Synchronized {count} global metal observations."))
        else:
            self.stdout.write(self.style.WARNING("No observations synchronized; configure METALS_DEV_API_KEY."))
