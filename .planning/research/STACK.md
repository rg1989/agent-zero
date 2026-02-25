# Stack Research

**Domain:** CDP WebSocket browser control + interactive CLI subprocess management in Python
**Researched:** 2026-02-25
**Confidence:** HIGH (all verified against actual codebase, installed packages, and official pip index)

---

## Context: What Already Exists

Agent Zero's fork already has working implementations to build on:

| Component | Location | Status |
|-----------|----------|--------|
| PTY session manager | `python/helpers/tty_session.py` | Production-ready, asyncio-native |
| Local interactive shell | `python/helpers/shell_local.py` | Wraps TTYSession |
| CDP async client | `apps/shared-browser/app.py` | Working with `websockets` async |
| CDP sync pattern | `usr/skills/shared-browser/SKILL.md` | Documented with `websocket-client` |
| Chromium w/ CDP | `apps/shared-browser/startup.sh` | Running on port 9222, `--remote-allow-origins=*` |
| `websockets` package | `requirements.txt` (via install) | v15.0.1 installed |

The codebase already has a complete async PTY implementation using Python stdlib `pty` + `asyncio`. The shared-browser app already uses `websockets` (async) for CDP. **The goal is to extend these patterns, not replace them.**

---

## Recommended Stack

### Core Technologies — CDP Browser Control

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `websockets` (async) | `>=15.0` | CDP WebSocket connection in async contexts (Flask async handlers, Agent Zero tools) | Already installed. The shared-browser `app.py` already uses this pattern (`websockets.connect(ws_url, max_size=None)`). Async is the right choice for Flask async + Agent Zero's asyncio event loop. v15 has `websockets.asyncio.client` and stable `websockets.sync.client`. |
| `websocket-client` (sync) | `>=1.9.0` | CDP WebSocket connection in synchronous scripts (skill code snippets, one-shot bash execution) | The SKILL.md documents `websocket.create_connection(url)` — this is the sync API. Add to `requirements.txt`. Different PyPI package name: `websocket-client`, import name: `websocket`. Version 1.9.0 is current stable. |
| `urllib.request` (stdlib) | built-in | CDP tab discovery via `http://localhost:9222/json` | Already used in `app.py`. No dependency needed. Zero-cost tab enumeration to get WebSocket debugger URLs. |

### Core Technologies — Interactive `claude` CLI Subprocess

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `claude --print` (`-p`) mode | CLI v2.1.55+ | Non-interactive, pipe-friendly execution for single-turn tasks | **This is the primary recommended approach.** `claude -p "prompt"` outputs response to stdout and exits. Supports `--output-format text/json/stream-json`. Unset `CLAUDECODE` env var to allow subprocess launch from within Claude Code sessions. Handles completion detection naturally — process exits. |
| `TTYSession` (existing) | built-in | Multi-turn interactive `claude` sessions in a real PTY | Already in `python/helpers/tty_session.py`. Uses `asyncio` + stdlib `pty.openpty()` on Linux. Can spawn `claude` in interactive mode with full PTY emulation. Agent Zero's `LocalInteractiveSession` already wraps this. Reuse for CLAUDE-02/03/04 requirements. |
| `asyncio.create_subprocess_exec` (stdlib) | built-in | Non-interactive `claude -p` subprocess in async code | Use for single-shot `claude -p` calls from Agent Zero tools. Returns stdout directly. No extra library needed — pure stdlib. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `websocket-client` | `>=1.9.0` | Synchronous CDP in skill snippets | Agent Zero skill code runs via `code_execution_tool` as Python snippets. Sync `websocket.create_connection(url)` is simpler for snippet-style code than async context managers. Add to `requirements.txt`. |
| `base64` (stdlib) | built-in | Decode CDP `Page.captureScreenshot` response | Already used in `app.py` and SKILL.md. No install needed. |
| `json` (stdlib) | built-in | CDP message serialization | Built-in. Already used everywhere. |
| `psutil` | `>=7.0.0` | Check if Chromium process is running before CDP | Already in `requirements.txt`. Use to detect stale Chromium before attempting CDP connection. |

### Shell Utilities (Docker system packages)

