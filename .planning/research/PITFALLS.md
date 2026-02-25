# Pitfalls Research

**Domain:** CDP browser control + interactive CLI subprocess control in a Docker-based LLM agent
**Researched:** 2026-02-25
**Confidence:** HIGH (based on direct codebase analysis of existing implementation + training knowledge of CDP/PTY patterns)

---

## Critical Pitfalls

### Pitfall 1: Page.navigate Returns Before the Page Has Loaded

**What goes wrong:**
`Page.navigate` resolves its CDP response as soon as the navigation *starts* — not when the page finishes loading. Agent Zero currently calls `_run(_cdp("Page.navigate", {"url": url}))` and immediately invalidates the screenshot cache. The agent takes a screenshot milliseconds later and sees a blank white page or the previous page still rendering. It concludes navigation "worked" or failed incorrectly.

**Why it happens:**
CDP's `Page.navigate` method returns the frameId and loaderId on the initial HTTP redirect/request, not on DOMContentLoaded or load events. Developers assume "got a response = page is ready." The existing `app.py` does exactly this — no wait after navigate.

**How to avoid:**
After calling `Page.navigate`, subscribe to `Page.loadEventFired` on the same WebSocket connection before navigating, then wait for that event (or `Page.frameStoppedLoading` on the returned frameId). A simpler practical approach: call `Page.enable` first, then navigate, then poll `/json` URL field + `Runtime.evaluate document.readyState` with a 2-second back-off loop until `readyState === 'complete'`. Cap at 10 seconds with a hard timeout, then proceed anyway.

**Warning signs:**
- Screenshots after navigation show loading spinner or previous page
- Agent reports "navigation succeeded" but URL check shows old URL still
- Intermittent test failures where navigation "works" only when the next step has a delay

**Phase to address:** BROWSER-01 (CDP navigation fix) and BROWSER-03 (verification step)

---

### Pitfall 2: CDP WebSocket 403 Because `--remote-allow-origins` Is Missing or Wrong

**What goes wrong:**
Chromium's CDP WebSocket endpoint enforces an `Origin` header check. Without `--remote-allow-origins=*`, any WebSocket connection from a non-localhost origin (including the Flask app running inside the same container but connecting as a Python `websockets` client) gets a 403. The HTTP `/json` endpoint still responds (port is open), making developers think CDP is available — only WebSocket connections fail.

**Why it happens:**
The flag was added in Chromium ~108. Docker deployments often reuse old startup scripts. The current `startup.sh` already includes `--remote-allow-origins=*`, but if anyone changes the startup command, removes that flag, or Chromium restarts via a different mechanism (supervisor, app manager restart), the flag can be lost.

**How to avoid:**
- Treat `--remote-allow-origins=*` as a hard requirement, not a suggestion. Assert it in `startup.sh` comments and in the skill doc.
- Add a health check on app startup: hit `/json` with `urllib.request`, then also attempt a WebSocket handshake. If WebSocket fails but HTTP succeeds, log "CDP WebSocket 403 — check `--remote-allow-origins=*` flag."
- Keep the flag in a single place (`startup.sh`) — never reconstruct the Chromium launch command inline anywhere else.

**Warning signs:**
- `websockets.exceptions.InvalidStatusCode: 403` in Flask logs
- `/json` returns tabs successfully but every `_cdp()` call raises an exception
- Works when testing manually with `curl` but fails from Python code

**Phase to address:** BROWSER-04 (Chromium CDP startup fix)

---

### Pitfall 3: Per-Request CDP WebSocket Reconnection Is Fragile Under Load

**What goes wrong:**
The current `_cdp()` helper opens a new WebSocket connection, sends one command, waits for its response, and closes the connection — every single call. Under concurrent requests (polling screenshot + clicking + navigating simultaneously), multiple goroutines race for the same CDP tab. Chrome CDPs accepts multiple simultaneous connections but routes events by connection; closing a connection mid-navigation loses events (like `loadEventFired`) that were fired while waiting on a different command. This also adds 50-100ms of TLS+handshake latency per call.

