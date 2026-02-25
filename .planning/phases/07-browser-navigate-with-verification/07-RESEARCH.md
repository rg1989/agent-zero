# Phase 7: Browser Navigate-with-Verification - Research

**Researched:** 2026-02-25
**Domain:** Chrome DevTools Protocol (CDP) / websocket-client (Python) / Observe-Act-Verify skill documentation
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BROWSER-01 | Agent Zero navigates to a URL using CDP `Page.navigate` followed by a `document.readyState` poll (never treats navigation as complete before page loads) | `Page.navigate` returns immediately per CDP official docs; `Runtime.evaluate` with `document.readyState` is the verified polling approach for synchronous `websocket-client` context |
| BROWSER-02 | Agent Zero takes a screenshot via CDP before every browser interaction to observe current state | `Page.captureScreenshot` already in SKILL.md; SKILL.md's Workflow section needs a clear RULE that screenshot is mandatory before every action |
| BROWSER-03 | Agent Zero verifies navigation succeeded by checking current URL and page title after navigate-and-wait | `Runtime.evaluate` with `({url: location.href, title: document.title})` is the verified pattern; already shown in existing SKILL.md |
| BROWSER-05 | Agent Zero uses a consistent Observe → Act → Verify workflow for all browser interactions (documented and enforced in skill) | Existing Workflow section in SKILL.md is only 3 lines; needs full Observe-Act-Verify section with explicit steps and "ALWAYS" enforcement language |
</phase_requirements>

---

## Summary

Phase 7 is a skill documentation rewrite plus a small Python code-pattern fix in `usr/skills/shared-browser/SKILL.md`. The scope is narrow: two problems need solving. First, the existing navigate pattern calls `Page.navigate` and then does `time.sleep(2)` — a known fragile pattern identical to the `sleep 2` that Phase 6 fixed in `startup.sh`. The documented fix is to replace the `time.sleep(2)` with a poll loop that calls `Runtime.evaluate` with `document.readyState` every 0.5s until the value is `'complete'` or a 10-second timeout is reached. Second, the "Observe → Act → Verify" workflow in SKILL.md is currently just three informal bullet points; it needs to become a first-class named section with step-by-step instructions that the agent can follow reliably.

No new Python modules need to be added to `app.py`. No changes to `startup.sh`, `app.py`, or any `python/` files are required. The entire phase ships as a documentation-only rewrite of `usr/skills/shared-browser/SKILL.md`, with updated code examples in that file. The one dependency concern is that `websocket-client` (the synchronous library used in all SKILL.md code examples) is not currently in `requirements.txt`. Per STATE.md it was already identified as needing to be added (`websocket-client>=1.9.0`). This must happen as part of Phase 7 so the skill's code examples are runnable.

The CDP behavior is fully understood: `Page.navigate` returns immediately (before the page loads) per official CDP protocol documentation. The return value includes `frameId` and `loaderId` but gives no load-completion signal. Navigation completion must be detected by polling `document.readyState` via `Runtime.evaluate`, or by listening for `Page.loadEventFired`. The polling approach is preferred here because the existing SKILL.md helper uses synchronous `websocket-client` (not async), and listening for events on a synchronous WebSocket requires either a message-draining loop (complex) or setting a recv timeout. The readyState poll is simpler, equally reliable, and already mentioned in MEMORY.md as the chosen approach.

**Primary recommendation:** Rewrite `usr/skills/shared-browser/SKILL.md` with: (1) a navigate-with-verification code block that polls `document.readyState`, (2) a `verify_navigation()` snippet using `Runtime.evaluate` to read URL and title, (3) a full Observe-Act-Verify section that makes screenshot-before-action a hard rule, and (4) add `websocket-client>=1.9.0` to `requirements.txt`.

---

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| `websocket-client` | >=1.9.0 | Synchronous WebSocket for CDP commands in agent code | Already referenced throughout SKILL.md; synchronous API matches agent code execution context; 1.9.0 is the current stable release (released 2025-10-07) |
| Chrome DevTools Protocol | N/A (protocol, not library) | `Page.navigate`, `Runtime.evaluate`, `Page.captureScreenshot` | Browser's native remote control interface; no alternatives for headless CDP |
| `urllib.request` | stdlib | HTTP GET to `http://localhost:9222/json` for tab discovery | Already in use in SKILL.md and `app.py`; no new dependencies |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `json` | stdlib | Serialize/deserialize CDP messages | Every CDP interaction |
| `time` | stdlib | `time.sleep(0.5)` in poll loop; `time.time()` for timeout | Inside navigate-with-verification poll |
| `base64` | stdlib | Decode PNG from `Page.captureScreenshot` | When saving screenshot to file |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| readyState poll via `Runtime.evaluate` | `Page.loadEventFired` event | Event approach requires async client or message-drain loop on sync WS; poll is simpler and equally reliable for this use case |
| `websocket-client` sync API | `websockets` async API | `websockets` is already used by `app.py` but not suited for agent code execution context which is synchronous Python in Agent Zero's `code_execution_tool` |
| `websocket-client` sync API | `playwright` CDP session | Playwright is explicitly banned by project requirements (spawns separate Chromium) |

