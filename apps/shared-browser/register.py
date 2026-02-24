#!/usr/bin/env python3
"""
Seed shared-browser into the app registry on every container startup.
Called from run_A0.sh before uvicorn starts.
- If not registered: inserts the entry with autostart=True
- If registered with the old /usr/apps path: fixes cwd and sets autostart=True
- Otherwise: no-op
"""
import json
import os
import time

REGISTRY = '/a0/apps/.app_registry.json'
APP_NAME = 'shared-browser'

ENTRY = {
    "name": APP_NAME,
    "port": 9003,
    "cmd": "exec bash startup.sh",
    "cwd": "/a0/apps/shared-browser",
    "description": "Shared Browser — Collaborative browser instance",
    "env": {},
    "autostart": True,
    "core": True,
    "status": "registered",
    "pid": None,
    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "url": f"/{APP_NAME}/",
}

os.makedirs(os.path.dirname(REGISTRY), exist_ok=True)

try:
    with open(REGISTRY) as f:
        registry = json.load(f)
except Exception:
    registry = {}

changed = False

if APP_NAME not in registry:
    registry[APP_NAME] = ENTRY
    changed = True
    print(f"[shared-browser] registered with autostart=True")
else:
    existing = registry[APP_NAME]
    # Fix stale path left over from before the app was moved into apps/
    if '/usr/apps/' in existing.get('cwd', ''):
        existing['cwd'] = ENTRY['cwd']
        existing['cmd'] = ENTRY['cmd']
        changed = True
        print(f"[shared-browser] fixed cwd: /usr/apps/ -> /a0/apps/shared-browser")
    # Upgrade cmd from "bash startup.sh" to "exec bash startup.sh" so that
    # AppManager's tracked PID is the actual Flask process rather than the
    # intermediate /bin/sh shell (which exits after forking bash).
    if existing.get('cmd') == 'bash startup.sh':
        existing['cmd'] = ENTRY['cmd']
        changed = True
        print(f"[shared-browser] upgraded cmd to exec bash startup.sh")
    # Remove legacy ws_port — VNC/websockify stack has been removed
    if 'ws_port' in existing:
        del existing['ws_port']
        changed = True
        print(f"[shared-browser] removed legacy ws_port (VNC stack removed)")
    # Ensure autostart is on
    if not existing.get('autostart'):
        existing['autostart'] = True
        changed = True
        print(f"[shared-browser] enabled autostart")
    # Ensure core is set (cannot be removed via UI)
    if not existing.get('core'):
        existing['core'] = True
        changed = True
        print(f"[shared-browser] set core=True")

# Always reset pid/status on startup — the app is never running at this point
# and stale PIDs from the previous container lifetime can be reused by other
# processes, which would fool _cleanup_dead_processes() into skipping autostart.
registry[APP_NAME]['status'] = 'registered'
registry[APP_NAME]['pid'] = None
changed = True  # ensure we write regardless

if changed:
    with open(REGISTRY, 'w') as f:
        json.dump(registry, f, indent=2)
