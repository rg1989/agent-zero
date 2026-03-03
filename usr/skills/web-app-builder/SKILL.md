---
name: "web-app-builder"
description: "Build, deploy, and manage local web applications within Agent Zero. Use when the user asks to build a dashboard, visualisation, web app, or anything best served as a browser-based interface. Apps are served at localhost:50000/{app_name}/ with no extra port forwarding required."
version: "3.0.0"
author: "Agent Zero"
tags: ["webapp", "dashboard", "visualisation", "flask", "server", "deploy", "monitor", "apps"]
trigger_patterns:
  # App creation - broad patterns (word "app" in context of building)
  - " app"
  - "webapp"
  - "web app"
  - "web tool"
  - "web interface"
  # App types
  - "dashboard"
  - "visualise"
  - "visualize"
  - "tracker"
  - "manager"
  - "monitor"
  - "viewer"
  - "browser-based"
  - "bookshelf"
  # Management
  - "start the app"
  - "stop the app"
  - "restart the app"
  - "list my apps"
  - "show my apps"
  - "app status"
  - "my apps"
---

# Web App Builder

CRITICAL: Follow the MANDATORY SEQUENCE below exactly. Do NOT skip steps. If any step fails, STOP and report the failure to the user — never proceed with a broken app.

---

## TOOL USAGE — READ THIS FIRST

All bash commands in this skill MUST be executed using `code_execution_tool` with `runtime: "terminal"`.

DO NOT use `runtime: "python"` for any step. DO NOT import any Python modules (there is no `python.helpers.webapp_manager` or `python/helpers/webapp.py`). The webapp API is HTTP-only — all interactions use `curl` commands via the terminal.

Correct tool call format for every bash step:
~~~json
{
    "thoughts": ["Executing step N of web-app-builder skill..."],
    "headline": "Step N: <description>",
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "terminal",
        "session": 0,
        "reset": false,
        "code": "<bash commands from the step>"
    }
}
~~~

---

## EXECUTION FLOW — DO NOT STOP

Execute ALL 8 steps in a single uninterrupted sequence. After announcing your template selection in Step 2, IMMEDIATELY proceed to Step 3 (allocate port) in the same response. Do NOT wait for user confirmation between steps.

The only acceptable reasons to stop mid-sequence are:
- A step returns an error (STOP and report it)
- The app name is invalid or reserved in Step 1 (STOP and ask for a new name)

Do NOT stop to ask "shall I proceed?" or "would you like me to continue?" — just execute.

---

## How routing works

```
Browser → localhost:50000/{app_name}/... → (proxy inside container) → localhost:{PORT}/...
```

The proxy is built into Agent Zero's server. You just start the app on any port in 9000–9099. No extra port forwarding needed. Apps persist across Docker rebuilds.

---

## MANDATORY SEQUENCE

Every app creation MUST follow these steps in order. No step may be skipped.

---

### Step 1 — Validate the app name

Before anything else, validate the chosen name:

**Rules:**
- Lowercase letters, digits, and hyphens only (regex: `^[a-z][a-z0-9-]{0,28}[a-z0-9]$`)
- Minimum 2 characters, maximum 30 characters
- Must start with a letter, must end with a letter or digit
- No underscores (use hyphens instead)

**Proxy-reserved names (blocked by `app_proxy.py` `_RESERVED`) — MUST NOT be used:**
`login`, `logout`, `health`, `dev-ping`, `socket.io`, `static`, `message`, `poll`, `settings_get`, `settings_set`, `csrf_token`, `chat_create`, `chat_load`, `upload`, `webapp`, `mcp`, `a2a`

**Built-in app names (occupied by core apps) — also avoid:**
`shared-browser`, `shared-terminal`

**Validation command (run this before proceeding):**
```bash
APP_NAME="chosen-name"
# Check format
echo "$APP_NAME" | grep -qP '^[a-z][a-z0-9-]{0,28}[a-z0-9]$' && echo "VALID" || echo "INVALID: must be lowercase alphanumeric + hyphens, 2-30 chars, start with letter"
# Check not reserved or occupied
BLOCKED="login logout health dev-ping socket.io static message poll settings_get settings_set csrf_token chat_create chat_load upload webapp mcp a2a shared-browser shared-terminal"
echo "$BLOCKED" | tr ' ' '\n' | grep -qx "$APP_NAME" && echo "BLOCKED: choose a different name" || echo "NAME AVAILABLE"
```

If the name is INVALID or RESERVED, tell the user and ask for a different name. Do NOT proceed.

---

### Step 2 — Auto-select a template

1. **Read the template catalog:** Read `/a0/apps/_templates/_CATALOG.md` for the full list of templates with descriptions, use cases, and selection criteria. Also read `/a0/apps/_templates/_GUIDE.md` for the decision tree if you need more detail.

