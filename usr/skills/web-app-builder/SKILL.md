---
name: "web-app-builder"
description: "Build, deploy, and manage local web applications within Agent Zero. Use when the user asks to build a dashboard, visualisation, web app, or anything best served as a browser-based interface. Apps are served at localhost:50000/{app_name}/ with no extra port forwarding required."
version: "1.0.0"
author: "Agent Zero"
tags: ["webapp", "dashboard", "visualisation", "flask", "fastapi", "react", "server", "deploy", "monitor", "apps"]
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

Build and host local web applications that are immediately accessible in the user's browser at `localhost:50000/{app_name}/` — no extra port forwarding needed.

---

## How It Works

Agent Zero runs inside Docker. A reverse proxy built into the server intercepts any request to `localhost:50000/{app_name}/` and forwards it to the app's inner port (in the 9000–9099 range). You start the app, register it, and it's live.

```
User browser → localhost:50000/my_app/ → (proxy) → container:9000 → your app
```

---

## Directory Convention

All apps live under `/a0/apps/{app_name}/`:

```
/a0/apps/
└── my_app/
    ├── app.py          # or server.js, index.html, etc.
    ├── requirements.txt
    ├── templates/
    ├── static/
    └── data/
```

---

## Step-by-Step: Building a New App

### Step 1 — Allocate a port

```python
import requests
resp = requests.get("http://localhost/webapp?action=alloc_port")
port = resp.json()["port"]
print(f"Using port {port}")
```

Or via shell:
```bash
curl -s "http://localhost/webapp?action=alloc_port" | python3 -c "import sys,json; print(json.load(sys.stdin)['port'])"
```

### Step 2 — Create the app directory and write the app

```bash
mkdir -p /a0/apps/my_app
```

Write `app.py` (or whatever fits the stack). **The app must listen on the allocated port.** Use the `PORT` environment variable which is always set automatically:

```python
import os
port = int(os.environ.get("PORT", 9000))
app.run(host="0.0.0.0", port=port)
```

### Step 3 — Register and start the app

```python
import requests

# Register
requests.post("http://localhost/webapp", json={
    "action": "register",
    "name": "my_app",
    "port": 9000,           # port from step 1
    "cmd": "python app.py", # command to start the app
    "cwd": "/a0/apps/my_app",
    "description": "My dashboard"
})

# Start
requests.post("http://localhost/webapp", json={
    "action": "start",
    "name": "my_app"
})
```

The app is now accessible at **`localhost:50000/my_app/`**.

---

## Management API (POST /webapp)

All management is done via `POST http://localhost/webapp` with a JSON body.

| action | required fields | description |
|--------|----------------|-------------|
| `list` | — | List all registered apps |
| `alloc_port` | — | Get next available port (9000–9099) |
| `register` | `name`, `port`, `cmd`, `cwd` | Register an app |
| `start` | `name` | Start a registered app |
| `stop` | `name` | Stop a running app |
| `restart` | `name` | Stop + start |
| `status` | `name` | Get app info & status |
| `remove` | `name` | Stop + unregister |
| `autostart` | `name`, `enabled` | Enable/disable autostart on server boot |

GET shortcuts: `GET /webapp?action=list` and `GET /webapp?action=status&name=my_app`

---

## App Stack Recipes

### Python / Flask

```python
# /a0/apps/my_app/app.py
import os
from flask import Flask
app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>Hello from my_app</h1>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    app.run(host="0.0.0.0", port=port, debug=False)
```

Start command: `python app.py`
Install deps first: `pip install flask` (or add to requirements.txt and run `pip install -r requirements.txt`)

### Python / FastAPI

```python
# /a0/apps/my_app/app.py
import os, uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def root():
    return "<h1>FastAPI app</h1>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

Start command: `python app.py`

### Static HTML (via Python http.server)

```bash
mkdir -p /a0/apps/my_app
# write index.html ...
```

Register with cmd: `python -m http.server $PORT`

### Node.js / Express

```js
// /a0/apps/my_app/server.js
const express = require('express');
const app = express();
const port = process.env.PORT || 9000;
app.get('/', (req, res) => res.send('<h1>Node app</h1>'));
app.listen(port, '0.0.0.0', () => console.log(`Listening on ${port}`));
```

Start command: `node server.js`

---

## Important: Path-Aware Apps

Because the app is served under a sub-path (`/my_app/`), internal links and asset references need to be relative, or you need to configure the app's base path.

**Flask example with correct base path:**

```python
from flask import Flask
app = Flask(__name__)