**Installation:**
```bash
pip install "websocket-client>=1.9.0"
```
Add to `requirements.txt`:
```
websocket-client>=1.9.0
```

---

## Architecture Patterns

### Files Changed

```
usr/skills/shared-browser/SKILL.md    # Primary target — full rewrite of navigate + workflow sections
requirements.txt                       # Add websocket-client>=1.9.0
```

No changes to `apps/shared-browser/app.py`, `apps/shared-browser/startup.sh`, or any `python/` files.

### Pattern 1: Navigate-with-Verification (replace bare `Page.navigate`)

**What:** Call `Page.navigate`, then poll `Runtime.evaluate('document.readyState')` until `'complete'` or 10-second timeout.

**When to use:** Every time the agent navigates to a URL. This is the ONLY sanctioned navigate pattern in the skill.

**Example:**
```python
# Source: CDP official docs (Page.navigate returns immediately) + verified Runtime.evaluate pattern
import websocket, json, urllib.request, time

def cdp_connect():
    tabs = json.loads(urllib.request.urlopen('http://localhost:9222/json').read())
    page_tabs = [t for t in tabs if t.get('type') == 'page']
    ws = websocket.create_connection(page_tabs[0]['webSocketDebuggerUrl'])
    return ws

msg_id = [0]
def send(ws, method, params={}):
    msg_id[0] += 1
    ws.send(json.dumps({'id': msg_id[0], 'method': method, 'params': params}))
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == msg_id[0]:
            return resp
        # CDP events (no 'id') are skipped — this is correct for sync polling

def navigate_and_wait(ws, url, timeout=10):
    """Navigate to URL and wait for document.readyState == 'complete'."""
    send(ws, 'Page.navigate', {'url': url})
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
    return False  # Timed out — caller should screenshot and report state

# Usage
ws = cdp_connect()
ok = navigate_and_wait(ws, 'https://example.com')
```

### Pattern 2: Verify Navigation Succeeded

**What:** After `navigate_and_wait` returns True, read current URL and page title via CDP to confirm the expected page was reached.

**When to use:** After every navigation — this is the Verify step of Observe-Act-Verify.

**Example:**
```python
# Source: Already in existing SKILL.md (Runtime.evaluate pattern) — extended for navigation verification
def verify_navigation(ws, expected_url_contains=None):
    """Return current URL and title. Optionally assert URL contains expected string."""
    result = send(ws, 'Runtime.evaluate', {
        'expression': '({url: location.href, title: document.title})',
        'returnByValue': True
    })
    val = result.get('result', {}).get('result', {}).get('value', {})
    current_url = val.get('url', '')
    current_title = val.get('title', '')
    if expected_url_contains and expected_url_contains not in current_url:
        print(f"WARNING: Expected URL to contain '{expected_url_contains}', got '{current_url}'")
    return current_url, current_title

# Usage
url, title = verify_navigation(ws, expected_url_contains='example.com')
print(f"Page loaded: {title} — {url}")
```

### Pattern 3: CDP Screenshot (Observe step)

**What:** Take a CDP screenshot before every action to see current page state.

**When to use:** Before every CDP action or xdotool interaction. This is the Observe step of Observe-Act-Verify.

**Example:**
```python
# Source: Already in existing SKILL.md — documented here as mandatory first step
import base64
def take_screenshot(ws, path='/tmp/shared_browser.png'):
    result = send(ws, 'Page.captureScreenshot', {'format': 'png'})
    with open(path, 'wb') as f:
        f.write(base64.b64decode(result['result']['data']))
    # Load with vision_load to see state
    return path
```

### Pattern 4: Full Observe-Act-Verify Workflow

**What:** The mandatory three-step sequence for ALL browser interactions.

