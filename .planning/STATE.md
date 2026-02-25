# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Agent Zero can build, run, and persist web applications directly within its own UI
**Current focus:** Phase 11 — tmux Primitive Infrastructure (v1.2 start)

## Current Position

Phase: 11 of 15 (tmux Primitive Infrastructure)
Plan: 0 of 1 in current phase
Status: Ready to plan
Last activity: 2026-02-25 — v1.2 roadmap created; phases 11-15 defined

Progress: [██████████░░░░░░░░░░] 50% (10/15 phases complete across all milestones; 0/5 v1.2 phases)

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (v1.2)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| — | — | — | — |

*Updated after each plan completion*

## Accumulated Context

### Decisions

- v1.2 architecture: New `tmux_tool` Python class for shared terminal interaction; `code_execution_tool` and `terminal_agent.py` left untouched
- Prompt detection strategy: prompt pattern first, idle timeout fallback (10s minimum for AI CLI response times)
- No sentinel injection: shared terminal is user-visible; only stability polling + prompt matching are allowed
- ANSI stripping required before any capture-pane parsing: `re.sub(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07)', '', text)`
- Phase 13 is empirical-first: must observe installed OpenCode binary before writing any detection regex
- OpenCode hang regression risk: v0.15+ confirmed to hang on process exit; must check `opencode --version` at Phase 13 start

### Carried from v1.1

- CLAUDECODE fix is per-subprocess env only — never globally unset
- `ClaudeSession` uses `--resume UUID` for multi-turn
- `websocket-client>=1.9.0` required in requirements.txt

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 13: OpenCode installed version unknown — hang regression (v0.15+) may require fallback to `opencode serve` HTTP mode; assess at planning time with `opencode --version`
- Phase 13: Run `/gsd:research-phase` before planning (flagged HIGH in SUMMARY.md)

## Session Continuity

Last session: 2026-02-25
Stopped at: v1.2 roadmap created — ready to plan Phase 11
Resume file: None
