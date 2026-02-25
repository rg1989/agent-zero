# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Agent Zero can build, run, and persist web applications directly within its own UI
**Current focus:** Phase 12 — Readiness Detection (v1.2)

## Current Position

Phase: 11 of 15 (tmux Primitive Infrastructure)
Plan: 2 of 2 in current phase
Status: Phase 11 complete (both plans) — ready for Phase 12
Last activity: 2026-02-25 — Phase 11 Plan 02 executed; Docker deployment gap closed; TmuxTool verified end-to-end

Progress: [██████████░░░░░░░░░░] 53% (11/15 phases complete across all milestones; 2/5 v1.2 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 2 (v1.2)
- Average duration: 7 min
- Total execution time: 14 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 11-tmux-primitive-infrastructure | 2 | 14 min | 7 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

- v1.2 architecture: New `tmux_tool` Python class for shared terminal interaction; `code_execution_tool` and `terminal_agent.py` left untouched
- Prompt detection strategy: prompt pattern first, idle timeout fallback (10s minimum for AI CLI response times)
- No sentinel injection: shared terminal is user-visible; only stability polling + prompt matching are allowed
- ANSI stripping required before any capture-pane parsing: `re.sub(r'\x1b(?:\][^\x07]*\x07|[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)` — OSC branch must come FIRST (2-char branch range includes `]`)
- Phase 13 is empirical-first: must observe installed OpenCode binary before writing any detection regex
- OpenCode hang regression risk: v0.15+ confirmed to hang on process exit; must check `opencode --version` at Phase 13 start
- [Phase 11]: ANSI_RE OSC branch must precede 2-char branch: ] (0x5D) falls in \-_ range so ordering matters
- [Phase 11-02]: Docker live-reload pattern: bind mount ./python:/a0/python and ./prompts:/a0/prompts so tool/prompt changes reach container without rebuild; copy_A0.sh uses cp -ru (update-newer) without presence-check guard

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
Stopped at: Completed 11-02-PLAN.md — Phase 11 fully done (gap closure verified), ready for Phase 12
Resume file: None
