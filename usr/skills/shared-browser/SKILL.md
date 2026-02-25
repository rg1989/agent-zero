# Shared Browser Control Skill

## Metadata
- name: shared-browser
- version: 4.3
- description: Control and observe the shared headless Chromium browser via CDP WebSocket — with navigate-with-verification and Observe-Act-Verify workflow
- tags: browser, chromium, cdp, automation, shared
- author: agent-zero

## Overview
A shared Chromium browser runs in headless mode (`--headless=new`) with CDP enabled on port 9222.
Both user and agent interact with the browser exclusively via CDP WebSocket.

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
| Browser | Chromium (`--headless=new`, `--remote-allow-origins=*`) |
| CDP debug API | HTTP + WebSocket port 9222 |

## Prerequisites
Chromium MUST be started with `--remote-allow-origins=*` for CDP WebSocket access.
Already configured in `/a0/apps/shared-browser/startup.sh`.
If CDP returns 403: kill Chromium and restart with that flag.

---

## Method: CDP WebSocket (Programmatic)

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

def click_selector(ws, selector):
    """Click element by CSS selector using CDP Input events (works with trusted event handlers)."""
    js = "(() => { const el = document.querySelector('" + selector + "'); if (!el) return null; const rect = el.getBoundingClientRect(); return {x: rect.left + rect.width/2, y: rect.top + rect.height/2, found: true}; })()"
    result = send(ws, 'Runtime.evaluate', {'expression': js, 'returnByValue': True})
    coords = result.get('result', {}).get('result', {}).get('value')
    if not coords or not coords.get('found'):
        return False
    x, y = coords['x'], coords['y']
    send(ws, 'Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
    send(ws, 'Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
    return True

def eval_js(ws, code, return_value=True):
    """Evaluate JavaScript in page context."""
    result = send(ws, 'Runtime.evaluate', {'expression': code, 'returnByValue': return_value})
    if return_value:
        return result.get('result', {}).get('result', {}).get('value')
    return result

def type_text(ws, text):
    """Type text into focused element via CDP Input events."""
    for char in text:
        send(ws, 'Input.dispatchKeyEvent', {'type': 'keyDown', 'text': char})
        send(ws, 'Input.dispatchKeyEvent', {'type': 'keyUp', 'text': char})
        time.sleep(0.05)

def wait_for_selector(ws, selector, timeout=10):
    """Wait until element matching CSS selector exists in DOM. Essential for SPAs."""
    js = f"document.querySelector('{selector}') !== null"
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = send(ws, 'Runtime.evaluate', {'expression': js, 'returnByValue': True})
        if result.get('result', {}).get('result', {}).get('value'):
            return True
        time.sleep(0.3)
    return False

def get_cookies(ws):
    """Get all cookies for current page."""
    result = send(ws, 'Network.getCookies')
    return result.get('result', {}).get('cookies', [])

def set_cookies(ws, cookies):
    """Set cookies. cookies = [{'name': 'x', 'value': 'y', 'domain': 'example.com'}, ...]"""
    send(ws, 'Network.setCookies', {'cookies': cookies})

def set_user_agent(ws, user_agent):
    """Set custom User-Agent to mimic devices or avoid bot detection."""
    send(ws, 'Emulation.setUserAgentOverride', {'userAgent': user_agent})

def capture_console_logs(ws, duration=2):
    """Enable console capture and collect logs for duration seconds."""
    send(ws, 'Log.enable')
    logs = []
    ws.settimeout(duration)
    try:
        while True:
            msg = json.loads(ws.recv())
            if msg.get('method') == 'Log.entryAdded':
                entry = msg['params']['entry']
                logs.append({'level': entry['level'], 'text': entry['text']})
    except:
        pass
    ws.settimeout(None)
    return logs

def capture_network_traffic(ws, duration=2):
    """Enable network capture and collect requests for duration seconds."""
    send(ws, 'Network.enable')
    requests = []
    ws.settimeout(duration)
    try:
        while True:
            msg = json.loads(ws.recv())
            if msg.get('method') == 'Network.requestWillBeSent':
                req = msg['params']['request']
                requests.append({'url': req['url'], 'method': req['method']})
    except:
        pass
    ws.settimeout(None)
    return requests

def on_console_message(ws, duration=2):
    """Capture real-time console messages (Console domain — includes stack traces)."""
    send(ws, 'Console.enable')
    messages = []
    ws.settimeout(duration)
    try:
        while True:
            msg = json.loads(ws.recv())
            if msg.get('method') == 'Console.messageAdded':
                m = msg['params']['message']
                messages.append({'level': m.get('level'), 'text': m.get('text'), 'url': m.get('url')})
    except:
        pass
    ws.settimeout(None)
    return messages

def get_performance_metrics(ws):
    """Get browser performance metrics (JSHeapUsedSize, NavigationStart, etc.)."""
    send(ws, 'Performance.enable')
    result = send(ws, 'Performance.getMetrics')
    metrics = result.get('result', {}).get('metrics', [])
    return {m['name']: m['value'] for m in metrics}

def capture_dom_snapshot(ws):
    """Capture full DOM snapshot with layout and styling info (more than outerHTML)."""
    result = send(ws, 'DOMSnapshot.captureSnapshot', {
        'computedStyles': ['display', 'visibility', 'opacity', 'color', 'background-color'],
        'includeDOMRects': True
    })
    return result.get('result', {})
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

### CDP Screenshot
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

## Decision Guide: CDP Methods

| Task | Method |
|---|---|
| Navigate to URL | CDP `navigate_and_wait()` |
| Wait for element (SPA) | CDP `wait_for_selector()` |
| Get console logs | CDP `capture_console_logs()` |
| Capture network requests | CDP `capture_network_traffic()` |
| Get page resources | CDP `Runtime.evaluate` + Performance API |
| Run JavaScript | CDP `eval_js()` |
| Click by selector | CDP `click_selector()` (uses Input events — works with trusted handlers) |
| Click by coordinates | CDP `Input.dispatchMouseEvent` |
| Scroll | CDP `eval_js(ws, 'window.scrollBy(0, 500)')` |
| Switch tabs | CDP `Target.activateTarget` |
| Type text | CDP `type_text()` |
| Session/cookies | CDP `get_cookies()` / `set_cookies()` |
| Spoof user agent | CDP `set_user_agent()` |
| Console messages (with stack) | CDP `on_console_message()` |
| Performance metrics | CDP `get_performance_metrics()` |
| Full DOM snapshot | CDP `capture_dom_snapshot()` |

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

**2. ACT**
Choose the appropriate action:
- Navigate: `navigate_and_wait(ws, url)` — NEVER `Page.navigate` + `time.sleep()`
- Click by selector: `click_selector(ws, 'selector')` — uses CDP Input events (works with trusted handlers)
- Click by coordinates: `send(ws, 'Input.dispatchMouseEvent', ...)`
- Type text: `type_text(ws, 'text')`
- Run JavaScript: `eval_js(ws, 'code')`
- Scroll: `eval_js(ws, 'window.scrollBy(0, 500)')`

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
SPA pages (React, Vue, etc.) set `document.readyState = 'complete'` when initial HTML loads, but actual content is rendered by JavaScript after that. Use `wait_for_selector()` to poll for a key element, then screenshot and `vision_load` — visual confirmation catches what readyState misses.

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
| Loader stuck in Agent Zero UI | `pkill -f playwright` to kill orphaned Playwright sessions |
| Tab switch wrong | Use `ctrl+NUMBER` by tab position, not URL |
| Link opens new tab instead of navigating | It had `target="_blank"` — use `ctrl+2` to switch to the new tab |
| Network events empty | Enable `Network.enable` BEFORE navigating, not after |
| `ModuleNotFoundError: No module named 'websocket'` | `websocket-client>=1.9.0` must be installed — it is in `requirements.txt`; rebuild Docker image if needed |
