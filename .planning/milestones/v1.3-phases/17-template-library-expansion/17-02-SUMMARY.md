---
phase: 17-template-library-expansion
plan: 02
subsystem: ui
tags: [flask, sqlite, crud, templates, python, jinja2]

# Dependency graph
requires: []
provides:
  - Full Flask+SQLite CRUD app template with Item model at apps/_templates/crud-app/
  - list/detail/create/edit/delete views for any data model
  - Dark-themed HTML templates with data-table, badge, form, and flash styles
  - Shared form.html pattern for create and edit (item=None vs item object)
affects: [17-guide-update, 18-skill-update]

# Tech tracking
tech-stack:
  added: [sqlite3 (stdlib), flask.g for per-request DB connection]
  patterns:
    - get_db()/close_db() pattern using flask.g for per-request SQLite connections
    - CREATE_TABLE_SQL as module-level constant with IF NOT EXISTS guard
    - Shared form template pattern (item=None for create, item object for edit)
    - data-confirm attribute pattern for JS delete confirmation without inline JS
    - Flash messages with category (success/error) rendered in base.html

key-files:
  created:
    - apps/_templates/crud-app/app.py
    - apps/_templates/crud-app/requirements.txt
    - apps/_templates/crud-app/templates/base.html
    - apps/_templates/crud-app/templates/list.html
    - apps/_templates/crud-app/templates/form.html
    - apps/_templates/crud-app/templates/detail.html
    - apps/_templates/crud-app/templates/404.html
    - apps/_templates/crud-app/static/style.css
    - apps/_templates/crud-app/static/app.js
  modified: []

key-decisions:
  - "404.html added (not in plan) — app.py references it for missing items; Rule 2 fix"
  - "btn class includes text-decoration:none for anchor tags used as buttons"
  - "actions-cell uses flexbox to align Edit/Delete side by side on wider screens"

patterns-established:
  - "CRUD template: get_db() returns g._database connection, close_db() tears it down"
  - "Parameterized SQL: all queries use ? placeholders, never f-strings with user input"
  - "Flash categories: 'success' (green left-border) and 'error' (red left-border)"
  - "Delete confirmation: data-confirm attribute on submit button, intercepted by app.js"

requirements-completed: [TMPL-03]

# Metrics
duration: 3min
completed: 2026-03-03
---

# Phase 17 Plan 02: CRUD App Template Summary

**Flask+SQLite CRUD template with Item model, 7 routes + 2 API endpoints, shared form pattern, dark-themed data-table, badge, and flash message styles**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T02:48:27Z
- **Completed:** 2026-03-03T02:51:05Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Flask app with SQLite CRUD integration, `get_db()`/`close_db()` helpers, and clearly-commented Item model definition section
- 7 CRUD routes (list, detail, new, create, edit, update, delete) + 2 API endpoints, all using parameterized SQL queries with flash messages
- 4 HTML templates (base with nav + flashes, list with data-table, shared form for create/edit, detail with card layout) plus a 404 template
- Dark theme CSS matching flask-basic with `.data-table`, `.badge` (active/inactive/archived), `.form-group`/`.form-control`, and `.flash` styles
- JS delete confirmation via `data-confirm` attribute pattern and flash auto-dismiss after 5 seconds

## Task Commits

1. **Task 1: Create crud-app template backend** - `6bf4590` (feat)
2. **Task 2: Create crud-app template frontend** - `6375045` (feat)

## Files Created/Modified

- `apps/_templates/crud-app/app.py` - Flask app with SQLite CRUD, Item model, 7 routes + 2 API endpoints
- `apps/_templates/crud-app/requirements.txt` - Comment about Flask pre-installed
- `apps/_templates/crud-app/templates/base.html` - Base layout with `<base>` tag, nav, flash messages block
- `apps/_templates/crud-app/templates/list.html` - Data table with item count, empty-state, delete confirmation
- `apps/_templates/crud-app/templates/form.html` - Shared create/edit form with pre-filled values
- `apps/_templates/crud-app/templates/detail.html` - Single item card with edit/delete/back actions
- `apps/_templates/crud-app/templates/404.html` - Not-found page for missing item IDs
- `apps/_templates/crud-app/static/style.css` - Dark theme with table, badge, form, flash, and detail styles
- `apps/_templates/crud-app/static/app.js` - Delete confirmation and flash auto-dismiss

## Decisions Made

- Added `404.html` template not explicitly listed in plan — `app.py` references it for missing items (Rule 2: missing critical functionality for correct error handling)
- Shared `form.html` uses `{% if item %}` throughout rather than two separate templates — reduces duplication and makes the pattern crystal clear for adaptation
- `btn` CSS class includes `text-decoration: none` so anchor tags styled as buttons work consistently with the existing button elements

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added 404.html template**
- **Found during:** Task 2 (frontend creation)
- **Issue:** app.py renders `404.html` for missing item IDs — template not listed in plan artifacts but required for app to function correctly
- **Fix:** Created `templates/404.html` extending base.html with empty-state message and back-to-list link
- **Files modified:** apps/_templates/crud-app/templates/404.html
- **Verification:** Template file exists; app.py `render_template("404.html", ...)` would not 500 on missing items
- **Committed in:** `6375045` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Auto-fix necessary for correct 404 handling. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- crud-app template complete and ready for Phase 18 (_GUIDE.md update to include all seven templates)
- Pattern established for SQLite-backed apps is clear and straightforward to adapt to different models

---
*Phase: 17-template-library-expansion*
*Completed: 2026-03-03*
