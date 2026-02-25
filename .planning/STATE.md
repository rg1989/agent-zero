# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Agent Zero can build, run, and persist web applications directly within its own UI
**Current focus:** Phase 8 — Claude CLI Single-Turn + Env Fix (complete) → Phase 9 next

## Current Position

Phase: 8 of 10 (Claude CLI Single-Turn + Env Fix)
Plan: 1 of 1 in current phase (complete)
Status: Phase 8 complete — ready for Phase 9
Last activity: 2026-02-25 — Completed 08-01 (claude_cli.py single-turn helper with CLAUDECODE env fix)

Progress: [█████░░░░░] 40% (v1.0 complete; Phases 6-8 complete; v1.1 phases 9-10 remaining)

## Performance Metrics

**Velocity:**
- Total plans completed: 3 (v1.1)
- Average duration: 5.7 min
- Total execution time: 17 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 06-cdp-startup-health-check | 1 | 1min | 1min |
| 07-browser-navigate-with-verification | 1 | 2min | 2min |
| 08-claude-cli-single-turn-env-fix | 1 | 14min | 14min |
| v1.1 phases 9-10 | TBD | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

- Scope: Minimal-footprint approach — fix two files (`startup.sh`, `shared-browser/SKILL.md`), create one new file (`usr/skills/claude-cli/SKILL.md`), add `websocket-client>=1.9.0` to `requirements.txt`
- No new Tool classes; `code_execution_tool` + `TTYSession` are sufficient primitives for all CLAUDE features
- CLAUDECODE fix is per-subprocess env only (`env=` param), never globally unset
- Phase 8 (claude single-turn) has empirical validation flag: confirm exact ANSI sequences and prompt marker by running `claude` in PTY before coding detection logic
- [Phase 6] Use curl -sf on /json HTTP endpoint (not TCP port check) — HTTP confirms CDP serving, not just TCP bound
- [Phase 6] 0.5s interval x 20 attempts = 10s max — matches Chromium 1-3s Docker startup with generous headroom
- [Phase 6] kill -0 crash-early guard on every iteration — detect Chromium death immediately, not after full timeout
- [Phase 6] Leave sleep 1 cleanup guard untouched — different concern from the CDP readiness race condition
- [Phase 7] navigate_and_wait uses time.sleep(0.1) after Page.navigate to prevent false-positive from old page readyState
- [Phase 7] send() signature updated to send(ws, method, params) with explicit ws arg to enable try/finally cleanup pattern
- [Phase 7] Bare Page.navigate + time.sleep(2) pattern fully eliminated from SKILL.md — replaced with navigate_and_wait() everywhere
- [Phase 08-claude-cli-single-turn-env-fix]: Use subprocess.run capture_output=True (not PTY) for clean stdout; per-call env_clean dict for CLAUDECODE fix; claude_single_turn() with --output-format json; claude_single_turn_text() with --output-format text

### Pending Todos

None yet.

### Blockers/Concerns

- [RESOLVED - Phase 8] claude_single_turn() uses subprocess.run capture_output=True — avoids PTY entirely; prompt marker irrelevant for single-turn; ANSI stripping confirmed defensive only
- [Phase 9] Idle-timeout calibration for multi-turn requires profiling claude's natural pause durations (1-2s thinking pauses can trigger false "done" signals)
- [RESOLVED - Phase 7] `websocket-client>=1.9.0` added to requirements.txt — will be installed on Docker image rebuild

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed 08-01-PLAN.md (claude CLI single-turn helper)
Resume file: None
