---
phase: quick-4
plan: 01
subsystem: extensions, skill
tags: [runtime-enforcement, skill-guidance, crud-app, extension-discovery]
dependency_graph:
  requires: []
  provides: [runtime-enforcement-reliable, crud-app-guidance]
  affects: [web-app-builder, code_execution_tool, extension-loading]
tech_stack:
  added: []
  patterns: [extension-discovery-via-python-root, targeted-template-customization]
key_files:
  created:
    - python/extensions/tool_execute_before/_20_enforce_skill_runtimes.py
  modified:
    - usr/skills/web-app-builder/SKILL.md
  deleted:
    - usr/extensions/tool_execute_before/_20_enforce_skill_runtimes.py
    - usr/extensions/tool_execute_before/ (directory)
    - usr/extensions/ (directory)
decisions:
  - "Move hook to python/extensions/ (default_root) rather than adding usr/extensions/ to discovery path"
  - "6-step crud-app customization guide prevents monolithic rewrites"
metrics:
  duration: "8 minutes"
  completed: "2026-03-03T05:24:26Z"
  tasks_completed: 2
  files_changed: 4
---

# Quick Task 4: Fix Remaining App Creation Errors Summary

**One-liner:** Moved runtime enforcement extension to guaranteed discovery path and added explicit 6-step crud-app customization guide to prevent template over-customization.

## What Was Done

### Task 1 — Move runtime enforcement hook to guaranteed discovery path

The `_20_enforce_skill_runtimes.py` extension was in `usr/extensions/tool_execute_before/` which is only discovered when `usr/` is added to the extension search path. The `python/extensions/` directory is always scanned via `default_root="python"`. Moving the file to `python/extensions/tool_execute_before/` ensures it always runs when the web-app-builder skill is active — regardless of user directory configuration.

The old file was deleted and the now-empty `usr/extensions/` directory tree was removed to avoid confusion.

**Commit:** `55e5c4b`

### Task 2 — Improve SKILL.md Step 5 crud-app guidance

The previous crud-app customization section was 3 bullet points — vague enough that agents often rewrote the entire `app.py` from scratch instead of making targeted edits. The new section:

1. Lists all 8 template files explicitly so the agent knows what exists
2. Adds a bold "DO NOT rewrite app.py or create new template files" directive
3. Provides a 6-step targeted customization guide: CREATE_TABLE_SQL, SQL queries, list.html, form.html, detail.html, entity rename via `sed`

This prevents wasted tokens from monolithic file rewrites that break routing, the `<base>` tag, mobile-responsive CSS, and other working infrastructure.

**Commit:** `0ec3797`

## Verification Results

1. Runtime hook file exists at `python/extensions/tool_execute_before/_20_enforce_skill_runtimes.py` — contains `EnforceSkillRuntimes` class and imports `Extension`
2. No stale copy at `usr/extensions/tool_execute_before/_20_enforce_skill_runtimes.py` — CLEAN
3. SKILL.md shows new guidance: "After copying, your app directory contains these files..."
4. SKILL.md Step 5 still has all 7 template subsections (flask-dashboard, flask-basic, static-html, dashboard-realtime, utility-spa, crud-app, file-tool)
5. `grep -c "DO NOT rewrite app.py"` returns 1
6. `grep -c "templates/list.html"` returns 2 (inventory line + customization step)
7. `grep "CREATE_TABLE_SQL"` appears in the crud-app customization step

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `python/extensions/tool_execute_before/_20_enforce_skill_runtimes.py` — FOUND
- `usr/skills/web-app-builder/SKILL.md` — modified with new content
- `55e5c4b` — FOUND (task 1 commit)
- `0ec3797` — FOUND (task 2 commit)
- Old file `usr/extensions/tool_execute_before/_20_enforce_skill_runtimes.py` — REMOVED
