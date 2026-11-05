"""Execute the release boundary with a local fake interpreter, never an updater."""
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from django.test import SimpleTestCase

from products.catalog_seed import PACKAGE_SHA256

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / 'ops' / 'manual_deploy' / 'seed_farda_sections.sh'
BASH = shutil.which('bash') or ('C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else None)


@unittest.skipUnless(BASH and Path(BASH).exists(), 'Bash is required for release-boundary tests')
class CatalogReleaseTests(SimpleTestCase):
    def run_helper(self, preview_rc=0, apply_rc=0):
        with tempfile.TemporaryDirectory(prefix='farda-seed-test-') as directory:
            temp = Path(directory)
            stub = temp / 'python-stub.sh'
            log = temp / 'calls.log'
            stub.write_text('#!/usr/bin/env bash\n'
                'printf "%s\\n" "$*" >> "$SEED_TEST_LOG"\n'
                'case " $* " in\n'
                '  *" --dry-run "*) exit "$SEED_TEST_PREVIEW_RC" ;;\n'
                '  *" --apply "*) exit "$SEED_TEST_APPLY_RC" ;;\n'
                '  *) exit 99 ;;\n'
                'esac\n', encoding='utf-8', newline='\n')
            stub.chmod(0o755)
            env = {**os.environ, 'SEED_TEST_LOG': log.as_posix(),
                   'SEED_TEST_PREVIEW_RC': str(preview_rc), 'SEED_TEST_APPLY_RC': str(apply_rc)}
            result = subprocess.run([BASH, HELPER.as_posix(), stub.as_posix()],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            return result, log.read_text().splitlines() if log.exists() else []

    def test_release_preview_then_explicit_apply_share_pinned_hash(self):
        result, calls = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [
            f'manage.py seed_farda_sections --dry-run --expected-sha256 {PACKAGE_SHA256}',
            f'manage.py seed_farda_sections --apply --actor release:update.sh --expected-sha256 {PACKAGE_SHA256}',
        ])

    def test_failed_preview_prevents_apply(self):
        result, calls = self.run_helper(preview_rc=37)
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(len(calls), 1)

    def test_apply_failure_stops_release(self):
        result, calls = self.run_helper(apply_rc=38)
        self.assertEqual(result.returncode, 38, result.stderr)
        self.assertEqual(len(calls), 2)

    def test_scripts_are_valid_bash(self):
        for path in (HELPER, ROOT / 'ops/manual_deploy/update.sh'):
            result = subprocess.run([BASH, '-n', path.as_posix()], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless((ROOT / '.git').exists() and shutil.which('git'), 'Requires committed Git archive')
class CatalogArchiveTests(SimpleTestCase):
    def test_committed_release_asset_keeps_reviewed_bytes(self):
        name = 'products/data/farda_sections_v1.json'
        archive = subprocess.check_output(['git', '-c', 'core.autocrlf=false', 'archive', 'HEAD', name], cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            raw = tar.extractfile(name).read()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), PACKAGE_SHA256)
