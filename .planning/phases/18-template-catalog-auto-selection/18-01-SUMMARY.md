---
phase: 18-template-catalog-auto-selection
plan: "01"
subsystem: app-templates
tags: [templates, catalog, decision-tree, documentation, flask, spa, crud, file-upload]

# Dependency graph
requires:
  - phase: 17-template-library-expansion
    provides: All 7 app templates (flask-basic, flask-dashboard, static-html, utility-spa, dashboard-realtime, crud-app, file-tool)

provides:
  - Machine-readable template catalog (_CATALOG.md) with structured metadata for all 7 templates
  - Updated decision tree in _GUIDE.md covering all 7 templates
  - pick_when criteria and use_cases for agent auto-selection

affects: [web-app-builder-skill, 18-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - YAML-in-markdown catalog format for machine-readable + human-readable template metadata
    - 7-branch decision tree (store-data -> backend? -> charts? -> SSE? -> files? -> tool?)

key-files:
  created:
    - apps/_templates/_CATALOG.md
  modified:
    - apps/_templates/_GUIDE.md

key-decisions:
  - "YAML-in-markdown catalog format chosen — parseable by the agent without a YAML parser, readable as plain text, consistent with existing _GUIDE.md markdown style"
  - "decision tree uses store-data as the first branch (crud-app is the biggest differentiator) then backend yes/no, then specialization depth"
  - "_GUIDE.md quick reference table added as header — gives a fast 7-row summary before the decision tree for scanning"

patterns-established:
  - "Template catalog entry format: name, description, use_cases (list), pick_when (string), start_command, has_backend (bool), has_database (bool), key_features (list)"

requirements-completed: [TMPL-05, TMPL-06]

# Metrics
duration: 2min
completed: 2026-03-03
---

# Phase 18 Plan 01: Template Catalog and Auto-Selection Guide Summary

**YAML-in-markdown template catalog (_CATALOG.md) with pick_when criteria and 7-branch decision tree in _GUIDE.md, covering all 7 app templates for agent auto-selection**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-03T03:14:24Z
- **Completed:** 2026-03-03T03:16:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- New `apps/_templates/_CATALOG.md` with structured YAML metadata for all 7 templates — each entry has name, description, use_cases, pick_when, start_command, has_backend, has_database, key_features
- `apps/_templates/_GUIDE.md` rewritten with a 7-branch decision tree, a quick reference table (all 7 templates with backend/DB columns), and full description sections for utility-spa, dashboard-realtime, crud-app, and file-tool
- Existing flask-basic, flask-dashboard, static-html sections and How-to/What-NOT sections preserved unchanged

## Task Commits

1. **Task 1: Create template catalog file** - `951b006` (feat)
2. **Task 2: Update _GUIDE.md decision tree for all 7 templates** - `633581d` (feat)

## Files Created/Modified

- `apps/_templates/_CATALOG.md` — New machine-readable catalog with YAML-in-markdown format; 7 template entries, each with use_cases list and pick_when criteria for agent selection
- `apps/_templates/_GUIDE.md` — Updated with 7-branch decision tree, quick reference table, and 4 new template description sections (utility-spa, dashboard-realtime, crud-app, file-tool)

## Decisions Made

1. **YAML-in-markdown format for _CATALOG.md** — Parseable by the agent as plain text without a YAML parser; human-readable in the terminal; consistent with the existing markdown docs in the project.

2. **decision tree: store-data as first branch** — `crud-app` is the most distinct template (only one with a database). Filtering it out first simplifies the remaining branches and reduces false positives from agents incorrectly picking flask-basic for DB apps.

3. **Quick reference table added to _GUIDE.md header** — A 7-row table with backend/DB flags gives the agent (and human) a fast scan before reading the full decision tree. Not in the original plan spec, but a natural addition that costs nothing and improves usability.

## Deviations from Plan

None - plan executed exactly as written. The quick reference table added to _GUIDE.md is a small enhancement (not replacing anything, just prepended before the decision tree) that improves scannability without altering the plan's requirements.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- _CATALOG.md and _GUIDE.md are complete and cover all 7 templates
- Phase 18 Plan 02 (if any) or the web-app-builder SKILL.md can now reference _CATALOG.md for agent-side template auto-selection
- All TMPL requirements completed: TMPL-02 (file-tool, 17-03), TMPL-03 (crud-app, 17-02), TMPL-04 (utility-spa + dashboard-realtime, 17-01), TMPL-05 (_CATALOG.md, this plan), TMPL-06 (_GUIDE.md update, this plan)

---
*Phase: 18-template-catalog-auto-selection*
*Completed: 2026-03-03*

## Self-Check: PASSED

All created/modified files confirmed present on disk. Both task commits (951b006, 633581d) confirmed in git history.
