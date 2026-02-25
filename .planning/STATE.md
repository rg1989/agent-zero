# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Agent Zero can build, run, and persist web applications directly within its own UI
**Current focus:** Phase 6 — CDP Startup Health-Check

## Current Position

Phase: 6 of 10 (CDP Startup Health-Check)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-02-25 — Roadmap created for v1.1 Reliability (phases 6-10)

Progress: [██░░░░░░░░] 20% (v1.0 complete; v1.1 phases 6-10 not started)

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (v1.1)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| v1.1 phases 6-10 | TBD | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

- Scope: Minimal-footprint approach — fix two files (`startup.sh`, `shared-browser/SKILL.md`), create one new file (`usr/skills/claude-cli/SKILL.md`), add `websocket-client>=1.9.0` to `requirements.txt`
- No new Tool classes; `code_execution_tool` + `TTYSession` are sufficient primitives for all CLAUDE features
- CLAUDECODE fix is per-subprocess env only (`env=` param), never globally unset
- Phase 8 (claude single-turn) has empirical validation flag: confirm exact ANSI sequences and prompt marker by running `claude` in PTY before coding detection logic

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 8] Claude CLI prompt marker string must be confirmed empirically (MEDIUM confidence) — run `claude` in PTY and inspect raw bytes with `repr()` or `xxd` before writing completion detection regex
- [Phase 9] Idle-timeout calibration for multi-turn requires profiling claude's natural pause durations (1-2s thinking pauses can trigger false "done" signals)
- [General] `websocket-client>=1.9.0` must be confirmed installable in Docker venv (`/opt/venv-a0`) — verify during Phase 7 setup

## Session Continuity

Last session: 2026-02-25
Stopped at: Roadmap written, ready to plan Phase 6
Resume file: None
