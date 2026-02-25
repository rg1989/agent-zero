# Shared Browser Control Skill

## Metadata
- name: shared-browser
- version: 4.0
- description: Control and observe the shared Chromium browser on Xvfb :99 via CDP WebSocket and xdotool — with navigate-with-verification and Observe-Act-Verify workflow
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

### CDP Helper Functions (REQUIRED — use these in every CDP session)

```python
import websocket, json, urllib.request, time, base64

def cdp_connect():
    """Connect to the first page tab in Chromium CDP."""
    tabs = json.loads(urllib.request.urlopen('http://localhost:9222/json').read())
    page_tabs = [t for t in tabs if t.get('type') == 'page']
    ws = websocket.create_connection(page_tabs[0]['webSocketDebuggerUrl'])
    return ws

msg_id = [0]
def send(ws, method, params={}):
    """Send CDP command, return response (skip async events)."""
    msg_id[0] += 1
    ws.send(json.dumps({'id': msg_id[0], 'method': method, 'params': params}))
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == msg_id[0]:
            return resp
        # CDP events (no 'id') are skipped — correct for sync polling

def navigate_and_wait(ws, url, timeout=10):
    """
    Navigate to URL via CDP and wait until document.readyState == 'complete'.
    Returns True if page loaded within timeout, False if timed out.
    ALWAYS use this instead of bare Page.navigate + time.sleep().
    """
    send(ws, 'Page.navigate', {'url': url})
    time.sleep(0.1)   # Brief pause so navigation starts before polling readyState
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = send(ws, 'Runtime.evaluate', {
            'expression': 'document.readyState',
            'returnByValue': True
        })
        state = result.get('result', {}).get('result', {}).get('value', '')
        if state == 'complete':
            return True
        time.sleep(0.5)
    return False  # Timed out — caller must screenshot and report state

def verify_navigation(ws, expected_url_contains=None):
    """Read current URL and title after navigation. Optionally assert URL match."""
    result = send(ws, 'Runtime.evaluate', {
        'expression': '({url: location.href, title: document.title})',
        'returnByValue': True
    })
    val = result.get('result', {}).get('result', {}).get('value', {})
    url = val.get('url', '')
    title = val.get('title', '')
    if expected_url_contains and expected_url_contains not in url:
        print(f"WARNING: Expected URL containing '{expected_url_contains}', got: {url}")
    return url, title

def take_screenshot(ws, path='/tmp/shared_browser.png'):
    """Take CDP screenshot and save to path. Use vision_load() to view."""
    result = send(ws, 'Page.captureScreenshot', {'format': 'png'})
    with open(path, 'wb') as f:
        f.write(base64.b64decode(result['result']['data']))
    return path
```

### Full Navigate Workflow (Observe-Act-Verify)

```python
ws = cdp_connect()
try:
    # 1. OBSERVE — screenshot to see current state before acting
    take_screenshot(ws)
    # vision_load('/tmp/shared_browser.png')

    # 2. ACT — navigate with built-in readyState wait (NEVER bare Page.navigate + sleep)
    loaded = navigate_and_wait(ws, 'https://example.com')

    # 3. VERIFY — confirm the right page was reached
    if loaded:
        url, title = verify_navigation(ws, expected_url_contains='example.com')
        take_screenshot(ws)
        # vision_load('/tmp/shared_browser.png')
        print(f"Success: {title} — {url}")
    else:
        take_screenshot(ws)
        # vision_load('/tmp/shared_browser.png')
        print("WARNING: Page did not reach readyState=complete within 10s — see screenshot")
finally:
    ws.close()
```

### Run JavaScript
```python
result = send(ws, 'Runtime.evaluate', {'expression': 'document.title', 'returnByValue': True})
title = result['result']['result']['value']
```

### Get Console Errors (existing page)
```python
result = send(ws, 'Runtime.evaluate', {
    'expression': '({title: document.title, url: location.href})',
    'returnByValue': True
})
val = result['result']['result']['value']
```

