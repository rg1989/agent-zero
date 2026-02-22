---
name: "web-app-builder"
description: "Build, deploy, and manage local web applications within Agent Zero. Use when the user asks to build a dashboard, visualisation, web app, or anything best served as a browser-based interface. Apps are served at localhost:50000/{app_name}/ with no extra port forwarding required."
version: "2.0.0"
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

Build and host local web applications accessible at `localhost:50000/{app_name}/`.
No extra port forwarding needed. Apps persist across Docker rebuilds.

---

## How routing works

```
Browser → localhost:50000/{app_name}/... → (proxy inside container) → localhost:{PORT}/...
```

The proxy is built into Agent Zero's server. You just start the app on any port in 9000–9099.

---

## Step 1 — Choose a template

**Always start from a template.** This saves setup time and ensures correct routing.

Read `/a0/apps/_templates/_GUIDE.md` for full details. Quick decision:

| Task | Template |
|------|----------|
| Charts, metrics, live data | `flask-dashboard` |
| Web app with Python logic, forms, multiple pages | `flask-basic` |
| Pure front-end visualisation, no Python needed | `static-html` |

---

## Step 2 — Allocate a port

```bash
PORT=$(curl -s "http://localhost/webapp?action=alloc_port" | python3 -c "import sys,json; print(json.load(sys.stdin)['port'])")
echo "Port: $PORT"
```

---

## Step 3 — Copy the template

```bash
cp -r /a0/apps/_templates/{CHOSEN_TEMPLATE} /a0/apps/{app_name}
```

Example:
```bash
cp -r /a0/apps/_templates/flask-dashboard /a0/apps/my_dashboard
```

---

## Step 4 — Customise the app

Edit the copied files. The key things to change:

**For `flask-dashboard`:**
- `app.py` → replace the sample data in `/api/data` with real data (files, psutil, DB, etc.)
- `templates/index.html` → change the title, add/remove metric cards or chart datasets

**For `flask-basic`:**
- `app.py` → add your routes and logic
- `templates/index.html` → replace the content section

**For `static-html`:**
- `app.js` → replace `DATA` with real data or a fetch call
- `index.html` → swap Chart.js CDN for D3/Plotly if needed

**Rules that must not change:**
- Always `host="0.0.0.0"` (not 127.0.0.1)
- Always read port from env: `PORT = int(os.environ.get("PORT", 9000))`
- Always read app name from env: `APP_NAME = os.environ.get("APP_NAME", "")`
- Always use relative asset URLs (the `<base>` tag handles sub-path routing)

---

## Step 5 — Register and start

```bash
# Register
curl -s -X POST http://localhost/webapp \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"register\",\"name\":\"{app_name}\",\"port\":$PORT,\"cmd\":\"python app.py\",\"cwd\":\"/a0/apps/{app_name}\",\"description\":\"{short description}\"}"

# Start
curl -s -X POST http://localhost/webapp \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"start\",\"name\":\"{app_name}\"}"
```

For `static-html`, the start command is `python serve.py` instead of `python app.py`.

The app is now live at **`localhost:50000/{app_name}/`**.

---

## Management commands

All via `POST http://localhost/webapp` with JSON body, or GET for reads.

```bash
# List all apps
curl -s "http://localhost/webapp?action=list"

# Stop
curl -s -X POST http://localhost/webapp -H "Content-Type: application/json" \
  -d '{"action":"stop","name":"my_app"}'

# Restart
curl -s -X POST http://localhost/webapp -H "Content-Type: application/json" \
  -d '{"action":"restart","name":"my_app"}'

# Enable autostart (survives container restarts)
curl -s -X POST http://localhost/webapp -H "Content-Type: application/json" \
  -d '{"action":"autostart","name":"my_app","enabled":true}'

# Remove
curl -s -X POST http://localhost/webapp -H "Content-Type: application/json" \
  -d '{"action":"remove","name":"my_app"}'
```

---

## Monitoring

```bash
# Check if port is responding
python3 -c "import socket; s=socket.socket(); s.settimeout(1); print('UP' if not s.connect_ex(('127.0.0.1', PORT)) else 'DOWN'); s.close()"

# View logs (if you registered with log redirect)
tail -f /a0/apps/{app_name}/app.log

# Running processes
ps aux | grep python
```

To log output, register with:
```
"cmd": "python app.py >> /a0/apps/{app_name}/app.log 2>&1"
```

---

## Naming rules

- Lowercase, digits, hyphens, underscores only
- Do NOT use: `login`, `logout`, `health`, `message`, `poll`, `upload`,
  `settings_get`, `settings_set`, `csrf_token`, `chat_create`, `mcp`, `a2a`,
  `webapp`, `socket.io`, `static`
- Good names: `dashboard`, `sales_viz`, `monitor`, `log_viewer`, `data_explorer`

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "not running" page | Use `restart` action; check logs |
| 502 Bad Gateway | App not listening yet; wait 1–2s then retry |
| Static assets 404 | Ensure `<base>` tag present; use relative paths |
| App unreachable | Confirm `host="0.0.0.0"` in app code |
| Port conflict | Use `alloc_port` — it skips used ports |
