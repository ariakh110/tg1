#!/usr/bin/env bash
# Apply committed Kavex release archives on the production server.
# Usage: bash /opt/tirexa/update.sh [both|backend|frontend]
set -Eeo pipefail

TARGET="${1:-both}"
if [[ "$TARGET" != "both" && "$TARGET" != "backend" && "$TARGET" != "frontend" ]]; then
  echo "ERROR: target must be one of: both, backend, frontend" >&2
  exit 2
fi

cd /opt/tirexa

if [[ "$TARGET" == "backend" || "$TARGET" == "both" ]]; then
  echo "==> Extracting backend..."
  tar -xzf backend.tar.gz -C backend
  echo "==> Running migrations and collectstatic..."
  cd backend
  bash ops/prepare_media.sh /opt/tirexa/backend tirexa-backend
  set -a
  # shellcheck disable=SC1091
  source ./.env
  set +a
  .venv/bin/python manage.py migrate --noinput
  .venv/bin/python manage.py collectstatic --noinput | tail -1
  cd /opt/tirexa
  systemctl restart tirexa-backend
  echo "==> tirexa-backend: $(systemctl is-active tirexa-backend)"
fi

if [[ "$TARGET" == "frontend" || "$TARGET" == "both" ]]; then
  FRONTEND_RELEASE="/opt/tirexa/frontend_release"
  echo "==> Extracting frontend into staging..."
  rm -rf -- "$FRONTEND_RELEASE"
  mkdir -p "$FRONTEND_RELEASE"
  tar -xzf frontend.tar.gz -C "$FRONTEND_RELEASE"

  DEPLOY_HELPER="$FRONTEND_RELEASE/ops/deploy_frontend_release.sh"
  if [[ ! -f "$DEPLOY_HELPER" ]]; then
    echo "ERROR: frontend archive is missing ops/deploy_frontend_release.sh" >&2
    exit 1
  fi

  # Git for Windows can export shell scripts with CRLF when core.autocrlf is
  # enabled. Normalize defensively before Bash parses strict-mode options.
  if LC_ALL=C grep -q $'\r' "$DEPLOY_HELPER"; then
    echo "==> Normalizing frontend deployment helper line endings..."
    sed -i 's/\r$//' "$DEPLOY_HELPER"
  fi

  bash "$DEPLOY_HELPER" \
    "$FRONTEND_RELEASE" \
    "/opt/tirexa/frontend" \
    "tirexa-frontend"
fi

echo
echo "===== SMOKE TESTS ====="
sleep 3
curl -s -o /dev/null -w "home:          %{http_code}\n" http://127.0.0.1/
curl -s -o /dev/null -w "api:           %{http_code}\n" http://127.0.0.1/api/site-settings/
curl -s -o /dev/null -w "admin:         %{http_code}\n" http://127.0.0.1/django-admin/

SETTINGS="$(curl -s http://127.0.0.1/api/site-settings/)"
if grep -q google_tag_manager_id <<< "$SETTINGS"; then
  echo "GTM field: present"
else
  echo "GTM field: missing"
fi
if grep -q openai_configured <<< "$SETTINGS"; then
  echo "openai_configured field: present"
else
  echo "openai_configured field: missing"
fi
if grep -q openai_api_key <<< "$SETTINGS"; then
  echo "SECURITY ERROR: openai_api_key is public"
else
  echo "OpenAI key: hidden"
fi
echo "===== DONE ====="

if [[ "$TARGET" == "backend" || "$TARGET" == "both" ]]; then
  echo
  echo "===== POST-DEPLOY REMINDER ====="
  echo "Sales and SEO assistants use separate credentials."
  echo "Verify each assistant API key in the admin panel."
  echo "Default AvalAI base URL: https://api.avalai.ir/v1"
fi
