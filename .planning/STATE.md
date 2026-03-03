# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-03)

**Core value:** Agent Zero can build, run, and persist web applications directly within its own UI
**Current focus:** Defining requirements for v1.3 App Builder

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-03 — Milestone v1.3 started

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (v1.3)

*Updated after each plan completion*

## Accumulated Context

### Decisions

- v1.2 architecture: New `tmux_tool` Python class for shared terminal interaction; `code_execution_tool` and `terminal_agent.py` left untouched
- Prompt detection strategy: prompt pattern first, idle timeout fallback (10s minimum for AI CLI response times)
- No sentinel injection: shared terminal is user-visible; only stability polling + prompt matching are allowed
- ANSI stripping required before any capture-pane parsing: `re.sub(r'\x1b(?:\][^\x07]*\x07|[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)` — OSC branch must come FIRST (2-char branch range includes `]`)

### Carried from v1.2

- CLAUDECODE fix is per-subprocess env only — never globally unset
- `ClaudeSession` uses `--resume UUID` for multi-turn
- `websocket-client>=1.9.0` required in requirements.txt

### Pending Todos

None yet.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-03
Stopped at: Starting milestone v1.3 App Builder
Resume file: None
