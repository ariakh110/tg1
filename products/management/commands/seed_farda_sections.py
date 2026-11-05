import json

from django.core.management.base import BaseCommand, CommandError

from products.catalog_seed import SeedError, seed_sections


class Command(BaseCommand):
    help = 'Preview or explicitly apply the pinned inactive angle/channel catalog. Offline, create-only.'

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--dry-run', action='store_true', help='Read-only preview (default).')
        mode.add_argument('--apply', action='store_true', help='Atomically create missing rows once.')
        parser.add_argument('--actor', default='', help='Operator/release label, required for apply.')
        parser.add_argument('--expected-sha256', default=None)

    def handle(self, *args, **options):
        try:
            report = seed_sections(apply=options['apply'], actor=options['actor'],
                                   expected_sha256=options['expected_sha256'])
        except SeedError as exc:
            if exc.report:
                self.stderr.write(json.dumps(exc.report, ensure_ascii=True, sort_keys=True))
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(report, ensure_ascii=True, sort_keys=True))
