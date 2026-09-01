#!/usr/bin/env bash
# Apply committed Kavex release archives on the production server.
# Usage: bash /opt/tirexa/update.sh [both|backend|frontend]
set -Eeo pipefail

TARGET="${1:-both}"
CANONICAL_HOST="${CANONICAL_HOST:-kavehmetal.com}"
CANONICAL_ORIGIN="${CANONICAL_ORIGIN:-https://kavehmetal.com}"
LEGACY_CANONICAL_HOST="${LEGACY_CANONICAL_HOST:-kavex.ir}"
ORIGIN_IP_HOST="${ORIGIN_IP_HOST:-130.185.75.68}"
FRONTEND_API_URL="${FRONTEND_API_URL:-$CANONICAL_ORIGIN/api}"
if [[ "$TARGET" != "both" && "$TARGET" != "backend" && "$TARGET" != "frontend" ]]; then
  echo "ERROR: target must be one of: both, backend, frontend" >&2
  exit 2
fi

upsert_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"

  mkdir -p -- "$(dirname -- "$file")"
  touch -- "$file"
  if grep -q "^${key}=" "$file"; then
    sed -i "s|^${key}=.*$|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >> "$file"
  fi
}

backup_domain_env_once() {
  local file="$1"
  local backup="${file}.pre-kavehmetal"

  if [[ -f "$file" && ! -f "$backup" ]]; then
    cp -a -- "$file" "$backup"
  fi
}

configure_backend_domain() {
  local env_file="/opt/tirexa/backend/.env"
  backup_domain_env_once "$env_file"
  upsert_env_value "$env_file" "DJANGO_ALLOWED_HOSTS" \
    "$CANONICAL_HOST,www.$CANONICAL_HOST,127.0.0.1,localhost"
  upsert_env_value "$env_file" "CORS_ALLOWED_ORIGINS" \
    "$CANONICAL_ORIGIN,https://www.$CANONICAL_HOST"
  upsert_env_value "$env_file" "CSRF_TRUSTED_ORIGINS" \
    "$CANONICAL_ORIGIN,https://www.$CANONICAL_HOST"
  upsert_env_value "$env_file" "FRONTEND_BASE" "$CANONICAL_ORIGIN"
}

configure_frontend_domain() {
  local env_file="/opt/tirexa/frontend/.env.production.local"
  backup_domain_env_once "$env_file"
  upsert_env_value "$env_file" "NEXT_PUBLIC_SITE_URL" "$CANONICAL_ORIGIN"
  upsert_env_value "$env_file" "CANONICAL_SITE_URL" "$CANONICAL_ORIGIN"
  upsert_env_value "$env_file" "NEXT_PUBLIC_API_URL" "$FRONTEND_API_URL"
}

cd /opt/tirexa

if [[ "$TARGET" == "backend" || "$TARGET" == "both" ]]; then
  echo "==> Configuring backend domain environment..."
  configure_backend_domain
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
  echo "==> Configuring frontend domain environment..."
  configure_frontend_domain
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

  CANONICAL_SITE_URL="$CANONICAL_ORIGIN" \
  NEXT_PUBLIC_SITE_URL="$CANONICAL_ORIGIN" \
  NEXT_PUBLIC_API_URL="$FRONTEND_API_URL" \
  bash "$DEPLOY_HELPER" \
    "$FRONTEND_RELEASE" \
    "/opt/tirexa/frontend" \
    "tirexa-frontend"
fi

echo
echo "===== SMOKE TESTS ====="
sleep 3
LOCAL_CANONICAL_CURL=(
  curl -k -sS --resolve "$CANONICAL_HOST:443:127.0.0.1"
)
"${LOCAL_CANONICAL_CURL[@]}" -o /dev/null -w "home:          %{http_code}\n" \
  "$CANONICAL_ORIGIN/"
"${LOCAL_CANONICAL_CURL[@]}" -o /dev/null -w "api:           %{http_code}\n" \
  "$CANONICAL_ORIGIN/api/site-settings/"