# Use url_for() for all internal links — Flask handles relative paths correctly
# Avoid hardcoded absolute paths like href="/"
```

**FastAPI with root_path:**

```python
app = FastAPI(root_path="/my_app")
```

**Static assets:** use relative paths (`./style.css`) or the `<base>` HTML tag:
```html
<base href="/my_app/">
```

---

## Monitoring & Maintenance

### Check status of all apps

```python
import requests, json
apps = requests.get("http://localhost/webapp?action=list").json()["apps"]
for a in apps:
    print(f"{a['name']:20} {a['status']:10} port={a['port']}")
```

### Check if an app is alive (ping its port)

```python
import socket
def is_port_open(port):
    s = socket.socket()
    s.settimeout(1)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except:
        return False

print(is_port_open(9000))
```

### Restart a crashed app

```python
import requests
requests.post("http://localhost/webapp", json={"action": "restart", "name": "my_app"})
```

### View running processes

```bash
ps aux | grep python
# or
ps aux | grep node
```

### View app logs

If you want persistent logs, redirect stdout when registering:

```python
requests.post("http://localhost/webapp", json={
    "action": "register",
    "name": "my_app",
    "port": 9000,
    "cmd": "python app.py >> /a0/apps/my_app/app.log 2>&1",
    "cwd": "/a0/apps/my_app",
})
```

Then: `tail -f /a0/apps/my_app/app.log`

---

## Naming Rules

- App names must be **URL-safe**: lowercase letters, digits, hyphens, underscores
- **Avoid reserved names** (these are Agent Zero's own routes):
  `login`, `logout`, `health`, `message`, `poll`, `upload`, `settings_get`, `settings_set`, `csrf_token`, `chat_create`, `mcp`, `a2a`, `webapp`, `socket.io`, `static`
- Good names: `dashboard`, `sales_viz`, `monitor`, `my_app`, `data_explorer`

---

## Full Example: Data Dashboard

```python
# Allocate port
import requests
port = requests.get("http://localhost/webapp?action=alloc_port").json()["port"]

# Write the app
import os
app_dir = f"/a0/apps/dashboard"
os.makedirs(app_dir, exist_ok=True)

app_code = f'''
import os, json
from flask import Flask, jsonify
import psutil

app = Flask(__name__)

@app.route("/")
def index():
    return """<html><body>
    <h1>System Dashboard</h1>
    <div id="data">Loading...</div>
    <script>
      fetch("/metrics").then(r=>r.json()).then(d=>{{
        document.getElementById("data").innerHTML =
          "<p>CPU: "+d.cpu+"%</p><p>RAM: "+d.ram+"%</p>";
      }});
      setInterval(()=>location.reload(), 5000);
    </script></body></html>"""

@app.route("/metrics")
def metrics():
    return jsonify(cpu=psutil.cpu_percent(), ram=psutil.virtual_memory().percent)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", {port}))
    app.run(host="0.0.0.0", port=port)
'''

with open(f"{app_dir}/app.py", "w") as f:
    f.write(app_code)

# Register
requests.post("http://localhost/webapp", json={{
    "action": "register",
    "name": "dashboard",
    "port": port,
    "cmd": "python app.py",
    "cwd": app_dir,
    "description": "System resource dashboard"
}})

# Start
requests.post("http://localhost/webapp", json={{"action": "start", "name": "dashboard"}})
print(f"Dashboard live at: localhost:50000/dashboard/")
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| App shows "not running" page | Use `restart` action or check logs |
| 502 Bad Gateway | App crashed or not listening on correct port yet; wait a second then retry |
| Port conflict | Use `alloc_port` — it skips ports already in the registry |
| Static files not loading | Use relative paths or `<base href="/{app_name}/">` |
| App not reachable | Make sure `host="0.0.0.0"` (not `127.0.0.1`) in the app |

---

## Quick Reference

```bash
# List all apps
curl -s http://localhost/webapp?action=list | python3 -m json.tool

# Allocate a port
curl -s http://localhost/webapp?action=alloc_port

# Start an app
curl -s -X POST http://localhost/webapp -H "Content-Type: application/json" \
  -d '{"action":"start","name":"my_app"}'

# Stop an app
curl -s -X POST http://localhost/webapp -H "Content-Type: application/json" \
  -d '{"action":"stop","name":"my_app"}'

# Remove an app
curl -s -X POST http://localhost/webapp -H "Content-Type: application/json" \
  -d '{"action":"remove","name":"my_app"}'
```
