#!/usr/bin/env bash
set -euo pipefail

BACKEND_ROOT="${1:-$(pwd)}"
SERVICE_NAME="${2:-tirexa-backend}"
DETECTED_USER="$(systemctl show "$SERVICE_NAME" --property=User --value 2>/dev/null || true)"
SERVICE_USER="${BACKEND_SERVICE_USER:-${DETECTED_USER:-www-data}}"
SERVICE_GROUP="${BACKEND_SERVICE_GROUP:-$(id -gn "$SERVICE_USER")}"
MEDIA_ROOT="${DJANGO_MEDIA_ROOT:-$BACKEND_ROOT/media}"

install -d -m 775 \
  "$MEDIA_ROOT" \
  "$MEDIA_ROOT/blog" \
  "$MEDIA_ROOT/blog/thumbs" \
  "$MEDIA_ROOT/blog/media" \
  "$MEDIA_ROOT/blog/og"

chown -R "$SERVICE_USER:$SERVICE_GROUP" "$MEDIA_ROOT"
chmod -R u+rwX,g+rX "$MEDIA_ROOT"

if command -v runuser >/dev/null 2>&1; then
  runuser -u "$SERVICE_USER" -- test -w "$MEDIA_ROOT/blog/thumbs"
  runuser -u "$SERVICE_USER" -- test -w "$MEDIA_ROOT/blog/media"
else
  test -w "$MEDIA_ROOT/blog/thumbs"
  test -w "$MEDIA_ROOT/blog/media"
fi

echo "Media storage ready: $MEDIA_ROOT ($SERVICE_USER:$SERVICE_GROUP)"
