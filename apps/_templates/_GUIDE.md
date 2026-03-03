# App Templates — Selection Guide

Templates live at `/a0/apps/_templates/`. Copy one to start a new app instantly
instead of building from scratch.

---

## Quick reference table

| Template | Backend | DB | Best for |
|---|---|---|---|
| `flask-basic` | yes | no | General web apps, forms, custom Python logic |
| `flask-dashboard` | yes | no | Metrics/charts dashboard with polling refresh |
| `static-html` | no | no | Pure front-end, D3/Plotly visualizations, external APIs |
| `utility-spa` | no | no | Input-process-output tools: calculators, converters |
| `dashboard-realtime` | yes | no | Live data with SSE streaming, multiple chart types |
| `crud-app` | yes | yes | Record management: create/read/update/delete with DB |
| `file-tool` | yes | no | File upload, download, format conversion |

---

## Decision tree

```
Does the app need to store/manage data records?
|
+-- YES --> crud-app
|
+-- NO --> Does it need Python backend logic?
           |
           +-- YES --> Does it show charts/metrics with live data?
           |          |
           |          +-- YES --> Need real-time streaming (SSE)?
           |          |          |
           |          |          +-- YES --> dashboard-realtime
           |          |          +-- NO  --> flask-dashboard
           |          |
           |          +-- NO  --> Does it handle file uploads?
           |                     |
           |                     +-- YES --> file-tool
           |                     +-- NO  --> flask-basic
           |
           +-- NO  --> Is it an input-process-output tool?
                      |
                      +-- YES --> utility-spa
                      +-- NO  --> static-html
```

---

## Templates

### `flask-basic`
**Best for:** General web apps — forms, pages, dynamic content, any Python backend logic.

Includes:
- `app.py` — Flask app with a `/` route and an example `/api/data` endpoint
- `templates/base.html` — base layout (topbar, main content area)
- `templates/index.html` — starter page extending base
- `static/style.css` — dark theme, grid utilities, card/button components
- `static/app.js` — fetch helper, DOM-ready boilerplate

Start command: `python app.py`
No extra pip installs needed (Flask is pre-installed).

---

### `flask-dashboard`
**Best for:** Metrics, monitoring, time-series charts, dashboards that show live/polling data.

Includes:
- `app.py` — Flask app with a `/api/data` endpoint returning metrics + chart data
- `templates/index.html` — self-contained dashboard with metrics grid and Chart.js line chart
- `static/style.css` — dashboard-optimised dark theme
- Chart.js loaded from CDN — no npm needed

`/api/data` returns this shape — customise it to your data source:
```json
{
  "metrics": [{"label": "...", "value": "...", "unit": "...", "color": "#hex"}],
  "chart":   {"labels": [...], "datasets": [{"label": "...", "data": [...], "color": "#hex"}]},
  "updated_at": 1234567890
}
```

Start command: `python app.py`
No extra pip installs needed.

**Useful with psutil** (pre-installed) for real system metrics:
```python
import psutil
{"label": "CPU", "value": f"{psutil.cpu_percent():.0f}", "unit": "%", "color": "#00f2fe"}
```

---

### `static-html`
**Best for:** Pure front-end visualisations — no Python backend logic needed. D3.js charts, custom SVGs, single-page views from static data or external APIs.

Includes:
- `serve.py` — minimal Flask static file server (injects `<base>` tag automatically)
- `index.html` — HTML page with Chart.js pre-wired (D3/Plotly CDN options commented in)
- `style.css` — dark theme matching other templates
- `app.js` — sample data + Chart.js render + table render

Start command: `python serve.py`
No extra pip installs needed.

**To use with D3.js:** uncomment the D3 CDN in `index.html` and replace the Chart.js code in `app.js`.

---

### `utility-spa`
**Best for:** Lightweight single-page tools — calculators, text processors, unit converters, encoding/decoding tools, local data viewers.

Includes:
- `serve.py` — Flask static file server with automatic `<base>` tag injection (same as `static-html` pattern)
- `index.html` — input area, action button row, output area layout
- `style.css` — dark theme with `.tool-input`, `.tool-actions`, `.tool-output` classes
- `app.js` — sample text transformer (uppercase, lowercase, title case, reverse, char count)

Start command: `python serve.py`
No extra pip installs needed.

**Tip:** Replace the sample transform functions in `app.js` with your own logic. The `processInput()` function is the main entry point — it reads the input, applies the transformation, and writes the result.