"${LOCAL_CANONICAL_CURL[@]}" -o /dev/null -w "admin:         %{http_code}\n" \
  "$CANONICAL_ORIGIN/django-admin/"

if [[ "$TARGET" == "frontend" || "$TARGET" == "both" ]]; then
  IP_REDIRECT_RESULT="$(
    curl -k -sS -o /dev/null -w '%{http_code}|%{redirect_url}' \
      --connect-to "$ORIGIN_IP_HOST:443:127.0.0.1:443" \
      "https://$ORIGIN_IP_HOST/"
  )"
  IFS='|' read -r IP_REDIRECT_STATUS IP_REDIRECT_URL <<< "$IP_REDIRECT_RESULT"
  echo "origin IP:     $IP_REDIRECT_STATUS -> $IP_REDIRECT_URL"

  if [[ "$IP_REDIRECT_STATUS" != "301" || "$IP_REDIRECT_URL" != "$CANONICAL_ORIGIN/" ]]; then
    echo "ERROR: origin IP did not redirect permanently to $CANONICAL_ORIGIN/" >&2
    exit 1
  fi

  LEGACY_REDIRECT_RESULT="$(
    curl -k -sS -o /dev/null -w '%{http_code}|%{redirect_url}' \
      --resolve "$LEGACY_CANONICAL_HOST:443:127.0.0.1" \
      "https://$LEGACY_CANONICAL_HOST/products?family=sheet&source=legacy-host"
  )"
  IFS='|' read -r LEGACY_REDIRECT_STATUS LEGACY_REDIRECT_URL <<< "$LEGACY_REDIRECT_RESULT"
  echo "legacy host:   $LEGACY_REDIRECT_STATUS -> $LEGACY_REDIRECT_URL"

  if [[ "$LEGACY_REDIRECT_STATUS" != "301" || "$LEGACY_REDIRECT_URL" != "$CANONICAL_ORIGIN/products?family=sheet&source=legacy-host" ]]; then
    echo "ERROR: legacy Host did not redirect permanently to the canonical origin" >&2
    exit 1
  fi

  ST52_REDIRECT_RESULT="$(
    "${LOCAL_CANONICAL_CURL[@]}" -o /dev/null -w '%{http_code}|%{redirect_url}' \
      "$CANONICAL_ORIGIN/category/sheet/ST52?source=deploy-smoke"
  )"
  IFS='|' read -r ST52_REDIRECT_STATUS ST52_REDIRECT_URL <<< "$ST52_REDIRECT_RESULT"
  echo "ST52 legacy:   $ST52_REDIRECT_STATUS -> $ST52_REDIRECT_URL"

  if [[ "$ST52_REDIRECT_STATUS" != "301" || "$ST52_REDIRECT_URL" != "$CANONICAL_ORIGIN/category/sheet/st52?source=deploy-smoke" ]]; then
    echo "ERROR: uppercase ST52 did not redirect permanently to the lowercase canonical URL" >&2
    exit 1
  fi

  ROBOTS="$("${LOCAL_CANONICAL_CURL[@]}" "$CANONICAL_ORIGIN/robots.txt")"
  mapfile -t ROBOTS_SITEMAP_LINES < <(
    grep -iE '^[[:space:]]*sitemap[[:space:]]*:' <<< "$ROBOTS" || true
  )
  EXPECTED_SITEMAP_LINE="Sitemap: $CANONICAL_ORIGIN/sitemap.xml"
  if [[ ${#ROBOTS_SITEMAP_LINES[@]} -eq 1 && "${ROBOTS_SITEMAP_LINES[0]}" == "$EXPECTED_SITEMAP_LINE" ]]; then
    echo "canonical sitemap: exactly one directive in robots.txt"
  else
    echo "ERROR: robots.txt must contain exactly: $EXPECTED_SITEMAP_LINE" >&2
    printf 'Found sitemap directives:\n%s\n' "${ROBOTS_SITEMAP_LINES[*]:-(none)}" >&2
    exit 1
  fi
fi

SETTINGS="$("${LOCAL_CANONICAL_CURL[@]}" "$CANONICAL_ORIGIN/api/site-settings/")"
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
