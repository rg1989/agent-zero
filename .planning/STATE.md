# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-03)

**Core value:** Agent Zero can build, run, and persist web applications directly within its own UI
**Current focus:** v1.3 App Builder -- Phase 18 (Template Catalog Auto-Selection)

## Current Position

Phase: 18 of 18 (Template Catalog Auto-Selection)
Plan: 1 of 1 in current phase
Status: Phase 18 Plan 1 complete
Last activity: 2026-03-03 -- Completed 18-01: template catalog (_CATALOG.md) + updated _GUIDE.md decision tree for all 7 templates

Progress: [█████████░] 90%

## Performance Metrics

**Velocity:**
- Total plans completed: 5 (v1.3)

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 16-skill-reliability-core | 01 | 15min | 2 | 2 |
| 17-template-library-expansion | 01 | 5min | 2 | 5 |
| 17-template-library-expansion | 02 | 3min | 2 | 9 |
| 17-template-library-expansion | 03 | 3min | 2 | 6 |
| 18-template-catalog-auto-selection | 01 | 2min | 2 | 2 |

*Updated after each plan completion*

## Accumulated Context

### Decisions

- v1.3 phase structure: 3 phases (16-18). Phases 16 and 17 are independent (can run in parallel). Phase 18 depends on both.
- Existing web-app-builder SKILL.md exists but is unreliable -- Phase 16 is a rewrite, not a patch
- Three templates already exist (flask-basic, flask-dashboard, static-html) -- Phase 17 adds four more
- _GUIDE.md already exists -- Phase 18 updates it to cover all seven templates
- [16-01] Rewrote SKILL.md entirely (v2->v3) rather than patching -- v2 had no name validation, no health check, underscore examples
- [16-01] Name validation goes first (Step 1) before resource allocation -- fail fast, no cleanup needed
- [16-01] Health check uses curl -sf bash loop (20x0.5s) -- shell-native, no Python imports required
- [16-01] Reserved names list in skill exactly matches app_proxy.py _RESERVED to prevent documentation drift
- [17-01] utility-spa uses serve.py static pattern + vanilla JS (no framework); dashboard-realtime uses SSE primary + polling fallback, 3 Chart.js charts (line/bar/doughnut)
- [17-02] crud-app template: Flask + SQLite with full REST CRUD, dark-theme data-table, shared form pattern (item=None/item), get_db()/close_db() via flask.g, parameterized SQL, 404.html added for correct error handling
- [17-03] file-tool template: multipart upload, format conversion pipeline, drag-and-drop UI, file-card grid
- [18-01] YAML-in-markdown catalog format: parseable as plain text, no parser required, human-readable in terminal
- [18-01] decision tree: store-data as first branch (crud-app is most distinct — only one with DB); then backend yes/no, then specialization
- [18-01] Quick reference table added to _GUIDE.md header (not in plan spec): 7-row table with backend/DB flags for fast scanning

### Carried from v1.2

- CLAUDECODE fix is per-subprocess env only -- never globally unset
- `ClaudeSession` uses `--resume UUID` for multi-turn
- `websocket-client>=1.9.0` required in requirements.txt

### Pending Todos

None yet.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-03
Stopped at: Completed 18-01-PLAN.md (template catalog + _GUIDE.md update for all 7 templates)
Resume file: None
