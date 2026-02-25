---
phase: 06-cdp-startup-health-check
plan: 01
subsystem: infra
tags: [bash, chromium, cdp, startup, health-check, docker]

# Dependency graph
requires: []
provides:
  - "Deterministic CDP readiness poll in apps/shared-browser/startup.sh replacing fragile sleep 2"
  - "Diagnostic error messages on Chromium startup failure (timeout and crash-early paths)"
affects:
  - phase 7 (browser navigate-with-verification builds on reliable CDP connection)
  - shared-browser skill documentation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "bash until loop with curl -sf for CDP HTTP endpoint polling (20 x 0.5s = 10s max)"
    - "kill -0 $PID for process liveness without signaling"
    - "exit 1 with stderr diagnostic on startup failure — no silent hang"

key-files:
  created: []
  modified:
    - apps/shared-browser/startup.sh

key-decisions:
  - "Use curl -sf on /json HTTP endpoint (not TCP port check) — HTTP check confirms CDP is serving, not just TCP bound"
  - "0.5s interval x 20 attempts = 10s max timeout — matches Chromium 1-3s typical Docker startup with generous headroom"
  - "kill -0 crash-early guard on every iteration — detect Chromium death immediately, not after full timeout"
  - "Leave sleep 1 cleanup guard (before Chromium launch) untouched — different concern, not the race condition being fixed"
  - "No set +e wrapper needed — until is a conditional context, curl non-zero exit is safe inside it"

patterns-established:
  - "Startup readiness: poll HTTP endpoint, not sleep — until curl -sf http://localhost:PORT/endpoint > /dev/null 2>&1"
  - "Process guard: kill -0 $PID to detect crash-early inside wait loops"
  - "Startup failure: exit 1 with >&2 diagnostic message, never silent hang"

requirements-completed: [BROWSER-04]

# Metrics
duration: 1min
completed: 2026-02-25
---

# Phase 6 Plan 01: CDP Startup Health-Check Summary

**Bash CDP readiness poll (curl -sf /json, 20x0.5s) replaces fragile sleep 2 in shared-browser startup.sh, with crash-early detection and stderr diagnostics on failure**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-25T03:50:11Z
- **Completed:** 2026-02-25T03:51:13Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments

- Replaced `sleep 2` with deterministic `until curl -sf http://localhost:9222/json` polling loop (20 attempts x 0.5s = 10s max)
- Added `kill -0 $CHROMIUM_PID` crash-early guard on each iteration — Chromium death detected immediately instead of after full timeout
- Two `ERROR:` diagnostics to stderr: one for timeout, one for process death — eliminates silent hangs
- All changes pure bash, no new dependencies, `set -e` semantics preserved correctly via `until` conditional context

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace sleep 2 with CDP readiness poll in startup.sh** - `db4ba79` (fix)

## Files Created/Modified

- `apps/shared-browser/startup.sh` - Replaced `sleep 2` (line 42) with 18-line CDP poll block; structure: cleanup -> Chromium launch -> CDP poll -> Flask exec

## Decisions Made

- Used `curl -sf /json` (not `nc -z` TCP check) — TCP port can accept before CDP HTTP handler initializes, giving false positive
- 0.5s interval chosen as balance: no flood output, no apparent hang, Chromium typically starts in 1-3s in Docker
- `kill -0` over `ps` parsing — POSIX standard, zero-dependency, no fragile text parsing
- Left `sleep 1` (line 20, before Chromium launch) untouched — this is a cleanup timing guard for `pkill`/`fuser`, not the race condition being fixed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `grep -n "sleep 2"` check initially appeared to fail because grep matched the comment "(replaces sleep 2)" — verified with `^sleep 2$` exact-command grep that no `sleep 2` command line exists. All verification checks pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CDP readiness is now deterministic — Phase 7 (browser navigate-with-verification) can rely on the connection being ready when Flask starts
- The `until curl -sf` pattern established here can be referenced in shared-browser SKILL.md (Phase 7) as confirmation that CDP is pre-verified before agent connection

## Self-Check: PASSED

- FOUND: apps/shared-browser/startup.sh
- FOUND: .planning/phases/06-cdp-startup-health-check/06-01-SUMMARY.md
- FOUND: commit db4ba79 (task commit)
- FOUND: until curl -sf loop (1 match)
- FOUND: 2x kill -0 guards
- PASS: bash -n syntax check

---
*Phase: 06-cdp-startup-health-check*
*Completed: 2026-02-25*
