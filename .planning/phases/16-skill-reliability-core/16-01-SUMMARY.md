---
phase: 16-skill-reliability-core
plan: 01
subsystem: skills
tags: [web-app-builder, skill, system-prompt, flask, validation, health-check]

# Dependency graph
requires: []
provides:
  - System prompt routing instruction directing agent to load web-app-builder skill for any app creation request
  - web-app-builder SKILL.md v3.0.0 with mandatory 8-step creation sequence
  - App name validation with regex and reserved name blocklist (runnable bash)
  - Post-start HTTP health poll loop (curl -sf, 10s timeout) with HEALTHY/FAILED branches
  - All reserved proxy paths documented in skill (matches app_proxy.py _RESERVED exactly)
affects: [17-template-library, 18-guide-and-polish, web-app-builder skill consumers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MANDATORY SEQUENCE pattern: numbered steps with explicit STOP-on-failure gates"
    - "Name validation before resource allocation prevents wasted work"
    - "HTTP poll health check before declaring success (curl -sf loop, 0.5s sleep, 20 iterations)"

key-files:
  created: []
  modified:
    - prompts/agent.system.main.tips.md
    - usr/skills/web-app-builder/SKILL.md

key-decisions:
  - "Rewrite SKILL.md entirely (v2 -> v3) rather than patching — v2 had structural gaps making reliable app creation impossible"
  - "Name validation goes first (Step 1) before any resource allocation — fail fast, no cleanup needed"
  - "Health check uses curl -sf in a bash loop (20 x 0.5s) — shell-native, no Python imports required"
  - "Reserved names list in skill must exactly match app_proxy.py _RESERVED (minus empty string) plus built-in app names as a separate group"
  - "System prompt instruction uses terse imperative style matching existing tips file format"

patterns-established:
  - "Skill MANDATORY SEQUENCE: numbered steps, each with explicit failure handling and STOP language"
  - "Reserved name validation: blocklist bash command the agent runs before any work begins"
  - "Health check before success: agent must receive HTTP 200 before telling user app is ready"

requirements-completed: [SKILL-01, SKILL-02, SKILL-03, SKILL-04]

# Metrics
duration: 15min
completed: 2026-03-03
---

# Phase 16 Plan 01: Skill Reliability Core Summary

**System prompt routes all app creation to web-app-builder; SKILL.md v3.0.0 enforces mandatory 8-step sequence with name validation (regex + reserved blocklist) and HTTP health poll before declaring success**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-03T02:30:00Z
- **Completed:** 2026-03-03T02:45:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added "## Apps System" section to `prompts/agent.system.main.tips.md` — agent now explicitly directed to load web-app-builder skill before any app creation, with ad-hoc Flask scripts prohibited
- Rewrote `usr/skills/web-app-builder/SKILL.md` from v2.0.0 to v3.0.0 with MANDATORY SEQUENCE of 8 ordered steps
- Step 1 validates app name format (regex `^[a-z][a-z0-9-]{1,28}[a-z0-9]$`) and checks against all 17 proxy-reserved names plus 2 built-in app names with a runnable bash command
- Step 8 health check polls HTTP port with `curl -sf` in a 20-iteration loop (0.5s sleep = 10s max) and branches on HEALTHY/FAILED with distinct user-facing messages
- All steps include explicit "STOP and report" failure handling — no silent failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Add app creation routing instruction to system prompt** - `1069e78` (feat)
2. **Task 2: Rewrite SKILL.md with mandatory sequence, name validation, and health check** - `1b54a76` (feat)

## Files Created/Modified

- `prompts/agent.system.main.tips.md` - Added "## Apps System" section with skills_tool:load instruction and ad-hoc script prohibition
- `usr/skills/web-app-builder/SKILL.md` - Complete rewrite to v3.0.0 with 8-step MANDATORY SEQUENCE

## Decisions Made

- Rewrite SKILL.md entirely (v2 to v3) rather than patching — v2 had no name validation, no health check, combined register+start as one step, and used underscore-based naming examples that violated the actual naming rules
- Name validation goes first (Step 1) before any resource allocation — fail fast principle, no cleanup needed if name is invalid
- Health check uses `curl -sf` in a bash loop rather than Python socket — shell-native, no imports, directly testable by the agent in the same shell context
- Reserved names list in skill exactly matches `app_proxy.py` `_RESERVED` (minus empty string) to prevent stale documentation drift; built-in app names listed separately as "occupied" to distinguish from proxy-enforced blocks
- System prompt instruction written in terse imperative style matching the existing tips file format (no full sentences, compressed phrasing)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - both files had clear, well-scoped requirements.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 16-01 complete: system prompt routing + reliable skill document in place
- Phase 17 (template library) can now proceed independently — it adds new templates the skill's Step 2 table will reference
- Phase 18 (guide and polish) depends on both Phase 16 and Phase 17 being complete
- No blockers

---
*Phase: 16-skill-reliability-core*
*Completed: 2026-03-03*
