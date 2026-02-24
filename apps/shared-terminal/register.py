#!/usr/bin/env python3
"""
Seed shared-terminal into the app registry on every container startup.
Called from run_A0.sh before uvicorn starts.
- If not registered: inserts the entry with autostart=True
- Otherwise: ensures autostart and core flags are set, resets pid/status
"""
import json
import os
import time

REGISTRY = '/a0/apps/.app_registry.json'
APP_NAME = 'shared-terminal'

ENTRY = {
    "name": APP_NAME,
    "port": 9004,
    "cmd": "exec bash startup.sh",
    "cwd": "/a0/apps/shared-terminal",
    "description": "Shared Terminal \u2014 Persistent tmux session",
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
    print(f"[shared-terminal] registered with autostart=True")
else:
    existing = registry[APP_NAME]
    if not existing.get('autostart'):
        existing['autostart'] = True
        changed = True
        print(f"[shared-terminal] enabled autostart")
    if not existing.get('core'):
        existing['core'] = True
        changed = True
        print(f"[shared-terminal] set core=True")

# Always reset pid/status on startup — the app is never running at this point
# and stale PIDs from the previous container lifetime can be reused by other
# processes, which would fool _cleanup_dead_processes() into skipping autostart.
registry[APP_NAME]['status'] = 'registered'
registry[APP_NAME]['pid'] = None
changed = True

if changed:
    with open(REGISTRY, 'w') as f:
        json.dump(registry, f, indent=2)
