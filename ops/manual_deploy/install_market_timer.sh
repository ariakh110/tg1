#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="$1"
BACKEND_PYTHON="$2"
if [[ "$APP_ROOT" != /* || "$BACKEND_PYTHON" != /* || "$APP_ROOT" =~ [[:space:]] || "$BACKEND_PYTHON" =~ [[:space:]] ]]; then
  echo 'Market timer requires absolute paths without spaces.' >&2
  exit 1
fi
cat > /etc/systemd/system/tirexa-market-sync.service <<UNIT
[Unit]
Description=Kaveh Metal external market schedule check
After=tirexa-backend.service network-online.target

[Service]
Type=oneshot
User=root
ExecStart=$BACKEND_PYTHON $APP_ROOT/backend/ops/run_market_sync.py
TimeoutStartSec=260
UMask=0077
UNIT
cat > /etc/systemd/system/tirexa-market-sync.timer <<'UNIT'
[Unit]
Description=Check Kaveh Metal market schedules every five minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=15s
Unit=tirexa-market-sync.service

[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now tirexa-market-sync.timer
systemctl start --no-block tirexa-market-sync.service
echo "==> Market schedule timer: $(systemctl is-active tirexa-market-sync.timer)"
