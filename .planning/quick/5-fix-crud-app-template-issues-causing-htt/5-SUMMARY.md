---
phase: quick-5
plan: 01
subsystem: web-app-builder
tags: [crud-app, template, skill, agent-comprehension, inline-comments]
dependency_graph:
  requires: []
  provides: [crud-app-customize-guidance, crud-app-template-markers]
  affects: [usr/skills/web-app-builder/SKILL.md, apps/_templates/crud-app/app.py]
tech_stack:
  added: []
  patterns: [inline-CUSTOMIZE-markers, worked-example-in-skill, explicit-file-inventory]
key_files:
  modified:
    - apps/_templates/crud-app/app.py
    - usr/skills/web-app-builder/SKILL.md
decisions:
  - "Templates remain GENERIC with items/name/description/status placeholders — bookshelf example goes in SKILL.md only"
  - "Removed dangerous blanket sed 's/items/yourentity/g' command that broke function names and route paths"
  - "Added WARNING block with NEVER keyword to maximally deter agents from rewriting from scratch"
metrics:
  duration: ~10 minutes
  completed: 2026-03-03
  tasks_completed: 2
  files_modified: 2
---

# Quick Task 5: Fix crud-app Template Issues Causing HTTP 500 Errors — Summary

## One-liner

Added CUSTOMIZE/DO NOT CHANGE inline markers to the generic crud-app template and rewrote SKILL.md Step 5 crud-app guidance with an explicit 6-step sequence, file inventory, and bookshelf worked example.

## What Was Done

### Task 1: CUSTOMIZE markers in crud-app template app.py (commit 545b8fb)

Added inline comment markers throughout `apps/_templates/crud-app/app.py` to make customization points unambiguous:

- **CUSTOMIZATION GUIDE block** at top of file explaining the marker system
- **`# DO NOT CHANGE`** on PORT and APP_NAME lines (proxy routing required)
- **`# CUSTOMIZE: change filename if desired`** on DATABASE line
- **`# CUSTOMIZE:`** block above CREATE_TABLE_SQL with instruction to keep `id` and `created_at`
- **`# CUSTOMIZE:`** comments in each CRUD route function above SQL queries (items_list, items_detail, items_create, items_update, items_delete, api_items_list, api_items_delete)
- **`# DO NOT CHANGE template names`** on all render_template() calls
- **`# DO NOT CHANGE — host must be 0.0.0.0 for proxy routing`** on app.run line

Result: 13 CUSTOMIZE markers, 10 DO NOT CHANGE markers. Zero changes to actual code logic.

### Task 2: SKILL.md crud-app Step 5 rewrite (commit ef48846)

Replaced the existing 10-line crud-app section in Step 5 with a comprehensive guide:

1. **WARNING block** — explicit "NEVER rewrite app.py or templates from scratch" with `NEVER` keyword
2. **File inventory** — lists all 8 template files (app.py, base.html, list.html, form.html, detail.html, 404.html, style.css, app.js, requirements.txt) with description of each
3. **6-step customization sequence** — explicit ordered steps: CREATE_TABLE_SQL, SQL queries, list.html, form.html, detail.html, display text
4. **Worked example (bookshelf)** — shows exact before/after for CREATE_TABLE_SQL, items_create route, and list.html table headers
5. **Removed dangerous sed command** — `sed -i 's/items/yourentity/g'` blanket replace was breaking function names, route paths, and template variable names
6. **Updated quick reference section** — crud-app entry now points to CUSTOMIZE markers and worked example

All other template sections (flask-dashboard, flask-basic, static-html, dashboard-realtime, utility-spa, file-tool) were left unchanged.

## Root Cause Addressed

The bookshelf agent failure occurred because:
1. SKILL.md guidance was too vague — agents couldn't understand what exactly to change
2. app.py had no visual markers distinguishing infrastructure code from customizable code
3. The dangerous blanket sed command encouraged wholesale text replacement instead of targeted edits
4. No concrete example showed what "edit the SQL queries" actually means in practice

## Verification Results

- `python3 -c "import ast; ast.parse(...)"` → SYNTAX OK (template code unchanged)
- `grep -c 'CUSTOMIZE:' apps/_templates/crud-app/app.py` → 13 (>= 6 required)
- `grep -c 'DO NOT CHANGE' apps/_templates/crud-app/app.py` → 10 (>= 3 required)
- `grep 'Worked example' usr/skills/web-app-builder/SKILL.md` → found
- `grep -c 'sed.*items/yourentity' usr/skills/web-app-builder/SKILL.md` → 0 (removed)
- `grep 'For .flask-dashboard' usr/skills/web-app-builder/SKILL.md` → present (unchanged)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files exist:
- apps/_templates/crud-app/app.py — FOUND
- usr/skills/web-app-builder/SKILL.md — FOUND
- .planning/quick/5-fix-crud-app-template-issues-causing-htt/5-SUMMARY.md — FOUND (this file)

Commits exist:
- 545b8fb — FOUND (feat(quick-5): add CUSTOMIZE/DO NOT CHANGE markers)
- ef48846 — FOUND (feat(quick-5): rewrite crud-app Step 5)