| Utility | Package | Purpose | When to Use |
|---------|---------|---------|-------------|
| `chromium` | `chromium` (apt) | The CDP-controlled browser | Already installed via `install_additional.sh`. Must be started with `--remote-allow-origins=*` and `--remote-debugging-port=9222`. Currently `--headless=new`. |
| `xdotool` | `xdotool` (apt) | X11 keyboard/mouse simulation | Secondary to CDP. Use only for tasks CDP cannot handle: tab switching by position, scroll with wheel, DevTools open. Requires Xvfb display. |
| `scrot` | `scrot` (apt) | X11 screenshot fallback | Use when Chromium CDP screenshot fails (process crashed). |

**Note:** `xvfb`, `x11vnc`, `chromium`, `websockify` are already installed in `install_additional.sh`. `xdotool` and `scrot` may need adding if not already present — verify with `which xdotool` in container.

---

## Installation

```bash
# Add to requirements.txt
websocket-client>=1.9.0
```

That is the only new Python dependency needed.

```bash
# In Docker install_additional.sh — verify these are present
apt-get install -y --no-install-recommends xdotool scrot
```

No other packages needed. The entire CDP async stack (`websockets`), PTY stack (stdlib `pty` + `asyncio`), and subprocess stack (`asyncio.create_subprocess_exec`) are already available.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `claude -p` (print mode) for single-turn | `pexpect` for interactive mode | Use `pexpect` only if you need to interact with `claude`'s interactive TUI and parse prompt boundaries. `pexpect` adds a dependency and complex pattern matching. `claude -p` is simpler, more reliable, and officially supported for scripting. |
| `TTYSession` (existing) for multi-turn | `pexpect` + `expect()` | `pexpect` is easier to write but Agent Zero's `TTYSession` is already in production, async-native, and battle-tested. Extending the existing abstraction is lower risk than adding a new library. |
| `websockets` async (existing) for app.py | `playwright` CDP API | Playwright is already installed (`playwright==1.52.0`) but must NOT be used for the shared browser — it spawns a separate Chromium instance and creates a persistent loader in the Agent Zero UI (documented in SKILL.md). Use Playwright only when explicitly requested by the user. |
| `websocket-client` sync for skills | `websockets` async | Skill snippet code runs in `code_execution_tool`'s synchronous Python runtime via `ipython -c`. Using async `websockets` in a snippet requires `asyncio.run()` wrapper. `websocket-client`'s synchronous `create_connection()` is cleaner for snippet-style code. |
| `asyncio.create_subprocess_exec` | `subprocess.run` | Both work. Prefer async version in Agent Zero tools since the framework is async-native. `subprocess.run` is fine in skill snippets. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `playwright` for shared browser | Spawns isolated Chromium, creates persistent UI loader, defeats the purpose of the shared browser. Explicitly banned in SKILL.md. | `websockets` async CDP in app code; `websocket-client` sync CDP in skill snippets |
| `pexpect` | Adds a dependency (`pexpect>=4.9.0`) for functionality the existing `TTYSession` already provides. `pexpect` also uses its own PTY implementation that would conflict/duplicate. | `TTYSession` (existing) for multi-turn interactive sessions; `claude -p` for single-turn |
| `ptyprocess` standalone | Lower-level than `pexpect`, provides no benefit over stdlib `pty` which `TTYSession` already uses directly. | Existing `tty_session.py` stdlib implementation |
| `websockets` v<10 API patterns | v15 changed the API. Old code using `websockets.connect()` as a regular function (not async context manager) will fail. The shared-browser `app.py` correctly uses `async with websockets.connect(...) as ws:`. | `websockets>=15.0` with async context manager pattern |
| `selenium` / `pyppeteer` | Heavy dependencies; pyppeteer is abandoned (last release 2022); both would create separate browser instances. | Direct CDP via `websockets` or `websocket-client` |
| Raw `CLAUDECODE` env bypass in production code | Unsetting `CLAUDECODE` allows subprocess launch of `claude` but creates nested sessions that "share runtime resources and will crash all active sessions" (per claude's own error message). | `claude -p` with `CLAUDECODE` unset only in the subprocess env (not the parent), using `env=` parameter to `subprocess` calls |

---

## Stack Patterns by Variant

**If running CDP from within Agent Zero tool code (async context):**
- Use `websockets` async with `async with websockets.connect(ws_url) as ws:`
- Pattern already established in `apps/shared-browser/app.py`
- The `_cdp()` helper in `app.py` is the reference implementation

**If running CDP from a skill snippet (via `code_execution_tool` Python runtime):**
- Use `websocket-client`: `ws = websocket.create_connection(url)`
- The SKILL.md CDP helper is the reference implementation
- Synchronous — no event loop required

**If running `claude -p` for a single-turn response:**
```python
import asyncio, os
env = os.environ.copy()
env.pop("CLAUDECODE", None)  # allow nested launch
proc = await asyncio.create_subprocess_exec(
    "claude", "-p", "--output-format", "text", prompt_text,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env=env,
)
stdout, stderr = await proc.communicate()
response = stdout.decode()
```

**If running `claude` interactively for multi-turn sessions (CLAUDE-02/03/04):**
- Use `TTYSession` from `python/helpers/tty_session.py` directly
- Spawn with `TTYSession("claude")` after unsetting `CLAUDECODE` in the env
- Read output with `read_full_until_idle(idle_timeout=0.5, total_timeout=30)`
- Detect completion by watching for `claude`'s output to stop (idle timeout approach)
- Or inject a sentinel: after sending a prompt, append `; echo __DONE__` — though this doesn't work for interactive `claude` TUI
- Better: poll `read_chunks_until_idle` and detect the `> ` or `claude>` prompt pattern

**If verifying Chromium CDP is available before connecting:**
```python
import urllib.request, json
try:
    tabs = json.loads(urllib.request.urlopen("http://localhost:9222/json", timeout=3).read())
    page_tabs = [t for t in tabs if t.get("type") == "page"]
    # proceed with ws_url = page_tabs[0]["webSocketDebuggerUrl"]
except Exception:
    # Chromium not running or CDP not enabled — restart with --remote-allow-origins=*
```

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `websockets>=15.0` | Python 3.12.4 (Docker venv `/opt/venv-a0`) | v15 is the current series. API: `async with websockets.connect(url) as ws`. The `max_size=None` param is still valid. |
| `websocket-client>=1.9.0` | Python 3.12.4 | Sync API: `websocket.create_connection(url)`. Thread-safe. Docker venv compatible. |
| `TTYSession` (existing) | Python 3.12.4 | Uses stdlib `pty`, `asyncio`, `termios`. All built-in. Linux/Mac only (Windows uses `pywinpty` which is also already in `requirements.txt`). |
| `claude -p` mode | claude v2.1.55+ | Requires unsetting `CLAUDECODE` in subprocess env. Supports `--output-format text/json/stream-json`. |

---

## CDP WebSocket Pitfall: `websocket-client` vs `websockets`

These are **two different packages** with similar names:

| Package | PyPI name | Import name | Style | Use case |
|---------|-----------|-------------|-------|----------|
| `websockets` | `websockets` | `import websockets` | Async | App code, Flask async handlers |
| `websocket-client` | `websocket-client` | `import websocket` | Sync | Skill snippets, one-shot scripts |

The SKILL.md uses `import websocket` (sync). The `app.py` uses `import websockets` (async). Both are needed. Only `websockets` is currently installed. `websocket-client` must be added to `requirements.txt`.

---

## Sources

- `python/helpers/tty_session.py` — verified: stdlib `pty` + asyncio PTY implementation, no external dependencies
- `python/helpers/shell_local.py` — verified: wraps `TTYSession`, confirms existing interactive session pattern
- `apps/shared-browser/app.py` — verified: `websockets` async CDP pattern, `asyncio.wait_for` for timeout, `async with websockets.connect(ws_url, max_size=None)`
- `usr/skills/shared-browser/SKILL.md` — verified: `websocket-client` sync CDP pattern documented
- `requirements.txt` — verified: `websocket-client` absent, `websockets` absent (but v15.0.1 installed as transitive dep)
- `docker/run/fs/ins/install_additional.sh` — verified: `xvfb`, `x11vnc`, `websockify`, `chromium` installed; `xdotool`/`scrot` not yet confirmed
- `docker/base/fs/ins/install_python.sh` — verified: Docker uses Python 3.12.4 in `/opt/venv-a0`
- `pip index versions pexpect` — verified: pexpect 4.9.0 is current stable (HIGH confidence via pip)
- `pip index versions websocket-client` — verified: websocket-client 1.9.0 is current stable (HIGH confidence via pip)
- `claude --help` (v2.1.55) — verified: `-p/--print` flag exists, `--output-format` supports text/json/stream-json, `CLAUDECODE` env var prevents nested sessions

---
*Stack research for: CDP browser control and interactive CLI subprocess management*
*Researched: 2026-02-25*
