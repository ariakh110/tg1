#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="$1"
BACKEND_PYTHON="$2"
if [[ "$APP_ROOT" != /* || "$BACKEND_PYTHON" != /* || "$APP_ROOT" =~ [[:space:]] || "$BACKEND_PYTHON" =~ [[:space:]] ]]; then
  echo 'Inquiry timer requires absolute paths without spaces.' >&2
  exit 1
fi
cat > /etc/systemd/system/tirexa-inquiry-notices.service <<UNIT
[Unit]
Description=Kaveh Metal private purchase inquiry notice dispatch
After=tirexa-backend.service network-online.target

[Service]
Type=oneshot
User=root
ExecStart=$BACKEND_PYTHON $APP_ROOT/backend/ops/run_inquiry_notices.py
TimeoutStartSec=260
UMask=0077
UNIT
cat > /etc/systemd/system/tirexa-inquiry-notices.timer <<'UNIT'
[Unit]
Description=Check Kaveh Metal purchase inquiry notices every minute

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
AccuracySec=5s
Unit=tirexa-inquiry-notices.service

[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now tirexa-inquiry-notices.timer
echo "==> Inquiry notice timer: $(systemctl is-active tirexa-inquiry-notices.timer)"
