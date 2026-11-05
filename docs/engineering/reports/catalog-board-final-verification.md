# Catalog board — final verification and release boundary

2026-11-06; workflow `catalog-board-price-only`.

## Post-review checks on final runtime tree

- Full isolated Django suite: **511/511 pass, 66.452s**, `tg1.settings_test`,
  temporary MEDIA_ROOT, no live database/provider writes. Expected injected matrix
  error and thumbnail cleanup errors are passing rollback/failure-path tests.
- Full frontend Node suite: `node --test tests/*.test.mjs`, **93/93 pass**.
- Focused final Node regressions:15/15; six new findings watched RED→GREEN.
- Touched runtime ESLint: exit0.
- Native `npm run build`: exit0, Next16.4.2/Turbopack. Existing middleware deprecation
  remains; no dependency or schema change. Loopback API/site environment was used
  only for this process; `.env` files were not edited.
- Earlier browser checkpoint before the final fix pass:14/14 local Chrome/Playwright
  scenarios (nine desktop families, four mobile families, admin paginated save/
  blank/CAS flow), no page JS errors or unexpected writes. Action trial clicks and
  reservation intent passed. Screenshots in `catalog-board-visual/` describe that
  checkpoint, not a fresh post-fix browser or deployed site.
- Additional preview-server execution was rejected by host policy and not retried
  through another route. Final presentation fixes are verified by data regressions,
  source inspection and production compilation; final browser/real-device smoke
  remains a release check, not a claim of this run.

Independent review and disposition: `catalog-board-quality-review.md`.
Spec compliance: `catalog-board-spec-review.md`. Full execution ledger and every
decision are preserved in `catalog-board-execution-ledger.md` after finalization.

## Reproduce safely

Backend tests must use `--settings=tg1.settings_test --noinput`, never production
settings. Run with disposable media; the runner used:

```python
import os, tempfile
os.environ['DJANGO_SETTINGS_MODULE'] = 'tg1.settings_test'
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
with tempfile.TemporaryDirectory(prefix='catalog-board-tests-') as media:
    settings.MEDIA_ROOT = media
    call_command('test', interactive=False, verbosity=1)
```

Frontend unit tests need no server. Browser fixture requires an authorized local
server built/run with API `http://127.0.0.1:8765/api` and site `http://localhost:3003`;
set `BASE_URL=http://localhost:3003`, `PLAYWRIGHT_MODULE_PATH` to the installed
Playwright package and `ARTIFACT_DIR` to a disposable folder, then run
`node tests/productBoard.browser.cjs`. It binds loopback8765 and uses artificial
data; never point this harness or a verification build at a production write API.

## Release decision

Both source repositories need the update: frontend depends on new admin row API.
Use existing release procedure only with separate authorization. Do not upload
the verification `.next`, environments, virtualenv, DB, scratch or test fixtures.
Build source with real server environment; no new schema migration is required by
this change. After release, smoke-test all families and two differently conditioned
tiers on a staging copy before making real price edits. Generic CSV/XLSX import is
not this strict amount-only editor. No merge, push, deployment or server write was
performed. Existing non-main branches and unrelated frontend docs are preserved.
