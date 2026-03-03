---
phase: quick-5
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - usr/skills/web-app-builder/SKILL.md
  - apps/_templates/crud-app/app.py
autonomous: true
requirements: [QUICK-5]

must_haves:
  truths:
    - "SKILL.md crud-app guidance provides explicit step-by-step customization that prevents agents from rewriting files from scratch"
    - "crud-app template app.py has detailed inline comments explaining what to change and what NOT to change"
    - "SKILL.md crud-app section includes a concrete worked example (e.g. bookshelf) showing exact sed/python commands"
  artifacts:
    - path: "usr/skills/web-app-builder/SKILL.md"
      provides: "Explicit crud-app customization guidance with worked example"
      contains: "NEVER rewrite app.py from scratch"
    - path: "apps/_templates/crud-app/app.py"
      provides: "Enhanced inline comments marking customization points"
      contains: "CUSTOMIZE:"
  key_links:
    - from: "usr/skills/web-app-builder/SKILL.md"
      to: "apps/_templates/crud-app/app.py"
      via: "Step 5 references exact line patterns and file structure"
      pattern: "CREATE_TABLE_SQL|CRUD Routes"
---

<objective>
Fix crud-app template issues that cause HTTP 500 errors during app creation.

Purpose: When agents use the crud-app template, they ignore the template files and rewrite from scratch — creating template name mismatches (renders index.html instead of list.html), missing the flask.g database pattern, and breaking the base.html layout. The root cause is that SKILL.md Step 5 guidance for crud-app is too vague, and the template's app.py lacks clear "change THIS, don't touch THAT" markers. The template code itself is correct — the problem is agent comprehension.

Output: Updated SKILL.md with explicit crud-app customization guide including a worked example, and enhanced app.py with inline CUSTOMIZE markers at every change point.
</objective>

<execution_context>
@/Users/rgv250cc/.claude/get-shit-done/workflows/execute-plan.md
@/Users/rgv250cc/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@usr/skills/web-app-builder/SKILL.md
@apps/_templates/crud-app/app.py
@apps/_templates/crud-app/templates/list.html
@apps/_templates/crud-app/templates/form.html
@apps/_templates/crud-app/templates/detail.html
@apps/_templates/crud-app/templates/base.html