### Capture LIVE Network + Console (must enable BEFORE navigation)
```python
send(ws, 'Network.enable')
send(ws, 'Log.enable')
navigate_and_wait(ws, 'https://example.com')   # REQUIRED — do not use bare Page.navigate + sleep here

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
result = send(ws, 'Runtime.evaluate', {
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
send(ws, 'Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': 500, 'y': 300, 'button': 'left', 'clickCount': 1})
send(ws, 'Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': 500, 'y': 300, 'button': 'left', 'clickCount': 1})
```

### Click by CSS Selector
```python
send(ws, 'Runtime.evaluate', {'expression': 'document.querySelector("a.some-link").click()'})
```

### Open New Tab
```python
send(ws, 'Target.createTarget', {'url': 'https://example.com'})
```

### CDP Screenshot (no scrot needed)
```python
import base64
result = send(ws, 'Page.captureScreenshot', {'format': 'png'})
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
| Navigate to URL | CDP `navigate_and_wait()` |
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

**RULE: ALWAYS take a screenshot and vision_load BEFORE every browser action.**
This is not optional. The screenshot is how the agent sees current state.

### Step-by-step

**1. OBSERVE**
```python
take_screenshot(ws)       # CDP screenshot
# vision_load('/tmp/shared_browser.png')   # Load into vision — see state
```
or via scrot (no CDP connection needed):
```bash
DISPLAY=:99 scrot /tmp/shared_browser.png -o
```

**2. ACT**
Choose the appropriate action:
- Navigate: `navigate_and_wait(ws, url)` — NEVER `Page.navigate` + `time.sleep()`
- Click by selector: `send(ws, 'Runtime.evaluate', {'expression': 'document.querySelector("selector").click()'})`
- Click by coordinates: `send(ws, 'Input.dispatchMouseEvent', ...)` or `xdotool mousemove X Y click 1`
- Type text: `xdotool type 'text'`
- Scroll: `xdotool key Page_Down`

**3. VERIFY**
After every action:
```python
take_screenshot(ws)
# vision_load('/tmp/shared_browser.png')
```
After navigation specifically, also verify URL and title:
```python
url, title = verify_navigation(ws, expected_url_contains='expected-domain.com')
print(f"{title} — {url}")
```

### Anti-Patterns (NEVER DO)
- `Page.navigate` + `time.sleep(N)`: fragile timing — use `navigate_and_wait()`
- Acting without observing: always screenshot first
- Assuming page state from a prior action: state may have changed
- Using `browser_agent` tool: spawns separate Playwright instance

---

## Common Pitfalls

### Pitfall 1: navigate_and_wait returns True but screenshot shows blank or spinner
SPA pages (React, Vue, etc.) set `document.readyState = 'complete'` when initial HTML loads, but actual content is rendered by JavaScript after that. Always screenshot and `vision_load` after navigate — visual confirmation catches what readyState misses.

**Warning signs:** `navigate_and_wait` returns `True` but screenshot shows a blank or spinner page.

### Pitfall 2: navigate_and_wait returns immediately (false positive from old page)
`Page.navigate` returns before navigation commits. The old page's `readyState` may still be `'complete'` during the brief window before the new page starts loading. A `time.sleep(0.1)` after `Page.navigate` is included in the function for this reason.

**Warning signs:** `navigate_and_wait` returns in under 100ms for a URL that clearly takes more than 1s to load.

### Pitfall 3: WebSocket left open between code blocks
CDP allows multiple simultaneous connections, but stale connections cause unexpected results. Always use try/finally to guarantee cleanup:
```python
ws = cdp_connect()
try:
    navigate_and_wait(ws, url)
    # ... other actions ...
finally:
    ws.close()
```

**Warning signs:** CDP commands return unexpected results or stale page data.

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
| `ModuleNotFoundError: No module named 'websocket'` | `websocket-client>=1.9.0` must be installed — it is in `requirements.txt`; rebuild Docker image if needed |