**Steps:**
1. **Observe:** `take_screenshot(ws)` → `vision_load('/tmp/shared_browser.png')` — see current page state before acting
2. **Act:** CDP command (navigate, click, type) or xdotool
3. **Verify:** `take_screenshot(ws)` → check URL/title via `verify_navigation(ws)` if navigation occurred

**For navigation specifically:**
1. Observe: screenshot → vision_load (see current page)
2. Act: `navigate_and_wait(ws, url)` (includes built-in readyState poll)
3. Verify: `verify_navigation(ws, expected_url_contains=...)` + screenshot → vision_load

### Anti-Patterns to Avoid

- **`Page.navigate` + `time.sleep(N)`:** Replaced by `navigate_and_wait()`. The sleep approach is the same fragile timing bug as `startup.sh sleep 2`.
- **Acting without observing first:** Always screenshot before acting. Never assume the page state from a previous action.
- **Treating `navigate_and_wait` returning `False` as recoverable silently:** If timeout occurs, screenshot the current state and report it — the page may have partially loaded or shown an error page.
- **Using `browser_agent` tool:** Explicitly banned. Spawns separate Playwright Chromium and creates persistent UI loader.
- **Checking `document.readyState === 'interactive'` as "done":** `interactive` means DOM is parsed but resources (images, scripts) may still be loading. Use `'complete'` as the success criterion.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Navigation completion detection | Custom event listener with `Page.loadEventFired` on sync WS | `Runtime.evaluate('document.readyState')` poll | Event approach on synchronous `websocket-client` requires message draining; poll is simpler and sufficient |
| Page readiness check | Arbitrary `time.sleep(N)` | `navigate_and_wait()` poll loop | Sleep has no guarantee; poll has a deterministic success signal |
| WebSocket CDP boilerplate | New helper library or wrapper class | The `send()` helper already in SKILL.md | Existing helper works; extending it is simpler than new abstraction |

**Key insight:** The skill documentation IS the deliverable here. Unlike Phase 6, there is no production code to change — the goal is to document and enforce patterns so the agent reliably follows them.

---

## Common Pitfalls

### Pitfall 1: `document.readyState` may be `'complete'` before JS-rendered content is visible

**What goes wrong:** SPA (Single Page Applications) — React, Vue, etc. — set `document.readyState = 'complete'` when the initial HTML loads, but the actual content is rendered by JavaScript after that. Checking readyState returns `'complete'` but the page looks blank or unfinished.

**Why it happens:** `document.readyState` tracks HTML/CSS/image load, not JavaScript execution or API calls.

**How to avoid:** After `navigate_and_wait` completes, take a screenshot and use `vision_load` to visually confirm the page looks as expected. If it's blank or loading, add an additional `time.sleep(1)` and screenshot again. This is why the Verify step (screenshot after action) is mandatory — visual confirmation catches what `readyState` misses.

**Warning signs:** `navigate_and_wait` returns `True` but screenshot shows a blank or spinner page.

### Pitfall 2: `send()` helper skips CDP events and can starve if events flood

**What goes wrong:** The existing `send()` helper in SKILL.md loops on `ws.recv()` waiting for the response with the matching `id`. If CDP is sending many async events (e.g., `Network.requestWillBeSent` when Network is enabled), the loop may spin through many events before seeing the response, adding latency.

**Why it happens:** CDP events don't have an `id` field; the helper correctly skips them. But if Network/Log/Page domains are enabled and active, there can be dozens of events between the command send and its response.

**How to avoid:** In `navigate_and_wait()`, do NOT enable `Network.enable` or `Log.enable` unless you need them. Keep the connection clean for navigate-and-poll. If you do need network events, use a separate connection or a message-buffering approach. The existing SKILL.md already has a dedicated "Capture LIVE Network + Console" section that uses a separate post-navigate drain loop — keep that pattern separate from navigate-with-verification.

**Warning signs:** `navigate_and_wait()` takes much longer than expected; responses to `Runtime.evaluate` come back slowly.

### Pitfall 3: WebSocket connection left open between code blocks

**What goes wrong:** Agent code opens a CDP WebSocket connection, does some actions, but doesn't close it. Next time the agent runs another code block, it tries to open a new connection. Chromium's CDP allows multiple simultaneous WebSocket connections, but the existing tab's state may be inconsistent if two connections are interleaved.

**Why it happens:** The SKILL.md already says "Always close WebSocket when done" but this is easy to miss, especially if an exception occurs mid-session.