Also read (for understanding what went wrong):
@apps/bookshelf/app.py (the FAILED app — agent rewrote from scratch instead of customizing template)
@apps/bookshelf/templates/index.html (agent created this instead of using template's list.html/form.html/detail.html)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add CUSTOMIZE markers to crud-app template app.py</name>
  <files>apps/_templates/crud-app/app.py</files>
  <action>
Add explicit `# CUSTOMIZE:` comment markers at every point the agent should modify, and `# DO NOT CHANGE` markers at infrastructure code that must stay. This makes it impossible to misunderstand what to change.

Specific changes to app.py:

1. Above the docstring at top of file, add a block comment:
```
# ============================================================
# CUSTOMIZATION GUIDE
# Lines marked "# CUSTOMIZE:" → change these for your entity
# Lines marked "# DO NOT CHANGE" → required for routing/proxy
# Everything else → leave as-is unless you know what you're doing
# ============================================================
```

2. Mark the `DATABASE` line with `# CUSTOMIZE: change filename if desired`

3. Mark the `CREATE_TABLE_SQL` block with:
```python
# CUSTOMIZE: Change table name, column names, and types below.
# Keep 'id INTEGER PRIMARY KEY AUTOINCREMENT' and 'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'.
```

4. Mark PORT and APP_NAME lines with `# DO NOT CHANGE — required for proxy routing`

5. In each CRUD route function, add a `# CUSTOMIZE:` comment above the SQL query explaining what to change:
   - `items_list`: `# CUSTOMIZE: change "items" to your table name`
   - `items_detail`: `# CUSTOMIZE: change "items" to your table name`
   - `items_create`: `# CUSTOMIZE: change column names in INSERT to match your CREATE_TABLE_SQL`
   - `items_update`: `# CUSTOMIZE: change column names in UPDATE to match your CREATE_TABLE_SQL`
   - `items_delete`: `# CUSTOMIZE: change "items" to your table name`
   - `render_template` calls: `# DO NOT CHANGE template names — list.html, form.html, detail.html, 404.html must match files in templates/`

6. Add a comment above the `app.run` line: `# DO NOT CHANGE — host must be 0.0.0.0 for proxy routing`

Do NOT change any actual code logic — only add/modify comments.
  </action>
  <verify>
Run: `python3 -c "import ast; ast.parse(open('apps/_templates/crud-app/app.py').read()); print('SYNTAX OK')"` to verify Python syntax is valid.
Run: `grep -c 'CUSTOMIZE:' apps/_templates/crud-app/app.py` — should return at least 6.
Run: `grep -c 'DO NOT CHANGE' apps/_templates/crud-app/app.py` — should return at least 3.
  </verify>
  <done>crud-app app.py has clear CUSTOMIZE and DO NOT CHANGE markers at every customization point, with zero changes to actual code logic.</done>
</task>

<task type="auto">
  <name>Task 2: Rewrite SKILL.md crud-app Step 5 with explicit customization guide and worked example</name>
  <files>usr/skills/web-app-builder/SKILL.md</files>
  <action>
Replace the existing `**For crud-app:**` section in Step 5 (lines 221-231 approximately) with a much more explicit guide. The new section must:

1. Start with a WARNING block:
```
**For `crud-app` — READ THIS CAREFULLY:**

**WARNING:** The #1 failure mode is rewriting app.py or templates from scratch. NEVER do this.
The template already has working CRUD routes, database helpers, flash messages, error handling, and 4 HTML templates (list.html, form.html, detail.html, 404.html). Your job is to make SMALL TARGETED EDITS to adapt the "Item" model to the user's entity.
```

2. List the files that exist and MUST NOT be deleted or recreated:
```
After copying, your app directory has these files — do NOT create, delete, or rewrite any:
- `app.py` — Flask server with CRUD routes (look for `# CUSTOMIZE:` markers)
- `templates/base.html` — shared layout with topbar, flash messages, CSS/JS includes
- `templates/list.html` — data table listing all records
- `templates/form.html` — create/edit form (shared, uses item=None for create)
- `templates/detail.html` — single record detail view
- `templates/404.html` — not-found page
- `static/style.css` — dark theme styles
- `static/app.js` — delete confirmation, flash dismiss
- `requirements.txt` — Flask dependency
```

3. Provide the exact 6-step customization sequence:
```
**Customization steps (do ALL 6 in order):**

1. **Edit `CREATE_TABLE_SQL` in app.py** — change the table name and columns.
   Find the line `CREATE TABLE IF NOT EXISTS items (` and change `items` to your entity (plural).
   Replace the column definitions (keep `id` and `created_at`).

2. **Update SQL in route functions** — in each route function in app.py, update:
   - Table name in every SQL query (e.g., `items` → `books`)
   - Column names in INSERT and UPDATE queries to match your new columns
   - Column names in `request.form.get(...)` calls to match your form fields

3. **Update `templates/list.html`** — change:
   - Table header `<th>` labels to your column names
   - `{{ item.fieldname }}` references to your column names
   - Keep the `{% for item in items %}` loop variable name as `item`

4. **Update `templates/form.html`** — change:
   - Form field labels and `name=` attributes to your columns
   - `{{ item.fieldname }}` references in value attributes

5. **Update `templates/detail.html`** — change:
   - `<dt>` labels and `{{ item.fieldname }}` references to your columns

6. **Update display text** — change "Item"/"Items" in page titles and headings:
   Use targeted sed: `sed -i 's/Items/Books/g; s/Item/Book/g; s/item/book/g' templates/*.html`
   Then manually check app.py flash messages and route docstring.
```

4. Add a **WORKED EXAMPLE** showing a bookshelf app:
```
**Worked example — Bookshelf app:**

Step 1: Edit CREATE_TABLE_SQL in app.py:
```python
# Change from:
CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT,
    status      TEXT    DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
# Change to:
CREATE TABLE IF NOT EXISTS books (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    author      TEXT    NOT NULL,
    genre       TEXT    DEFAULT 'fiction',
    rating      INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

Step 2: Update SQL queries — example for items_create route:
```python
# Change from:
name        = request.form.get("name", "").strip()
description = request.form.get("description", "").strip()
status      = request.form.get("status", "active")
# ...
"INSERT INTO items (name, description, status) VALUES (?, ?, ?)",
(name, description, status),

# Change to:
title  = request.form.get("title", "").strip()
author = request.form.get("author", "").strip()
genre  = request.form.get("genre", "fiction")
rating = int(request.form.get("rating", 0))
# ...
"INSERT INTO books (title, author, genre, rating) VALUES (?, ?, ?, ?)",
(title, author, genre, rating),
```

Step 3: Update list.html table headers + cells:
```html
<!-- Change: -->
<th>Name</th><th>Status</th>
{{ item.name }}  {{ item.status }}
<!-- To: -->
<th>Title</th><th>Author</th><th>Genre</th>
{{ item.title }}  {{ item.author }}  {{ item.genre }}
```
```

5. Remove the old `sed -i 's/items/yourentity/g; s/item/yourentity/g'` advice entirely — it is dangerous because it changes function names, route paths, and template variable names indiscriminately.

6. Also update the "Template customization quick reference" section at the bottom of the file to match the new guidance. Replace the `crud-app` entry with:
```
**`crud-app`** — data management app:
- Look for `# CUSTOMIZE:` markers in `app.py` — change table name, columns, form fields
- Template has 4 HTML files (list/form/detail/404) — update field references, do NOT delete or recreate
- Routes handle list/detail/create/edit/delete; update SQL queries to match your columns
- See the worked example in Step 5 above for a complete walkthrough
```

IMPORTANT: Keep all other template sections (flask-dashboard, flask-basic, static-html, dashboard-realtime, utility-spa, file-tool) exactly as they are. Only modify the crud-app parts.
  </action>
  <verify>
Run: `grep -c 'NEVER' usr/skills/web-app-builder/SKILL.md` — should find the WARNING about never rewriting.
Run: `grep -c 'CUSTOMIZE:' usr/skills/web-app-builder/SKILL.md` — confirms CUSTOMIZE markers referenced.
Run: `grep 'Worked example' usr/skills/web-app-builder/SKILL.md` — confirms worked example exists.
Run: `grep -c 'sed.*items/yourentity' usr/skills/web-app-builder/SKILL.md` — should return 0 (dangerous sed removed).
  </verify>
  <done>SKILL.md Step 5 crud-app section has explicit 6-step customization guide with WARNING against rewriting, a complete worked example (bookshelf), and no dangerous blanket sed commands. Other template sections unchanged.</done>
</task>

</tasks>

<verification>
1. `python3 -c "import ast; ast.parse(open('apps/_templates/crud-app/app.py').read()); print('OK')"` — template still valid Python
2. `grep -c 'CUSTOMIZE:' apps/_templates/crud-app/app.py` >= 6 — markers present
3. `grep 'Worked example' usr/skills/web-app-builder/SKILL.md` — worked example present
4. `grep -c 'sed.*items/yourentity' usr/skills/web-app-builder/SKILL.md` == 0 — dangerous sed removed
5. Verify no other template sections were accidentally modified: `grep 'For .flask-dashboard' usr/skills/web-app-builder/SKILL.md` still exists
</verification>

<success_criteria>
- crud-app template app.py has CUSTOMIZE and DO NOT CHANGE markers at every customization point
- SKILL.md Step 5 has explicit 6-step crud-app customization guide
- SKILL.md includes a worked "bookshelf" example showing exact before/after code changes
- The dangerous `sed -i 's/items/yourentity/g'` advice is removed
- All other template guidance sections remain unchanged
- Template app.py still passes Python syntax check
</success_criteria>

<output>
After completion, create `.planning/quick/5-fix-crud-app-template-issues-causing-htt/5-SUMMARY.md`
</output>