---

### `dashboard-realtime`
**Best for:** Live monitoring with streaming data — process metrics, live feeds, real-time event displays, any dashboard where data changes every few seconds.

Includes:
- `app.py` — Flask app with SSE endpoint (`/api/stream`), polling fallback (`/api/data`), and shared `generate_data()` function
- `templates/index.html` — three Chart.js charts (line time-series, bar, doughnut), metric cards, connection status indicator
- `static/style.css` — dashboard dark theme with responsive `.charts-grid` (line full-width, bar + doughnut side-by-side)

Start command: `python app.py`
No extra pip installs needed.

**Tip:** Use SSE for under 30 concurrent users; consider switching to polling-only mode (the `/api/data` endpoint) for higher load. The frontend handles SSE failure automatically by falling back to polling — no code changes needed.

---

### `crud-app`
**Best for:** Data management — any app that creates, reads, updates, and deletes records. Item/task/inventory managers, simple admin tools, anything that needs a database.

Includes:
- `app.py` — Flask app with SQLite (`get_db()`/`close_db()` pattern), 7 routes (list, detail, new, create, edit, update, delete), and 2 API endpoints
- `templates/base.html` — base layout with `<base>` tag, nav, flash message block
- `templates/list.html` — data table with item count, empty-state, and delete confirmation
- `templates/form.html` — shared form for create and edit (`item=None` vs `item` object)
- `templates/detail.html` — single-item card with edit/delete/back actions
- `templates/404.html` — not-found page for missing item IDs
- `static/style.css` — dark theme with `.data-table`, `.badge`, `.form-group`, `.flash` styles
- `static/app.js` — delete confirmation via `data-confirm` attribute, flash auto-dismiss

Start command: `python app.py`
No extra pip installs needed (sqlite3 is stdlib).

**Tip:** Edit the Item model section in `app.py` — add your own fields to `CREATE_TABLE_SQL` and update the queries. Run the app once to auto-create the database file.

---

### `file-tool`
**Best for:** File handling — upload, download, convert, process. Document processors, media tools, format converters, file managers.

Includes:
- `app.py` — Flask app with upload (`secure_filename`, extension allowlist, 50 MB limit), listing, download, delete, and format conversion endpoints
- `templates/base.html` — base layout with `<base>` tag
- `templates/index.html` — drag-and-drop dropzone, file-card grid, toast notification container
- `static/style.css` — dark theme with dropzone, file-card grid, progress bar, toast styles
- `static/app.js` — drag-drop upload, loadFiles, deleteFile, convertFile, showToast, CONVERT_OPTIONS map

Start command: `python app.py`
No extra pip installs needed (werkzeug, csv, io, mimetypes are all pre-installed or stdlib).

**Tip:** Add new conversions by extending the `CONVERSIONS` dict in `app.py` and the `CONVERT_OPTIONS` map in `app.js`. The conversion pipeline is isolated in the `/convert` endpoint — add a new `(ext, target)` key to `CONVERSIONS` and return the converted bytes.

---

## How to use a template

### 1. Allocate a port
```bash
PORT=$(curl -s "http://localhost/webapp?action=alloc_port" | python3 -c "import sys,json; print(json.load(sys.stdin)['port'])")
echo "Using port $PORT"
```

### 2. Copy the template
```bash
cp -r /a0/apps/_templates/flask-dashboard /a0/apps/my_app
```

### 3. Register + start
```bash
curl -s -X POST http://localhost/webapp \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"register\",\"name\":\"my_app\",\"port\":$PORT,\"cmd\":\"python app.py\",\"cwd\":\"/a0/apps/my_app\",\"description\":\"My dashboard\"}"

curl -s -X POST http://localhost/webapp \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"start\",\"name\":\"my_app\"}"
```

### 4. Open in browser
`localhost:50000/my_app/`

### 5. Customise
Edit `/a0/apps/my_app/app.py` and the templates/static files.
The app manager auto-sets `PORT` and `APP_NAME` env vars — read them in your code.

---

## What NOT to do

- Do not hardcode the port — always use `int(os.environ.get("PORT", 9000))`
- Do not use `host="127.0.0.1"` — always `host="0.0.0.0"` so the proxy can reach it
- Do not use absolute asset URLs like `/static/style.css` — the `<base>` tag + relative paths handle sub-path routing correctly
- Do not edit files in `_templates/` directly — copy first, then edit the copy
