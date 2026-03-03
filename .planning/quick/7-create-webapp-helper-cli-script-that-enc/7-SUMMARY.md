---
phase: quick-7
plan: "01"
subsystem: apps-system
tags: [webapp, cli, bash, skill, agent-guidance]
dependency_graph:
  requires: []
  provides: [webapp-helper-cli]
  affects: [usr/skills/web-app-builder/SKILL.md, prompts/agent.system.main.tips.md]
tech_stack:
  added: []
  patterns: [bash-cli-wrapper, curl-api-client, subcommand-dispatch]
key_files:
  created:
    - usr/bin/webapp-helper
  modified:
    - usr/skills/web-app-builder/SKILL.md
    - prompts/agent.system.main.tips.md
    - .gitignore
decisions:
  - "Use python3 for JSON payload building in register subcommand to handle special characters in start-cmd and description without quoting issues"
  - "Use full path /a0/usr/bin/webapp-helper in SKILL.md since usr/bin/ is not in container PATH"
  - "Update .gitignore to add !usr/bin/ and !usr/bin/** exceptions (was blocking new file)"
  - "Keep curl commands in SKILL.md only in Management commands Raw API section and Troubleshooting — all step-level commands now use webapp-helper"
metrics:
  duration: "~8 minutes"
  completed: "2026-03-03"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 3
---

# Quick Task 7: webapp-helper CLI Script — Summary

**One-liner:** Bash CLI wrapper at `usr/bin/webapp-helper` encapsulating all 8 webapp API operations (validate-name, alloc-port, init, register, start, stop, health-check, status) with consistent error output and exit codes, replacing raw curl construction in SKILL.md and system tips.

---

## What Was Built

### usr/bin/webapp-helper (321 lines)

Executable bash script (`chmod +x`) with `set -euo pipefail` and 8 subcommands:

| Subcommand | What it does |
|------------|-------------|
| `validate-name <name>` | Regex + reserved blocklist check. Outputs `VALID` or `ERROR: <reason>` |
| `alloc-port` | Calls `GET /webapp?action=alloc_port`, returns port number |
| `init <app-name> <template>` | Copies template dir, installs pip requirements |
| `register <app-name> <port> <cmd> [desc]` | POSTs registration JSON (cwd auto-derived) |
| `start <app-name>` | POSTs `{"action":"start","name":"..."}` |
| `stop <app-name>` | POSTs `{"action":"stop","name":"..."}` |
| `health-check <port> [timeout]` | Polls port every 0.5s, default 10s timeout |
| `status [app-name]` | GET list or single app status |

Constants hardcoded once at top:
```bash
API_URL="http://localhost/webapp"
APPS_DIR="/a0/apps"
TEMPLATES_DIR="/a0/apps/_templates"
RESERVED="login logout health dev-ping socket.io static message poll ..."
```

### SKILL.md (Steps 1, 3, 4, 6, 7, 8 updated)

- Step 1: `webapp-helper validate-name "$APP_NAME"` replaces inline bash regex + grep loop
- Step 3: `PORT=$(webapp-helper alloc-port)` replaces curl+python3 pipeline
- Step 4: `webapp-helper init "$APP_NAME" "{TEMPLATE}"` replaces cp + ls + pip3
- Step 6: `webapp-helper register "$APP_NAME" "$PORT" "{START_CMD}" "{DESC}"` replaces curl POST
- Step 7: `webapp-helper start "$APP_NAME"` replaces curl POST
- Step 8: `webapp-helper health-check "$PORT"` replaces 20-iteration polling loop
- Management commands: webapp-helper leads, Raw API section retained for restart/autostart/remove
- Steps 2 and 5 unchanged (require agent judgment)
- YAML description updated to mention webapp-helper

### prompts/agent.system.main.tips.md (3 additions)

- Directive after skill auto-load note: use webapp-helper, do NOT construct raw curl
- Point 4 updated: "use `webapp-helper alloc-port` to allocate ports"
- Internal vs External URLs section: CLI helper bullet added

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] .gitignore blocked new usr/bin/ directory**
- **Found during:** Task 1 commit
- **Issue:** `.gitignore` had `usr/**` with exceptions only for `usr/skills/`. The new `usr/bin/webapp-helper` was ignored.
- **Fix:** Added `!usr/bin/` and `!usr/bin/**` to `.gitignore` exceptions, matching the pattern already used for skills.
- **Files modified:** `.gitignore`
- **Commit:** c750c9e (included in Task 1 commit)

---

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | c750c9e | feat(quick-7): add webapp-helper CLI script with 8 subcommands |
| Task 2 | e24cc21 | feat(quick-7): update SKILL.md to use webapp-helper subcommands |
| Task 3 | 2f52cde | feat(quick-7): update system tips to direct agent to use webapp-helper |

---

## Self-Check: PASSED

- [x] `usr/bin/webapp-helper` exists and is executable
- [x] `bash -n usr/bin/webapp-helper` passes (no syntax errors)
- [x] 321 lines (above 150 minimum)
- [x] All 8 subcommands present: validate-name, alloc-port, init, register, start, stop, health-check, status
- [x] API_URL, APPS_DIR, TEMPLATES_DIR constants at top
- [x] SKILL.md contains 14 occurrences of webapp-helper (above 10 minimum)
- [x] Steps 2 and 5 preserved (grep finds "Auto-select a template" and "Customize the app")
- [x] System tips contain 3 occurrences of webapp-helper (at minimum 3)
- [x] Commits c750c9e, e24cc21, 2f52cde all exist in git log
