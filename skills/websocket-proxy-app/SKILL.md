---
name: "websocket-proxy-app"
description: "Build Agent Zero apps that require WebSocket connections (noVNC, live terminals, real-time streams, etc.). Agent Zero's proxy supports ws_port registration so WebSocket traffic bypasses Flask and routes directly to the WebSocket service. Use when asked to build any app that needs persistent WebSocket connections, VNC viewers, terminal emulators, or real-time binary streaming."
version: "1.0.0"
author: "Agent Zero"
tags: ["websocket", "vnc", "novnc", "proxy", "flask", "websockify", "realtime", "streaming"]
trigger_patterns:
  - "websocket app"
  - "vnc viewer"
  - "novnc"
  - "browser vnc"
  - "websockify"
  - "real-time app"
  - "live terminal"
  - "ws_port"
  - "websocket proxy"
---

# WebSocket Proxy App Skill

## Architecture Overview

Agent Zero exposes **one port (50000)** through its reverse proxy. All traffic enters here:

```
Browser
  ↓ HTTP  →  localhost:50000/{app_name}/...   → Flask on port 9002 (HTML, REST)
  ↓ WS    →  localhost:50000/{app_name}/path  → ws_port (e.g. 6080, websockify)
                    ↓
              AppProxy (app_proxy.py) routes based on scope type:
              - scope["type"] == "http"      → app["port"]
              - scope["type"] == "websocket" → app["ws_port"] (if set) else app["port"]
```

**Key insight:** Register with `ws_port` to split HTTP and WebSocket to different internal ports. This means Flask handles pages/REST while a dedicated WebSocket service (websockify, a Node WS server, etc.) handles the persistent connection — no gevent/async Flask needed.

---

## Registration: The Critical Step

### Without ws_port (HTTP-only apps — existing behaviour)
```json
POST /webapp
{
  "action": "register",
  "name": "my-app",
  "port": 9001,
  "cmd": "python app.py",
  "cwd": "/a0/apps/my-app",
  "description": "My app"
}
```

### With ws_port (WebSocket apps — new capability)
```json
POST /webapp
{
  "action": "register",
  "name": "my-app",
  "port": 9001,
  "ws_port": 6080,
  "cmd": "bash start.sh",
  "cwd": "/a0/apps/my-app",
  "description": "My app with WebSocket"
}
```

- `port` → HTTP requests (`GET /my-app/`, REST calls)
- `ws_port` → WebSocket upgrades (`ws://host/my-app/websockify`)

---

## VNC Browser Viewer: Full Recipe

### Stack
| Component   | Port | Purpose                                      |
|-------------|------|----------------------------------------------|
| Xvfb        | —    | Virtual X11 display on :99                   |
| x11vnc      | 5900 | VNC server reading from Xvfb                 |
| Chromium    | —    | Browser running on the virtual display       |
| websockify  | 6080 | WebSocket→TCP bridge (WS → VNC port 5900)    |
| Flask       | 9002 | Serves noVNC HTML and handles REST           |

### App Directory Structure
```
/a0/apps/browser-vnc/
├── start.sh          # Starts all processes
├── app.py            # Flask server (port 9002)
├── requirements.txt
└── static/
    └── novnc/        # noVNC JS library files
```

### start.sh
```bash
#!/bin/bash
set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. Virtual display
Xvfb :99 -screen 0 1920x1080x24 &
sleep 1

# 2. VNC server (no password, localhost only)
x11vnc -display :99 -forever -nopw -listen 127.0.0.1 -rfbport 5900 &
sleep 1

# 3. Browser
DISPLAY=:99 chromium --no-sandbox --disable-gpu \
  --disable-dev-shm-usage --start-maximized "$STARTUP_URL" &

# 4. WebSocket bridge
websockify --web="$APP_DIR/static/novnc" 6080 127.0.0.1:5900 &
sleep 1

# 5. Flask (HTTP only — no WebSocket needed here)
cd "$APP_DIR"
python app.py
```

