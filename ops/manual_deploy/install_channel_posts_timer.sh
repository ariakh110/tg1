#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="$1"
BACKEND_PYTHON="$2"
if [[ "$APP_ROOT" != /* || "$BACKEND_PYTHON" != /* || "$APP_ROOT" =~ [[:space:]] || "$BACKEND_PYTHON" =~ [[:space:]] ]]; then
  echo 'Channel post timer requires absolute paths without spaces.' >&2
  exit 1
fi
cat > /etc/systemd/system/tirexa-channel-posts.service <<UNIT
[Unit]
Description=Kaveh Metal private recurring channel post dispatch
After=tirexa-backend.service network-online.target

[Service]
Type=oneshot
User=root
ExecStart=$BACKEND_PYTHON $APP_ROOT/backend/ops/run_channel_posts.py
TimeoutStartSec=260
UMask=0077
UNIT
cat > /etc/systemd/system/tirexa-channel-posts.timer <<'UNIT'
[Unit]
Description=Check Kaveh Metal recurring channel posts every minute

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
AccuracySec=5s
Unit=tirexa-channel-posts.service

[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now tirexa-channel-posts.timer
echo "==> Channel post notice timer: $(systemctl is-active tirexa-channel-posts.timer)"
