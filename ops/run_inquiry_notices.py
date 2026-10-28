"""Root timer launcher: keep secrets in memory and run Django as backend user."""
import os
import pwd
import subprocess
import sys
from pathlib import Path


def main():
    pid = subprocess.check_output(['systemctl', 'show', 'tirexa-backend', '-p', 'MainPID', '--value'], text=True).strip()
    if not pid.isdecimal() or int(pid) <= 1:
        raise SystemExit('Backend is not running; inquiry notices deferred.')
    raw = Path(f'/proc/{pid}/environ').read_bytes()
    environment = dict(entry.decode().split('=', 1) for entry in raw.split(b'\0') if b'=' in entry)
    root = Path(__file__).resolve().parents[1]
    identity = pwd.getpwuid(Path(f'/proc/{pid}').stat().st_uid)
    result = subprocess.run([sys.executable, str(root / 'manage.py'), 'dispatch_purchase_inquiry_notices'],
        cwd=root, env=environment, user=identity.pw_uid, group=identity.pw_gid,
        extra_groups=os.getgrouplist(identity.pw_name, identity.pw_gid), timeout=240)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
