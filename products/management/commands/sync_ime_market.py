from django.core.management.base import BaseCommand, CommandError

from products.external_markets import MarketSyncError, sync_ime_market


class Command(BaseCommand):
    help = "Synchronize steel-chain physical trades from the official Iran Mercantile Exchange service."

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="from_jalali", help="Jalali date, for example 1405/07/01")
        parser.add_argument("--to", dest="to_jalali", help="Jalali date, for example 1405/07/15")

    def handle(self, *args, **options):
        try:
            count = sync_ime_market(options.get("from_jalali"), options.get("to_jalali"))
        except MarketSyncError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Synchronized {count} IME steel trade rows."))