**Why it happens:**
Stateless per-request design is simpler to write but ignores that CDP is a stateful, event-driven protocol. The pattern was chosen in the current `app.py` as the simplest thing that works.

**How to avoid:**
Use a persistent, module-level CDP WebSocket connection with a message dispatcher keyed by `msg_id`. Accept events into a separate queue. For this project's scale (single-user, low concurrency), a threading.Lock around a single persistent connection is sufficient. If that's too complex for the scope, at minimum ensure navigation waits use a dedicated connection kept open for the duration of the load wait, not the shared fire-and-forget helper.

**Warning signs:**
- Occasional `ConnectionClosedError` or `TimeoutError` in CDP calls during navigation
- Screenshots return stale data even though the browser has moved to a new page
- Race condition symptoms: sometimes works, sometimes doesn't, based on timing

**Phase to address:** BROWSER-01, with a note that a persistent connection is ideal but the per-request approach is acceptable if navigation wait is added

---

### Pitfall 4: `claude` CLI Prompt Detection Using Idle-Timeout Is Unreliable

**What goes wrong:**
The existing `TTYSession.read_full_until_idle()` collects output until there's been `idle_timeout` seconds of silence. For `claude` CLI, this breaks in two ways: (1) Claude streaming responses sometimes pauses mid-sentence for 1-2 seconds during tool calls or thinking, causing premature "done" detection; (2) The final prompt (e.g. `>` or the blinking cursor prompt state) produces no text at all — the idle timeout never fires because there's no further output to stop.

**Why it happens:**
Idle-timeout is designed for shell commands with deterministic end states. Claude CLI is a streaming LLM output tool — it has natural pauses that look like "done" but aren't, and its completion state is a UI cursor/prompt, not a trailing newline.

**How to avoid:**
Detect completion by matching the specific terminal prompt pattern that `claude` CLI renders when it's waiting for input. Inspect the raw PTY output: the claude CLI (Ink/React-based TUI) renders a visual prompt character sequence at the end of output — typically something like a `>` or a specific ANSI escape sequence indicating the input prompt is active. Use `read_chunks_until_idle` with a longer idle timeout (3-4s) AND add a regex check on the last 200 chars of accumulated output for the prompt marker. Do not rely on idle-timeout alone.

**Warning signs:**
- Agent receives partial responses (truncated mid-sentence)
- Agent sends the next prompt to claude before it has finished generating
- claude receives double input — one prompt while still processing, one after
- Infinite wait when claude is done but the prompt detection never fires

**Phase to address:** CLAUDE-02 and CLAUDE-03

---

### Pitfall 5: ANSI Escape Sequences Corrupt Claude CLI Output Parsing

**What goes wrong:**
Claude CLI is built with Ink (React for terminal). Its output is wrapped in ANSI escape sequences for colors, cursor positioning, and clearing lines. When the agent reads this output and tries to parse it as plain text, it gets garbage like `\x1b[2K\x1b[1A\x1b[2K` mixed into the response. If the agent tries to extract claude's answer by looking for its own prompt echoed back, the echo is also ANSI-wrapped.

**Why it happens:**
PTY output is raw terminal bytes. ANSI stripping is not automatic. The existing `tty_session.py`'s `_pump_stdout` reads raw chunks and decodes them as UTF-8 but does not strip ANSI codes. The `shell_ssh.py`'s `clean_string` function handles some cases for shell use but may not handle all of Ink's escape sequences.

**How to avoid:**
Apply an ANSI stripping pass before returning output to the agent. Use the `re.sub(r'\x1b\[[0-9;]*[mGKHFABCDEFJ]', '', text)` pattern, or use the `strip-ansi` equivalent. Also strip carriage returns (`\r`) which PTY output uses liberally. Apply this in the claude-specific wrapper layer, not in `TTYSession` itself (other uses of TTYSession may need ANSI intact).

