# Shared Browser Control Skill

## Metadata
- name: shared-browser
- version: 3.0
- description: Control and observe the shared Chromium browser on Xvfb :99 via CDP WebSocket and xdotool
- tags: browser, chromium, cdp, xdotool, automation, shared
- author: agent-zero

## Overview
A shared Chromium browser runs on virtual display Xvfb :99, visible to the user via noVNC.
Both user and agent can interact simultaneously.

## DEFAULT BROWSER RULE ⭐
**This shared browser is the DEFAULT browser for ALL user requests.**

- User says "open a browser", "navigate to X", "go to X", "browse to X", "open X in browser" → USE THIS SKILL
- User says "use playwright", "playwright browser", "playwright agent" → Only then use `browser_agent` tool
- NEVER use `browser_agent` tool unless the user explicitly mentions Playwright
- Always load this skill first when any browser-related task is requested

**CRITICAL: NEVER use the `browser_agent` tool for the shared browser — it spawns a separate isolated Playwright instance and creates a persistent loader in the Agent Zero UI.**

## Stack
| Component | Detail |
|---|---|
| Virtual Display | Xvfb :99 (1280x720) |
| Browser | Chromium on display :99 |
| VNC Server | x11vnc port 5900 |
| WebSocket bridge | websockify port 6081 |
| CDP debug API | HTTP + WebSocket port 9222 |
| Screenshot | scrot |
| UI control | xdotool |

## Prerequisites
Chromium MUST be started with `--remote-allow-origins=*` for CDP WebSocket access.
Already configured in `/a0/apps/shared-browser/startup.sh`.
If CDP returns 403: kill Chromium and restart with that flag.

---

## Method 1: Screenshot (Observe)

```bash
DISPLAY=:99 scrot /tmp/shared_browser.png -o
```
Load with vision_load to see current state before acting.

---

## Method 2: CDP WebSocket (Programmatic — FAST, No UI)

### Setup helper
```python
import websocket, json, urllib.request, time

tabs = json.loads(urllib.request.urlopen('http://localhost:9222/json').read())
page_tabs = [t for t in tabs if t.get('type') == 'page']

# Connect to desired tab
ws = websocket.create_connection(page_tabs[0]['webSocketDebuggerUrl'])

msg_id = [0]
def send(method, params={}):
    msg_id[0] += 1
    ws.send(json.dumps({'id': msg_id[0], 'method': method, 'params': params}))
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == msg_id[0]:
            return resp
        # else: it's an async event, skip
```

### Navigate
```python
send('Page.navigate', {'url': 'https://example.com'})
```

### Run JavaScript
```python
result = send('Runtime.evaluate', {'expression': 'document.title', 'returnByValue': True})
title = result['result']['result']['value']
```

### Get Console Errors (existing page)
```python
result = send('Runtime.evaluate', {
    'expression': '({title: document.title, url: location.href})',
    'returnByValue': True
})
val = result['result']['result']['value']
```

### Capture LIVE Network + Console (must enable BEFORE navigation)
```python
send('Network.enable')
send('Log.enable')
send('Page.navigate', {'url': 'https://example.com'})
time.sleep(2)

network_requests = []
console_msgs = []
ws.settimeout(2)
try:
    while True:
        msg = json.loads(ws.recv())
        method = msg.get('method', '')
        if method == 'Network.requestWillBeSent':
            req = msg['params']['request']
            network_requests.append({'url': req['url'], 'method': req['method']})
        elif method == 'Log.entryAdded':
            entry = msg['params']['entry']
            console_msgs.append({'level': entry['level'], 'text': entry['text']})
except:
    pass

print('Network:', network_requests)
print('Console:', console_msgs)
```

### Get Network Resources (already-loaded page, no navigation needed)
```python
result = send('Runtime.evaluate', {
    'expression': 'JSON.stringify(performance.getEntriesByType("resource").map(r=>({name:r.name.split("/").pop().slice(0,40),ms:Math.round(r.duration),bytes:r.transferSize})))',
    'returnByValue': True
})
import json as _json
resources = _json.loads(result['result']['result']['value'])
for r in resources:
    print(f"{r['name']:40} {r['ms']:5}ms  {r['bytes']} bytes")
```

