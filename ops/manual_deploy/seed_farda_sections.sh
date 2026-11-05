#!/usr/bin/env bash
# Called from the backend root, with the updater's resolved Python/DB environment.
# Offline, one-shot, inactive catalog only. Fail closed before continuing release.
set -euo pipefail

if [[ $# -ne 1 || -z "$1" ]]; then
  echo 'Usage: bash ops/manual_deploy/seed_farda_sections.sh BACKEND_PYTHON' >&2
  exit 2
fi
seed_python="$1"
seed_sha256='e9d903b8fe338bee4d72767311e9e236daf73f949280449af9fb750f19affa57'

"$seed_python" manage.py seed_farda_sections --dry-run --expected-sha256 "$seed_sha256"
"$seed_python" manage.py seed_farda_sections --apply --actor release:update.sh --expected-sha256 "$seed_sha256"
