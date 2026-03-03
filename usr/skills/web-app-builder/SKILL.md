---
name: "web-app-builder"
description: "Build, deploy, and manage local web applications within Agent Zero. Use when the user asks to build a dashboard, visualisation, web app, or anything best served as a browser-based interface. Apps are served at localhost:50000/{app_name}/ with no extra port forwarding required."
version: "3.0.0"
author: "Agent Zero"
tags: ["webapp", "dashboard", "visualisation", "flask", "server", "deploy", "monitor", "apps"]
trigger_patterns:
  - "build me an app"
  - "build a dashboard"
  - "build a web app"
  - "create a dashboard"
  - "create a web app"
  - "make a dashboard"
  - "make a web app"
  - "visualise"
  - "visualize"
  - "show me a chart"
  - "build a ui"
  - "create a ui"
  - "serve a webpage"
  - "start the app"
  - "stop the app"
  - "restart the app"
  - "list my apps"
  - "show my apps"
  - "app status"
---

# Web App Builder

CRITICAL: Follow the MANDATORY SEQUENCE below exactly. Do NOT skip steps. If any step fails, STOP and report the failure to the user — never proceed with a broken app.

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
- Lowercase letters, digits, and hyphens only (regex: `^[a-z][a-z0-9-]{1,28}[a-z0-9]$`)
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

4. **Handle override:** If the user asks to use a different template (now or later):
   - Acknowledge the change
   - Switch to the requested template
   - Continue from Step 3 (allocate port) — do NOT restart from Step 1

---

### Step 3 — Allocate a port

```bash
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

---

### Step 5 — Customize the app

Edit the copied files to implement what the user requested. Key rules that MUST NOT change:
- Always `host="0.0.0.0"` (not 127.0.0.1)
- Always read port from env: `PORT = int(os.environ.get("PORT", 9000))`
- Always read app name from env: `APP_NAME = os.environ.get("APP_NAME", "")`
- Always use relative asset URLs (the `<base>` tag handles sub-path routing)
- Never hardcode port numbers

**For `flask-dashboard`:**
- `app.py` → replace the sample data in `/api/data` with real data (files, psutil, DB, etc.)
- `templates/index.html` → change the title, add/remove metric cards or chart datasets

**For `flask-basic`:**
- `app.py` → add your routes and logic
- `templates/index.html` → replace the content section

**For `static-html`:**
- `app.js` → replace `DATA` with real data or a fetch call
- `index.html` → swap Chart.js CDN for D3/Plotly if needed

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
| Name rejected | Must match `^[a-z][a-z0-9-]{1,28}[a-z0-9]$`; no underscores |

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
- Edit the Item model section in `app.py` to define your fields and CREATE_TABLE_SQL
- Routes handle list/detail/create/edit/delete automatically based on the model
- SQLite database auto-creates on first request

**`file-tool`** — file upload and conversion:
- Edit ALLOWED_EXTENSIONS and MAX_CONTENT_LENGTH in `app.py` for your needs
- Add conversions: extend CONVERSIONS dict in `app.py` + CONVERT_OPTIONS in `app.js`
- Uploads stored in `uploads/` directory (auto-created)