### app.py (Flask)
```python
import os
from flask import Flask, render_template_string

app = Flask(__name__, static_folder="static")
PORT = int(os.environ.get("PORT", 9002))
APP_NAME = os.environ.get("APP_NAME", "browser-vnc")

HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Browser VNC</title>
  <style>
    body { margin: 0; background: #000; overflow: hidden; }
    #screen { width: 100vw; height: 100vh; }
  </style>
  <!-- noVNC core -->
  <script type="module">
    import RFB from '/{{ app_name }}/static/novnc/core/rfb.js';

    // Connect through Agent Zero's proxy — same host, correct path
    const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProto}//${location.host}/{{ app_name }}/websockify`;

    const rfb = new RFB(document.getElementById('screen'), wsUrl, {
      credentials: { password: '' },
    });
    rfb.scaleViewport = true;
    rfb.resizeSession = true;
  </script>
</head>
<body>
  <div id="screen"></div>
</body>
</html>"""

@app.route("/")
@app.route("/<path:subpath>")
def index(subpath=""):
    return render_template_string(HTML, app_name=APP_NAME)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
```

### requirements.txt
```
flask>=3.0
```

### Install noVNC
```bash
# Run once during setup
cd /a0/apps/browser-vnc/static
git clone --depth=1 https://github.com/novnc/noVNC.git novnc
```

### Register and Start
```python
import requests

BASE = "http://localhost:50000"

# Register with split HTTP/WS ports
requests.post(f"{BASE}/webapp", json={
    "action": "register",
    "name": "browser-vnc",
    "port": 9002,        # Flask — HTTP traffic
    "ws_port": 6080,     # websockify — WebSocket traffic
    "cmd": "bash start.sh",
    "cwd": "/a0/apps/browser-vnc",
    "description": "VNC Browser Viewer",
    "autostart": True,
    "env": {
        "STARTUP_URL": "https://example.com",
        "DISPLAY": ":99",
    }
})

requests.post(f"{BASE}/webapp", json={"action": "start", "name": "browser-vnc"})
print(f"Open: {BASE}/browser-vnc/")
```

---

## Other WebSocket App Patterns

### Pattern: Live Terminal (ttyd)
```json
{
  "name": "terminal",
  "port": 9003,
  "ws_port": 7681,
  "cmd": "ttyd --port 7681 bash & python serve_page.py",
  "ws_path": "/ws"
}
```
noVNC equivalent for terminal: connect to `ws://host/terminal/ws`

### Pattern: Custom Node.js WS Server
```json
{
  "name": "live-dashboard",
  "port": 9004,
  "ws_port": 9005,
  "cmd": "node server.js"
}
```
`server.js` listens for HTTP on `PORT` env var and WebSocket on `9005`.

### Pattern: Single Port (no ws_port needed)
If your app handles both HTTP and WebSocket on the same port (e.g. FastAPI, aiohttp, Node express + ws), just register with `port` and omit `ws_port`. AppProxy will upgrade WebSocket connections to that port directly.

---

## WebSocket URL Pattern

Always construct the WebSocket URL from `window.location` — never hardcode ports:

```javascript
const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${wsProto}//${location.host}/${APP_NAME}/your-ws-path`;
```

This works regardless of whether Agent Zero is accessed via HTTP or HTTPS, localhost or a tunnel.

---

## Checklist

- [ ] `ws_port` is set in registration if HTTP and WebSocket run on different ports
- [ ] WebSocket service is listening on `127.0.0.1:{ws_port}` before Flask starts
- [ ] noVNC / client JS uses `window.location.host` (not `localhost:6080`)
- [ ] `start.sh` starts WebSocket service **before** Flask (`app.py` last)
- [ ] `app.py` only handles HTTP — no gevent/async required
- [ ] Test path: `ws://localhost:50000/{app_name}/websockify` in browser DevTools → Network tab → WS

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `connection refused` on WebSocket | ws_port service not running | Check `start.sh` order, add `sleep` between starts |
| `unexpected token` in browser console | Proxy treating WS as HTTP | Ensure `ws_port` is set in registration |
| `1001 App port unreachable` | App not registered or wrong port | Verify `/webapp?action=status&name=…` |
| noVNC black screen | x11vnc/Xvfb race condition | Add `sleep 2` between Xvfb and x11vnc in `start.sh` |
| WebSocket connects then immediately closes | subprotocol mismatch | websockify needs `--web` flag, noVNC negotiates `binary` subprotocol automatically |
