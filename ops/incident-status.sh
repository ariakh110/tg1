#!/usr/bin/env bash
# Read-only status collection. Does not print environment files or private keys.
set -u
if [[ "$EUID" -ne 0 ]]; then
  echo 'Run with sudo bash ops/incident-status.sh' >&2
  exit 1
fi
printf '\n=== TIME ===\n'
date -u
printf '\n=== SERVICE BOUNDARIES ===\n'
systemctl show tirexa-frontend tirexa-backend nginx \
  -p Id -p ActiveState -p UnitFileState -p User -p Group -p WorkingDirectory \
  -p ProtectSystem -p ProtectHome -p PrivateTmp -p NoNewPrivileges -p ReadWritePaths
printf '\n=== EFFECTIVE SSH DEFAULTS (MATCH BLOCKS STILL NEED REVIEW) ===\n'
/usr/sbin/sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|allowusers) '
printf '\n=== DEPLOY PRIVILEGES ===\n'
id deploy
sudo -l -U deploy
printf '\n=== PORTS / FIREWALL ===\n'
ss -lntup
ufw status verbose
printf '\n=== PROCESSES (NO ARGUMENTS) ===\n'
ps -eo pid,ppid,user,pcpu,pmem,comm --sort=-pcpu | head -25
printf '\n=== PACKAGE METADATA (READ AS DATA) ===\n'
python3 - <<'PY'
import json
from pathlib import Path
for root in (Path('/srv/tirexa/frontend'), Path('/opt/tirexa/frontend')):
    for name in ('package.json', 'node_modules/next/package.json'):
        file = root / name
        if file.is_file():
            data = json.loads(file.read_text())
            print(str(file), data.get('dependencies', {}).get('next') if name == 'package.json' else data.get('version'))
PY
printf '\n=== EVIDENCE FILENAMES ===\n'
find /root/incident-2026-09-22-105859 -maxdepth 1 -type f -printf '%f %s bytes\n' 2>/dev/null
