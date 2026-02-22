# App Templates — Selection Guide

Templates live at `/a0/apps/_templates/`. Copy one to start a new app instantly
instead of building from scratch.

---

## Quick decision tree

```
Does the app need Python logic?
│
├── YES → Does it need to show charts / metrics?
│         ├── YES → flask-dashboard
│         └── NO  → flask-basic
│
└── NO  → static-html
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