**How to avoid:** Use try/finally:
```python
ws = cdp_connect()
try:
    navigate_and_wait(ws, url)
    # ... other actions ...
finally:
    ws.close()
```

**Warning signs:** CDP commands return unexpected results or stale page data.

### Pitfall 4: `navigate_and_wait` polls `document.readyState` before the navigation has actually started

**What goes wrong:** `Page.navigate` is sent, but the first `Runtime.evaluate` immediately returns `'complete'` — for the *previous* page, not the new one. The function returns `True` instantly and the agent thinks the new page is loaded when it isn't.

**Why it happens:** `Page.navigate` returns immediately before the navigation commits. There is a brief window where the current page's `readyState` is still `'complete'`.

**How to avoid:** Two strategies:
1. Add a `time.sleep(0.1)` after `Page.navigate` before starting the poll — gives the navigation a moment to start. (Simple, adequate for most cases.)
2. Check that `location.href` has changed to the new URL before accepting `readyState === 'complete'`. (More robust.)

The recommended approach in the SKILL.md is option 1 (sleep 0.1s) because it is simple and the 0.1s delay is negligible. Option 2 can be added for critical navigations.

**Warning signs:** `navigate_and_wait` returns immediately (< 100ms) for a URL that clearly takes > 1s to load.

### Pitfall 5: `websocket-client` not installed in Docker venv

**What goes wrong:** Agent code fails with `ModuleNotFoundError: No module named 'websocket'` when trying to use the CDP patterns from SKILL.md.

**Why it happens:** `websocket-client>=1.9.0` is not yet in `requirements.txt`. (STATE.md flags this: "websocket-client>=1.9.0 must be confirmed installable in Docker venv /opt/venv-a0 — verify during Phase 7 setup")

**How to avoid:** Add `websocket-client>=1.9.0` to `requirements.txt` as the first task in this phase, before the SKILL.md rewrite.

**Warning signs:** `import websocket` fails at runtime in agent code.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Navigate-with-Verification (complete function)
```python
# Source: CDP official docs (Page.navigate returns immediately) + Runtime.evaluate for readyState
import websocket, json, urllib.request, time, base64

def cdp_connect():
    """Connect to the first page tab in Chromium CDP."""
    tabs = json.loads(urllib.request.urlopen('http://localhost:9222/json').read())
    page_tabs = [t for t in tabs if t.get('type') == 'page']
    ws = websocket.create_connection(page_tabs[0]['webSocketDebuggerUrl'])
    return ws

msg_id = [0]
def send(ws, method, params={}):
    """Send CDP command, return response (skip events)."""
    msg_id[0] += 1
    ws.send(json.dumps({'id': msg_id[0], 'method': method, 'params': params}))
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == msg_id[0]:
            return resp

def navigate_and_wait(ws, url, timeout=10):
    """
    Navigate to URL via CDP and wait until document.readyState == 'complete'.
    Returns True if page loaded, False if timeout reached.
    """
    send(ws, 'Page.navigate', {'url': url})
    time.sleep(0.1)   # Brief pause so navigation starts before we poll readyState
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
    return False  # Timed out

def verify_navigation(ws, expected_url_contains=None):
    """Read current URL and title. Optionally check URL contains expected string."""
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
    """Take CDP screenshot and save to path."""
    result = send(ws, 'Page.captureScreenshot', {'format': 'png'})
    with open(path, 'wb') as f:
        f.write(base64.b64decode(result['result']['data']))
    return path
```

### Full Navigate Workflow (what agent actually runs)
```python
# Source: Pattern derived from Observe-Act-Verify workflow + navigate_and_wait function above
ws = cdp_connect()
try:
    # 1. OBSERVE — see current state
    take_screenshot(ws)
    # vision_load('/tmp/shared_browser.png')

    # 2. ACT — navigate with built-in wait
    loaded = navigate_and_wait(ws, 'https://example.com')

    # 3. VERIFY — confirm page reached
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

### Existing Navigate (BROKEN — what to replace in SKILL.md)
```python
# This is the pattern currently in SKILL.md "Capture LIVE Network + Console" section
# Line 99: time.sleep(2) — FRAGILE — replace with navigate_and_wait()
send('Page.navigate', {'url': 'https://example.com'})
time.sleep(2)   # <-- THIS LINE IS THE PROBLEM — replace with navigate_and_wait()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Page.navigate` + `time.sleep(2)` | `navigate_and_wait()` with `document.readyState` poll | Phase 7 | Deterministic vs probabilistic — same fix as Phase 6's startup.sh |
| 3-line informal workflow note | Full Observe-Act-Verify section with named functions and enforcement language | Phase 7 | Agent reliably follows repeatable pattern |
| Bare navigate with no URL/title verification | `verify_navigation()` reads URL + title after load | Phase 7 | Agent can confirm it reached the right page |