**Warning signs:**
- Agent output contains `\x1b[` or `ESC[` character sequences
- LLM gets confused by "weird characters" in tool call responses
- Response length is grossly inflated compared to what claude actually said

**Phase to address:** CLAUDE-02 (output reading) and CLAUDE-05 (skill documentation)

---

### Pitfall 6: Claude CLI Session Reuse Fails After claude Exits or Times Out

**What goes wrong:**
Agent Zero might keep a `TTYSession` reference from a previous claude interaction and send new input into it after claude has exited (due to timeout, error, or the user's inactivity timer). The PTY master fd becomes an orphan — writes succeed (the OS buffers them) but nothing reads them. From the agent's perspective, it sent the prompt but waits forever for output.

**Why it happens:**
`TTYSession` does not detect when the child process exits unless you call `wait()` or check `returncode`. The `_pump_stdout` coroutine exits silently when it reads EOF, leaving `self._buf` as an empty queue. The session object still exists and `send()` succeeds (it just writes to a closed PTY master that the OS allows).

**How to avoid:**
Track process liveness. After `_pump_stdout` receives EOF, set a flag (`self._eof = True`). In `read()` / `read_full_until_idle()`, return `None` immediately when `_eof` is True after draining the remaining queue. In the claude skill wrapper, always check `session.eof` before sending and restart the session if needed. Additionally, claude CLI has a configurable timeout — set it explicitly with `--timeout` or design sessions to be short-lived (one task per session).

**Warning signs:**
- Hang after a second prompt is sent to claude
- No output returned but no error raised
- Process table shows no `claude` process but `TTYSession._proc.returncode` is still `None`

**Phase to address:** CLAUDE-04 (multi-turn sessions)

---

### Pitfall 7: Chromium in headless=new Mode Has Different CDP Behavior Than Headed Mode

**What goes wrong:**
The current `startup.sh` uses `--headless=new` (Chromium's new headless mode introduced in M112, replacing the legacy `--headless` / `--headless=old`). New headless mode fixes many rendering issues but has subtle CDP differences: `Page.captureScreenshot` with `fromSurface: true` is required (the current code has this correctly), but `Emulation.setDeviceMetricsOverride` behaves differently — viewport changes may not take effect immediately, requiring a subsequent `Page.navigate` or `Page.reload` to actually re-render at the new size.

**Why it happens:**
Headless=new uses a compositing pipeline that separates the virtual display from the rendering surface. Viewport emulation changes are queued but not flushed until the next paint cycle, which only happens on navigation or explicit repaint triggers.

**How to avoid:**
After `Emulation.setDeviceMetricsOverride`, do not rely on immediate screenshot reflecting the new size. Either follow it with `Page.navigate` to the current URL (forces repaint) or add a `Runtime.evaluate` with `window.dispatchEvent(new Event('resize'))` as a softer trigger. Test the resize flow explicitly during BROWSER-04 implementation.

**Warning signs:**
- Viewport resize API returns success but screenshot still shows old dimensions
- Tests pass immediately after a fresh navigation but fail when resize is the only action

**Phase to address:** BROWSER-04 (Chromium startup/config)

---

### Pitfall 8: CDP Tab Selection Gets the Wrong Target After Multi-Tab or App-Related Navigation

**What goes wrong:**
`_get_ws_url()` always picks `tabs[0]` from `/json`. This is the first tab in Chromium's internal order, which is NOT necessarily the visible tab. When Chromium starts with a URL, that is `tabs[0]`. But if any internal page (chrome://new-tab-page, chrome://settings, DevTools) opens, or if the skill code opens a new target via `Target.createTarget`, the agent silently starts controlling the wrong tab.

**Why it happens:**
The `/json` endpoint returns tabs in Chrome's internal object creation order, not in user-visible order. A newly opened tab via `Target.createTarget` may appear anywhere in the list.

**How to avoid:**
Filter `/json` results by `type == 'page'` and prefer the tab whose URL is not `about:blank` or `chrome://`. The skill doc already recommends this filter (it's in the SKILL.md code examples) but `app.py` and `_get_ws_url()` do not apply it. Fix `_get_ws_url()` to filter by `type == 'page'` and skip `chrome://` and `about:blank` targets.

**Warning signs:**
- CDP commands succeed but nothing visible changes
- Screenshot shows a blank tab or settings page
- URL polling returns `chrome://new-tab-page` instead of the intended URL

**Phase to address:** BROWSER-01 (CDP navigation fix)

---

### Pitfall 9: asyncio.run() Inside Flask Threads Causes Event Loop Conflicts

**What goes wrong:**
`app.py` uses `asyncio.run(coro)` (via `_run()`) inside Flask route handlers, which run in regular OS threads (Flask's `threaded=True` mode). Python 3.10+ raises `RuntimeError: This event loop is already running` if called from a thread that already has an active event loop. This does not happen with simple Flask threading today, but it will break if the server is ever run under an ASGI host (Uvicorn/Hypercorn) or if any library sets a running event loop on the worker threads.

**Why it happens:**
`asyncio.run()` creates and destroys a new event loop per call. This is safe in plain threads but fragile — it cannot be used inside `async` contexts, and some libraries (like `nest_asyncio`) interfere with it in unexpected ways.

**How to avoid:**
For the current Flask threading model, `asyncio.run()` works but should be clearly documented as a limitation. If the server ever migrates to an async host, replace `asyncio.run()` with a module-level event loop running in a dedicated background thread, and use `asyncio.run_coroutine_threadsafe()`. For this milestone, leave as-is but add a comment warning about the limitation.

**Warning signs:**
- `RuntimeError: This event loop is already running` in Flask logs
- Happens only under specific deployment configurations (Gunicorn with gevent workers, Uvicorn)

**Phase to address:** Not a current milestone concern, but document it in BROWSER-01 implementation

---

### Pitfall 10: Claude CLI Spawned as Subprocess Inherits the Parent's Environment Incorrectly

**What goes wrong:**
When `TTYSession` spawns `claude` via `create_subprocess_shell`, it passes `env=os.environ.copy()`. If Agent Zero's Docker environment has `ANTHROPIC_API_KEY` set (it does — it's how the agent works), claude CLI will use it silently. But if the key is absent or scoped only to a specific context, claude fails to start with a cryptic error that looks like a PTY problem rather than an auth problem.

**Why it happens:**
claude CLI requires `ANTHROPIC_API_KEY` or a stored credentials file. When launched as a subprocess in Docker, it may not find credentials from the system keyring (no keyring daemon running in minimal Docker). The error message from claude CLI goes to stderr, which the PTY merges with stdout — it looks like random noise in the output.

**How to avoid:**
When creating the claude session, explicitly assert `ANTHROPIC_API_KEY` is present in the environment dict before spawning. If absent, return a clear error to the agent: "ANTHROPIC_API_KEY not set — cannot launch claude CLI." Also verify claude is on `$PATH` with a `which claude` or `claude --version` check before attempting a full session.

**Warning signs:**
- TTYSession starts successfully (process spawns) but first output contains "Invalid API key" or similar
- First read returns empty string or ANSI-only content before the session closes
- `_pump_stdout` hits EOF immediately after start

**Phase to address:** CLAUDE-01 (claude CLI launch)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Per-request CDP WebSocket connections | Simple, no connection pooling logic | Adds latency, loses async events, fragile under concurrency | Acceptable for milestone if nav-wait is added; revisit if concurrency becomes an issue |
| `asyncio.run()` in Flask threads | Works today with no additional infrastructure | Breaks under async hosts, not forward-compatible | Acceptable for this milestone; document the limitation |
| Idle-timeout only for claude output detection | Dead simple to implement | Unreliable for LLM streaming outputs with natural pauses | Never acceptable for production — always combine with prompt pattern matching |
| `tabs[0]` tab selection without type filtering | Works when Chromium opens with exactly one page tab | Breaks silently when internal tabs appear | Never acceptable — always filter for `type == 'page'` and non-chrome URLs |
| `time.sleep(2)` after Chromium start in `startup.sh` | Simple startup delay | Race condition — slow machines or loaded Docker hosts may need more time | Acceptable only with a fallback health-check loop (like `_wait_for_cdp()` already in `browser_agent.py`) |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| CDP `Page.navigate` | Treat the method response as "page loaded" | Wait for `Page.loadEventFired` or poll `document.readyState === 'complete'` after navigate |
| CDP `/json` tab list | Use `tabs[0]` directly | Filter `type == 'page'`, skip `chrome://` and `about:blank` |
| CDP WebSocket origin | Assume HTTP endpoint working means WebSocket works | Test WebSocket specifically; HTTP and WebSocket auth are separate in Chromium |
| claude CLI output | Treat raw PTY bytes as plain text | Strip ANSI escape sequences and `\r` before passing to LLM |
| claude CLI completion | Use idle timeout alone | Idle timeout + prompt pattern regex on last N bytes of output |
| claude CLI environment | Let subprocess inherit everything | Explicitly validate `ANTHROPIC_API_KEY` in env before spawning |
| TTYSession reuse | Reuse session object across tasks without checking liveness | Check `_eof` flag / process returncode before each send |
| Chromium resize + headless=new | Assume immediate repaint after `Emulation.setDeviceMetricsOverride` | Trigger repaint with navigate or JS `resize` event dispatch |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Per-call WebSocket handshake for CDP | CDP calls add 50-150ms latency each; screenshot polling feels sluggish | Use persistent connection with message dispatcher | At >1 concurrent CDP operation, or when polling rate is < 800ms |
| Full PTY output buffering for claude | `read_full_until_idle` accumulates entire session output in memory | Stream output chunks; only keep last N chars for prompt detection | When claude produces multi-page responses (context-heavy tasks) |
| Screenshot polling at 800ms unconditionally | 800ms poll is fine normally; after navigation it means up to 800ms of stale view | Invalidate cache immediately on navigate (current code does this correctly) + lower TTL post-navigate | Latency perception — not a functional break |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| CDP port 9222 exposed on Docker host interface (not just localhost) | Any process/container that can reach the host can control the browser, including reading cookies and executing JS | Bind CDP only to 127.0.0.1 inside the container; never expose 9222 via docker-compose `ports:` |
| `ANTHROPIC_API_KEY` logged in claude session debug output | API key appears in Agent Zero chat logs | Mask the key in any output captured from claude before logging; use the existing `get_secrets_manager` masking |
| claude CLI runs arbitrary shell commands on behalf of the LLM | If another agent sends malicious prompts to claude CLI, it can execute shell commands | Scope claude CLI sessions to sandboxed tasks only; document this in CLAUDE-05 skill |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Agent navigates and immediately screenshots before page loads | User sees the agent "observe" a blank/loading page and make wrong decisions | BROWSER-02/03: always wait for load complete before observe screenshot |
| Agent tells user "navigation succeeded" based on CDP response, not actual URL | Agent gives false confidence; user sees wrong page in drawer | Verify by comparing `tabs[0].url` to intended URL after navigation |
| claude CLI session left open after task completes | Subsequent agent tasks try to reuse stale session; hang | Explicit session lifecycle: open for task, close when done or after TTL |
| Agent Zero UI shows perpetual "loading" indicator when claude CLI session hangs | User thinks Agent Zero itself is stuck | Set hard timeouts on every claude CLI interaction (total_timeout ≤ 120s for any single exchange) |

---

## "Looks Done But Isn't" Checklist

- [ ] **CDP navigation:** `Page.navigate` was called and returned a result — verify the URL in `/json` matches the target URL before concluding navigation succeeded
- [ ] **CDP WebSocket:** `/json` HTTP endpoint responds — also verify a WebSocket connection succeeds with a `Runtime.evaluate 1+1` test call
- [ ] **Chromium startup:** Port 9222 is open (TCP connect succeeds) — also verify Chromium is past the startup splash by checking that `/json` returns at least one tab with a non-blank URL
- [ ] **claude CLI launch:** The process was spawned — also verify first output contains the claude greeting/prompt, not an error about missing API key or missing binary
- [ ] **claude CLI output received:** `read_full_until_idle` returned text — also verify the text contains actual content and not only ANSI escape sequences
- [ ] **claude CLI completion detected:** Idle timeout elapsed — also verify the last chars of output match the claude input prompt pattern, not a mid-response pause
- [ ] **Viewport resize:** `Emulation.setDeviceMetricsOverride` returned OK — also verify screenshot dimensions match the requested size

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Navigation returns before load complete | LOW | Add explicit wait loop; no architecture change needed |
| CDP WebSocket 403 | LOW | Restart Chromium with correct flags; the `startup.sh` already has them |
| Wrong tab selected | LOW | Fix `_get_ws_url()` filter; one-line change |
| claude CLI prompt detection mismatch | MEDIUM | Profile claude CLI's actual ANSI output to find the prompt marker; update regex |
| claude session hangs (orphaned PTY) | LOW | Kill process + respawn; add liveness check to `TTYSession` |
| ANSI sequences corrupting output | LOW | Add ANSI stripping in the claude-specific wrapper; no change to core `TTYSession` |
| Chromium started without CDP flags | LOW | `pkill chromium && restart shared-browser app` — already documented in skill troubleshooting |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Page.navigate timing (screenshot before load) | BROWSER-01, BROWSER-02, BROWSER-03 | Screenshot after navigate shows fully loaded page, URL matches target |
| CDP WebSocket 403 | BROWSER-04 | `websockets.connect(ws_url)` succeeds from Python after startup |
| Per-request WebSocket fragility | BROWSER-01 | Navigation + concurrent screenshot polling does not error |
| claude idle-timeout prompt detection | CLAUDE-02, CLAUDE-03 | claude returns full response; second prompt sent only after first completes |
| ANSI sequences in output | CLAUDE-02 | Captured output contains no `\x1b[` sequences when logged |
| claude session reuse after exit | CLAUDE-04 | Multi-turn session survives 3+ round trips; dead session auto-restarts |
| headless=new viewport resize | BROWSER-04 | Screenshot dimensions match viewport after resize |
| Wrong tab selection | BROWSER-01 | CDP always targets the visible page tab, not chrome:// internal tabs |
| asyncio.run() in Flask threads | BROWSER-01 (document only) | No crash under current deployment; comment warns about async host incompatibility |
| Subprocess env / auth failure | CLAUDE-01 | Missing API key produces a clear error message, not a silent hang |

---

## Sources

- Direct codebase analysis: `/apps/shared-browser/app.py`, `/python/tools/browser_agent.py`, `/python/helpers/tty_session.py`, `/python/helpers/shell_local.py`, `/usr/skills/shared-browser/SKILL.md`
- CDP protocol semantics: training knowledge of Chrome DevTools Protocol (Page.navigate, Page.loadEventFired, Emulation.setDeviceMetricsOverride behavior) — MEDIUM confidence on specific event names, HIGH confidence on the fundamental timing issue
- Chromium `--remote-allow-origins` flag: introduced ~M108, well-documented pattern — HIGH confidence
- claude CLI TUI/Ink architecture and ANSI output: training knowledge of Ink-based CLIs — MEDIUM confidence on specific escape sequences; recommend profiling actual claude output during CLAUDE-01
- PTY/pexpect subprocess control patterns: well-established patterns from training — HIGH confidence

---
*Pitfalls research for: CDP browser control + claude CLI interactive subprocess, Agent Zero fork (v1.1 Reliability milestone)*
*Researched: 2026-02-25*
