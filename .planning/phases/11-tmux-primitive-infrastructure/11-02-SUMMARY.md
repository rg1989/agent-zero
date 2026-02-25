---
phase: 11-tmux-primitive-infrastructure
plan: 02
subsystem: infra
tags: [docker, docker-compose, bind-mount, deployment, copy_A0]

# Dependency graph
requires:
  - phase: 11-tmux-primitive-infrastructure/11-01
    provides: TmuxTool and prompt doc files that must reach /a0 inside container
provides:
  - docker-compose.yml with python/ and prompts/ bind mounts (live-reload for all future tool and prompt changes)
  - copy_A0.sh with cp -ru (sync-newer) replacing cp -rn (no-clobber) and presence-check guard
  - Verified agent awareness of TmuxTool send/keys/read actions
affects:
  - 12-readiness-detection
  - 13-interactive-cli-session-lifecycle
  - 14-opencode-session-wrapper
  - 15-cli-orchestration-skill-documentation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bind mount pattern: ./python:/a0/python and ./prompts:/a0/prompts for live-reload without rebuild"
    - "cp -ru (update-newer) in copy_A0.sh: image files always propagate to /a0 even when volume is populated"

key-files:
  created: []
  modified:
    - docker-compose.yml
    - docker/run/fs/ins/copy_A0.sh

key-decisions:
  - "cp -ru (update-newer) chosen over cp -rn (no-clobber): ensures image-baked files always reach /a0 on restart; bind mounts shadow the copied files at runtime, so the copy is safe even with mounts active"
  - "Presence-check guard (if [ ! -f run_ui.py ]) removed: guard was the root cause of tool and prompt files being skipped on restarts with a populated volume"
  - "Bind mounts added for python/ and prompts/ so all future tool and prompt changes deploy automatically without container rebuild or volume wipe"

patterns-established:
  - "Live-reload pattern: add ./host-dir:/a0/container-dir bind mount in docker-compose.yml to make any directory live-editable in container without rebuild"
  - "copy_A0.sh role: sync non-mounted paths (run_ui.py, requirements.txt, etc.) from image to /a0 on every start; mounted paths are handled by docker-compose volumes and shadow the copies"

requirements-completed: [TERM-01, TERM-02, TERM-03, TERM-04]

# Metrics
duration: 10min
completed: 2026-02-25
---

# Phase 11 Plan 02: Docker Deployment Gap Closure Summary

**Python/ and prompts/ bind mounts added to docker-compose.yml; copy_A0.sh fixed to sync-newer so TmuxTool and its prompt doc reach /a0 on every container restart without volume wipe**

## Performance

- **Duration:** ~10 min (including human-verify checkpoint)
- **Started:** 2026-02-25T17:20:00Z
- **Completed:** 2026-02-25T17:30:00Z
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 2

## Accomplishments

- Root cause of Phase 11-01 UAT failure identified and fixed: `copy_A0.sh` presence-check guard (`if [ ! -f run_ui.py ]`) was silently skipping all file sync when `/a0` was already populated from the persistent volume
- `docker-compose.yml` extended with two bind mounts (`./python:/a0/python`, `./prompts:/a0/prompts`) providing live-reload for all current and future tool and prompt changes without container rebuild
- `copy_A0.sh` rewritten to use `cp -ru` (update-newer) removing the presence-check guard — image-baked files now always propagate to `/a0` on every restart
- Human verification confirmed: agent correctly described TmuxTool send/keys/read actions and successfully executed a TmuxTool send smoke test
- All four TERM requirements (TERM-01 through TERM-04) confirmed working end-to-end in the live container

## Task Commits

Each task was committed atomically:

1. **Task 1: Add python/ and prompts/ bind mounts; fix copy_A0.sh sync logic** - `793c6a4` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `docker-compose.yml` - Added `./python:/a0/python` and `./prompts:/a0/prompts` bind mounts under the agent-zero service volumes block
- `docker/run/fs/ins/copy_A0.sh` - Removed presence-check guard; replaced `cp -rn` (no-clobber) with `cp -ru` (update-newer) so image files propagate to /a0 on every container start

## Decisions Made

- Used `cp -ru --no-preserve=ownership,mode` so that the update-newer copy does not change file ownership/permissions on `/a0` (owned by the container user, not the build process)
- Bind mounts declared for `python/` and `prompts/` only (not `run_ui.py` or `requirements.txt`) — those files do not change frequently enough to warrant mounts and are handled correctly by the `cp -ru` logic

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — both files changed cleanly per plan specification and the human-verify checkpoint passed on first attempt.

## User Setup Required

**One-time volume wipe required when first applying this fix to an existing deployment.**

If the persistent volume was already populated before this fix, the volume must be wiped once so `copy_A0.sh` can sync new files:

```bash
cd /path/to/agent-zero
docker compose down
docker volume rm agent-zero_agent-zero-data
docker compose up --build -d
```

After this one-time wipe, subsequent restarts work correctly without wiping — `cp -ru` handles incremental sync and bind mounts handle live-reload.

## Next Phase Readiness

- Phase 12 (Readiness Detection) can proceed: TmuxTool send/keys/read are confirmed working in the live container
- Any future tool added to `python/tools/` will automatically appear in `/a0/python/tools/` without a rebuild — live-reload is structural, not dependent on remembering to copy files
- Any future prompt added to `prompts/` will automatically appear in `/a0/prompts/` and be auto-registered via the `agent.system.tool.*.md` glob pattern

## Self-Check: PASSED

- FOUND: commit 793c6a4 — feat(11-02): add python/ and prompts/ bind mounts; fix copy_A0.sh sync logic
- FOUND: `./python:/a0/python` in docker-compose.yml (verified during task execution)
- FOUND: `./prompts:/a0/prompts` in docker-compose.yml (verified during task execution)
- FOUND: `cp -ru` in docker/run/fs/ins/copy_A0.sh (verified during task execution)
- Human-verify checkpoint: APPROVED — all four verification steps passed

---
*Phase: 11-tmux-primitive-infrastructure*
*Completed: 2026-02-25*