2. **Match the user's request to a template** using this priority order:
   - If the user explicitly names a template (e.g., "use the crud-app template"), use that template
   - Otherwise, match based on keywords in the user's request:

   | Keywords / signals in request | Template | Start command |
   |-------------------------------|----------|---------------|
   | "database", "CRUD", "records", "items", "manage data", "list/edit/delete" | `crud-app` | `python app.py` |
   | "real-time", "live", "streaming", "SSE", "multiple charts" | `dashboard-realtime` | `python app.py` |
   | "dashboard", "metrics", "monitoring", "charts" | `flask-dashboard` | `python app.py` |
   | "upload", "download", "files", "convert", "file manager" | `file-tool` | `python app.py` |
   | "calculator", "converter", "text tool", "utility", "simple tool" | `utility-spa` | `python serve.py` |
   | "visualization", "D3", "Plotly", "static page", "no backend" | `static-html` | `python serve.py` |
   | General web app, forms, pages, custom API, or unclear | `flask-basic` | `python app.py` |

   If the request is ambiguous, default to `flask-basic` (most flexible).

3. **Tell the user your selection:** Before proceeding to Step 3, always say something like:
   > "I'll use the **{template-name}** template for this — it's the best fit because {brief reason}. If you'd prefer a different template, just let me know."
   Then immediately continue to Step 3 without waiting for user input. Only stop if the user actively interrupts.

4. **Handle override:** If the user asks to use a different template (now or later):
   - Acknowledge the change
   - Switch to the requested template
   - Continue from Step 3 (allocate port) — do NOT restart from Step 1

---

### Step 3 — Allocate a port

```bash
# Use code_execution_tool with runtime: "terminal" for this command
PORT=$(curl -s "http://localhost/webapp?action=alloc_port" | python3 -c "import sys,json; print(json.load(sys.stdin)['port'])")
echo "Allocated port: $PORT"
```

If this fails or returns empty, STOP and report the error.

---

### Step 4 — Copy the template

```bash
cp -r /a0/apps/_templates/{TEMPLATE} /a0/apps/{APP_NAME}
```

Verify the copy succeeded:
```bash
ls /a0/apps/{APP_NAME}/app.py || ls /a0/apps/{APP_NAME}/serve.py
```

If the directory doesn't exist or is empty, STOP and report the error.

**Install dependencies:**
```bash
pip3 install --break-system-packages -q -r /a0/apps/{APP_NAME}/requirements.txt 2>/dev/null || true
```

This ensures Flask and any extra packages the template needs are available. Always run this after copying.

---

### Step 5 — Customize the app

Edit the copied template files **in place** using small targeted changes (sed, python string replace, or read-modify-write). Do NOT rewrite entire files from scratch — the templates already have working HTML, CSS, routing, and responsive layouts. Only change what needs to change (model fields, titles, data sources, labels).

Key rules that MUST NOT change:
- Always `host="0.0.0.0"` (not 127.0.0.1)
- Always read port from env: `PORT = int(os.environ.get("PORT", 9000))`
- Always read app name from env: `APP_NAME = os.environ.get("APP_NAME", "")`
- Always use relative asset URLs (the `<base>` tag handles sub-path routing)
- Never hardcode port numbers
- **Mobile-responsive**: Keep the viewport meta tag, media queries, and flexible layouts from the template. All apps MUST work on mobile screens. Use `max-width` containers, CSS Grid/Flexbox, and test that nothing overflows on narrow viewports.

**For `flask-dashboard`:**
- `app.py` → replace the sample data in `/api/data` with real data (files, psutil, DB, etc.)
- `templates/index.html` → change the title, add/remove metric cards or chart datasets

**For `flask-basic`:**
- `app.py` → add your routes and logic
- `templates/index.html` → replace the content section

**For `static-html`:**
- `app.js` → replace `DATA` with real data or a fetch call
- `index.html` → swap Chart.js CDN for D3/Plotly if needed

**For `dashboard-realtime`:**
- `app.py` → edit `generate_data()` to produce your metrics/chart data
- SSE streams every 2s; adjust interval in the generator loop
- Three chart types available: line, bar, doughnut

**For `utility-spa`:**
- `app.js` → replace transform functions with your tool logic
- Layout: textarea input, action buttons, output area
- Start command is `python serve.py` (not `app.py`)

**For `crud-app` — READ THIS CAREFULLY:**

**WARNING:** The #1 failure mode is rewriting app.py or templates from scratch. NEVER do this.
The template already has working CRUD routes, database helpers, flash messages, error handling, and 4 HTML templates (list.html, form.html, detail.html, 404.html). Your job is to make SMALL TARGETED EDITS to adapt the "Item" model to the user's entity.

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