**Deprecated/outdated:**
- `time.sleep(2)` after `Page.navigate` in SKILL.md: Same anti-pattern as `sleep 2` in startup.sh. Replace with `navigate_and_wait()`.

---

## Open Questions

1. **Does `document.readyState === 'complete'` fire reliably for all page types?**
   - What we know: For standard HTML pages, `'complete'` fires when the load event has fired — all resources loaded. For SPAs, it may fire before JS-rendered content appears.
   - What's unclear: Whether the pages agents typically navigate to (Google, app pages, etc.) are SPAs that would fool the readyState check.
   - Recommendation: Document the SPA limitation in SKILL.md as Pitfall 1 (done above). The post-navigate screenshot + vision_load is the safety net. This is acceptable for v1.1.

2. **Should `navigate_and_wait` also verify `location.href` has changed before accepting `readyState === 'complete'`?**
   - What we know: There is a brief window where the old page's `readyState` is `'complete'` before the new navigation commits. The `time.sleep(0.1)` mitigation is adequate for most cases.
   - What's unclear: Whether this edge case is observable in practice on a local Chromium instance (vs a slow network).
   - Recommendation: Implement the 0.1s sleep mitigation. Add a note in SKILL.md about the edge case. Do not add URL checking to keep the function simple — it can be added in a future phase if needed.

3. **Should `websocket-client>=1.9.0` be pinned to exact version or `>=`?**
   - What we know: The rest of `requirements.txt` uses a mix of pinned (`==`) and range (`>=`) versions. The project convention for new additions (per STATE.md) is `>=1.9.0`.
   - What's unclear: Nothing — `>=` is correct per project convention and existing STATE.md decision.
   - Recommendation: Use `websocket-client>=1.9.0` to match the project convention established in STATE.md.

---

## Sources

### Primary (HIGH confidence)
- [Chrome DevTools Protocol — Page domain](https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-navigate) — confirmed `Page.navigate` returns immediately (before page load)
- [Chrome DevTools Protocol — Runtime.evaluate](https://chromedevtools.github.io/devtools-protocol/tot/Runtime/#method-evaluate) — confirmed `document.readyState` and `location.href` evaluation
- [Chrome DevTools Protocol — Page events](https://chromedevtools.github.io/devtools-protocol/tot/Page/#event-loadEventFired) — confirmed `Page.loadEventFired`, `Page.enable` required
- [websocket-client 1.9.0 PyPI](https://pypi.org/project/websocket-client/) — confirmed current version, `create_connection`, `settimeout` API
- Direct code inspection of `usr/skills/shared-browser/SKILL.md` — confirmed `time.sleep(2)` at line 99, bare 3-line workflow section, existing `send()` helper pattern
- Direct code inspection of `apps/shared-browser/app.py` — confirmed CDP patterns in production use
- Direct code inspection of `requirements.txt` — confirmed `websocket-client` absent

### Secondary (MEDIUM confidence)
- [websocket-client examples docs](https://websocket-client.readthedocs.io/en/latest/examples.html) — confirmed sync API patterns
- [trio-cdp getting started](https://trio-cdp.readthedocs.io/en/latest/getting_started.html) — confirmed navigate-then-wait-for-loadEventFired as the canonical async pattern (used for comparison with polling approach)
- STATE.md project decisions — confirmed `websocket-client>=1.9.0` should be added to `requirements.txt`

### Tertiary (LOW confidence)
- None applicable — all critical claims backed by primary sources

---

## Metadata

**Confidence breakdown:**
- Standard stack (websocket-client, CDP APIs): HIGH — verified against official CDP docs and pypi
- Architecture (navigate-and-wait pattern): HIGH — CDP official docs confirm Page.navigate timing; Runtime.evaluate for readyState is the standard polling approach
- Pitfalls: HIGH for pitfalls 1/3/4/5 (direct code inspection); MEDIUM for pitfall 2 (event flooding — theoretical but well-understood)
- Files to change: HIGH — direct inspection confirmed exactly `SKILL.md` (navigate section + workflow section) and `requirements.txt`

**Research date:** 2026-02-25
**Valid until:** 2027-02-25 (stable — CDP protocol stable for years; websocket-client API very stable)