### Click at Coordinates
```python
send('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': 500, 'y': 300, 'button': 'left', 'clickCount': 1})
send('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': 500, 'y': 300, 'button': 'left', 'clickCount': 1})
```

### Click by CSS Selector
```python
send('Runtime.evaluate', {'expression': 'document.querySelector("a.some-link").click()'})
```

### Open New Tab
```python
send('Target.createTarget', {'url': 'https://example.com'})
```

### CDP Screenshot (no scrot needed)
```python
import base64
result = send('Page.captureScreenshot', {'format': 'png'})
with open('/tmp/cdp_shot.png', 'wb') as f:
    f.write(base64.b64decode(result['result']['data']))
```

### Always close WebSocket when done
```python
ws.close()
```

---

## Method 3: xdotool (UI Keyboard/Mouse)

### Get window ID first
```bash
WIN=$(DISPLAY=:99 xdotool search --class chromium | head -1)
DISPLAY=:99 xdotool windowfocus $WIN
```

### Navigate
```bash
DISPLAY=:99 xdotool key ctrl+l
DISPLAY=:99 xdotool type 'https://example.com'
DISPLAY=:99 xdotool key Return

# Back / Forward
DISPLAY=:99 xdotool key alt+Left
DISPLAY=:99 xdotool key alt+Right

# Reload
DISPLAY=:99 xdotool key ctrl+r
```

### Tab Management (by position number, NOT by URL)
```bash
DISPLAY=:99 xdotool key ctrl+1    # Switch to tab 1
DISPLAY=:99 xdotool key ctrl+2    # Switch to tab 2
DISPLAY=:99 xdotool key ctrl+t    # New tab
DISPLAY=:99 xdotool key ctrl+w    # Close current tab
```

### Scrolling
```bash
DISPLAY=:99 xdotool key Page_Down
DISPLAY=:99 xdotool key Page_Up

# Mouse wheel
DISPLAY=:99 xdotool mousemove 640 400
DISPLAY=:99 xdotool click 5    # scroll down
DISPLAY=:99 xdotool click 4    # scroll up
```

### Click at Coordinates
```bash
DISPLAY=:99 xdotool mousemove 500 300 click 1
```

### DevTools
```bash
DISPLAY=:99 xdotool key F12              # Elements
DISPLAY=:99 xdotool key ctrl+shift+j    # Console
```

---

## Decision Guide: CDP vs xdotool

| Task | Best Method |
|---|---|
| Navigate to URL | CDP `Page.navigate` |
| Get console logs | CDP `Log.enable` + events |
| Capture network requests | CDP `Network.enable` + events |
| Get page resources | CDP `Runtime.evaluate` + Performance API |
| Run JavaScript | CDP `Runtime.evaluate` |
| Click by selector | CDP `Runtime.evaluate` + `.click()` |
| Click by coordinates | Either (CDP `Input.*` or xdotool) |
| Scroll | xdotool `Page_Down` or `click 4/5` |
| Switch tabs | xdotool `ctrl+NUMBER` |
| Type text | xdotool `type` |
| Open DevTools | xdotool `ctrl+shift+j` |

---

## Workflow: Observe → Act → Verify
1. Screenshot (`scrot`) → `vision_load` — see current state
2. Act via CDP (fast) or xdotool (UI-level)
3. Screenshot again to verify

---

## Troubleshooting

| Problem | Fix |
|---|---|
| CDP WebSocket 403 | Restart Chromium with `--remote-allow-origins=*` |
| xdotool no effect | Run `windowfocus` first |
| Loader stuck in Agent Zero UI | `pkill -f playwright` to kill orphaned Playwright sessions |
| Tab switch wrong | Use `ctrl+NUMBER` by tab position, not URL |
| Link opens new tab instead of navigating | It had `target="_blank"` — use `ctrl+2` to switch to the new tab |
| Network events empty | Enable `Network.enable` BEFORE navigating, not after |