**For `file-tool`:**
- `app.py` → edit `ALLOWED_EXTENSIONS` and `MAX_CONTENT_LENGTH` for your needs
- Add conversions: extend `CONVERSIONS` dict in `app.py` + `CONVERT_OPTIONS` in `app.js`
- Uploads stored in `uploads/` directory (auto-created)

---

### Step 6 — Register the app

```bash
curl -s -X POST http://localhost/webapp \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"register\",\"name\":\"{APP_NAME}\",\"port\":$PORT,\"cmd\":\"{START_CMD}\",\"cwd\":\"/a0/apps/{APP_NAME}\",\"description\":\"{DESCRIPTION}\"}"
```

Check the response for `"error"` — if present, STOP and report it.

---

### Step 7 — Start the app

```bash
curl -s -X POST http://localhost/webapp \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"start\",\"name\":\"{APP_NAME}\"}"
```

Check the response for `"error"` — if present, STOP and report it.

---

### Step 8 — Verify the app is running (REQUIRED)

Poll the app's port until it responds. Do NOT skip this step.

```bash
# Wait up to 10 seconds for the app to start responding
for i in $(seq 1 20); do
  if curl -sf -o /dev/null "http://127.0.0.1:$PORT/"; then
    echo "HEALTHY: App is responding on port $PORT"
    break
  fi
  if [ "$i" -eq 20 ]; then
    echo "FAILED: App not responding after 10 seconds"
    echo "Check logs or process status:"
    echo "  ps aux | grep '$APP_NAME'"
    echo "  curl -v http://127.0.0.1:$PORT/"
  fi
  sleep 0.5
done
```

- If HEALTHY: Tell the user the app is live at `localhost:50000/{APP_NAME}/` and open it with `open_app`.
- If FAILED: Tell the user the app failed to start. Check for Python errors, port conflicts, or missing dependencies. Do NOT say "your app is ready".

---

## Management commands

All via `POST http://localhost/webapp` with JSON body, or GET for reads.

```bash
# List all apps
curl -s "http://localhost/webapp?action=list"

# Stop
curl -s -X POST http://localhost/webapp -H "Content-Type: application/json" \
  -d '{"action":"stop","name":"my-app"}'

# Restart
curl -s -X POST http://localhost/webapp -H "Content-Type: application/json" \
  -d '{"action":"restart","name":"my-app"}'

# Enable autostart (survives container restarts)
curl -s -X POST http://localhost/webapp -H "Content-Type: application/json" \
  -d '{"action":"autostart","name":"my-app","enabled":true}'

# Remove
curl -s -X POST http://localhost/webapp -H "Content-Type: application/json" \
  -d '{"action":"remove","name":"my-app"}'
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "not running" page | Use `restart` action; check logs |
| 502 Bad Gateway | App not listening yet; wait 1–2s then retry |
| Static assets 404 | Ensure `<base>` tag present; use relative paths |
| App unreachable | Confirm `host="0.0.0.0"` in app code |
| Port conflict | Use `alloc_port` — it skips used ports |
| Health check fails | Check `ps aux | grep python`; look for import errors |
| Name rejected | Must match `^[a-z][a-z0-9-]{0,28}[a-z0-9]$`; no underscores |

---

## Template customization quick reference

**`flask-dashboard`** — metrics + charts:
- Edit `/api/data` route in `app.py` to return your data
- Use `psutil` for system metrics (pre-installed)
- Add/remove `datasets` in the chart config in `index.html`

**`flask-basic`** — general web app:
- Add routes to `app.py`; extend `base.html` for new pages
- Use `templates/index.html` as the main page template

**`static-html`** — pure front-end:
- Replace sample `DATA` in `app.js` with a `fetch()` call or static values
- Start command is `python serve.py` (not `app.py`)
- No Python backend — serve.py only serves static files

**`dashboard-realtime`** — live streaming dashboard:
- Edit `generate_data()` in `app.py` to produce your metrics/chart data
- SSE streams every 2s; adjust interval in the generator loop
- Three chart types available: line, bar, doughnut

**`utility-spa`** — lightweight single-page tool:
- Replace transform functions in `app.js` with your tool logic
- Input/output layout: textarea input, action buttons, output area
- Start command is `python serve.py` (not `app.py`)
- No Python backend — serve.py only serves static files

**`crud-app`** — data management app:
- Look for `# CUSTOMIZE:` markers in `app.py` — change table name, columns, form fields
- Template has 4 HTML files (list/form/detail/404) — update field references, do NOT delete or recreate
- Routes handle list/detail/create/edit/delete; update SQL queries to match your columns
- See the worked example in Step 5 above for a complete walkthrough

**`file-tool`** — file upload and conversion:
- Edit ALLOWED_EXTENSIONS and MAX_CONTENT_LENGTH in `app.py` for your needs
- Add conversions: extend CONVERSIONS dict in `app.py` + CONVERT_OPTIONS in `app.js`
- Uploads stored in `uploads/` directory (auto-created)
