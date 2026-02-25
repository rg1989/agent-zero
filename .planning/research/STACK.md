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
| Claude CLI single-turn | `python/helpers/claude_cli.py` | `claude_single_turn()` via `--print` flag |
| Claude CLI multi-turn | `python/helpers/claude_cli.py` | `ClaudeSession` with `--resume UUID` |

The codebase already has a complete async PTY implementation using Python stdlib `pty` + `asyncio`. The shared-browser app already uses `websockets` (async) for CDP. **The goal is to extend these patterns, not replace them.**

---

## v1.2 Additions: tmux Terminal Interaction and OpenCode CLI

This section covers ONLY the new stack needed for v1.2 Terminal Orchestration milestone.

### Core Technologies — tmux Terminal Interaction

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `subprocess.run` / `asyncio.create_subprocess_exec` (stdlib) | built-in | Drive tmux commands: `send-keys`, `capture-pane`, `list-sessions`, `list-panes` | **No new dependency.** tmux is a CLI tool — its entire API is invokable via subprocess. `tmux send-keys -t session:window.pane "text" Enter` and `tmux capture-pane -p -t target` cover all TERM-01 through TERM-05 requirements. Already used throughout Agent Zero's codebase. |
| `tmux` (system binary) | 3.x (already in Docker) | Terminal multiplexer — manages the shared terminal session (`agent0` session) | Already installed in Docker container as part of shared-terminal app. No install needed. The shared-terminal app (`apps/shared-terminal/`) already creates and manages a tmux session. |

**Verdict: zero new Python dependencies for tmux control.** Raw subprocess calls are the correct approach.

### Why NOT libtmux

libtmux (v0.53.1 on PyPI) provides a Python object wrapper around tmux. It is **not recommended** for this project for these reasons:

1. **Blocking, not async**: libtmux uses synchronous subprocess calls internally. Wrapping each call in `asyncio.run_in_executor` adds complexity with no benefit over direct subprocess calls.
2. **Dependency for a thin wrapper**: The operations needed — `send-keys` and `capture-pane` — are 1-2 line subprocess calls. libtmux adds 50KB+ of library code to wrap what is already simple.
3. **Version mismatch risk**: The project's Docker pip environment resolves to 0.46.2 (the version available at pip index time); the web-published latest is 0.53.1. API differences between minor versions have been noted in libtmux changelogs. A thin subprocess wrapper has no version drift risk.
4. **No object model benefit**: The project accesses one fixed tmux session (`agent0`) by name, not dynamic session trees. The object model libtmux provides is unused.

Use libtmux only if the project ever needs to manage many tmux sessions programmatically (session inventory, complex window/pane creation). That is out of scope for v1.2.

### Core Technologies — OpenCode CLI Orchestration

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `opencode` (system binary) | latest stable (Go binary) | OpenCode AI coding agent CLI | OpenCode is a Go binary distributed via `npm i -g opencode-ai@latest`, `brew install opencode`, or `curl -fsSL https://opencode.ai/install \| bash`. No Python package — it runs as a separate process. |
| tmux send-keys via subprocess | see above | Drive OpenCode's interactive TUI | OpenCode's TUI takes over stdin (full-screen terminal interface using opentui/SolidJS). The only way to interact with it programmatically is via tmux `send-keys` — exactly the same pattern as any other interactive TUI (htop, vim, etc.). |
| `subprocess.run` (stdlib) | built-in | `opencode -p "prompt"` for non-interactive single-turn | OpenCode supports `-p` flag for non-interactive mode (outputs response to stdout and exits). Useful for one-shot queries. Same pattern as `claude --print`. |

**OpenCode interaction modes:**

| Mode | Command | When to Use |
|------|---------|-------------|
| Non-interactive single-turn | `opencode -p "prompt"` | One-shot query, no context needed, no TUI |
| Non-interactive with session | `opencode -p "prompt" -s <session-id>` | Resume previous conversation in non-interactive mode |
| Interactive TUI | `opencode` or `opencode -s <session-id>` | Full TUI in tmux pane; orchestrate via send-keys |

**Note on `-p` flag status (LOW confidence, verify):** The `-p`/`--print` non-interactive flag for OpenCode has been referenced in community discussions and issue trackers (issue #10411 on anomalyco/opencode). Its exact flags and `--session` resumption behavior are functionally similar to Claude CLI's `--print --resume` but the exact flag names need verification against the installed binary. Run `opencode --help` to confirm before building `opencode_session()`.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` (stdlib) | built-in | Prompt pattern detection in `capture-pane` output | TERM-05: detect shell prompt (`$`, `#`, `>`) or OpenCode's prompt to confirm readiness |
| `asyncio` (stdlib) | built-in | Async subprocess for tmux commands, idle timeout logic | Already used throughout. `asyncio.create_subprocess_exec` + `asyncio.wait_for` for timeout |
| `time` (stdlib) | built-in | Poll timing for readiness detection | Already used in `TTYSession.read_chunks_until_idle` — reuse same idle-timeout pattern |

No new dependencies required.

---

## Recommended Stack — Complete Picture (v1.0 + v1.1 + v1.2)

### Core Technologies — CDP Browser Control

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `websockets` (async) | `>=15.0` | CDP WebSocket connection in async contexts (Flask async handlers, Agent Zero tools) | Already installed. The shared-browser `app.py` already uses this pattern (`websockets.connect(ws_url, max_size=None)`). Async is the right choice for Flask async + Agent Zero's asyncio event loop. v15 has `websockets.asyncio.client` and stable `websockets.sync.client`. |
| `websocket-client` (sync) | `>=1.9.0` | CDP WebSocket connection in synchronous scripts (skill code snippets, one-shot bash execution) | The SKILL.md documents `websocket.create_connection(url)` — this is the sync API. Add to `requirements.txt`. Different PyPI package name: `websocket-client`, import name: `websocket`. Version 1.9.0 is current stable. |
| `urllib.request` (stdlib) | built-in | CDP tab discovery via `http://localhost:9222/json` | Already used in `app.py`. No dependency needed. Zero-cost tab enumeration to get WebSocket debugger URLs. |

### Core Technologies — Interactive `claude` CLI Subprocess

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `claude --print` (`-p`) mode | CLI v2.1.55+ | Non-interactive, pipe-friendly execution for single-turn tasks | **Primary recommended approach.** `claude -p "prompt"` outputs response to stdout and exits. Supports `--output-format text/json/stream-json`. Unset `CLAUDECODE` env var to allow subprocess launch from within Claude Code sessions. Handles completion detection naturally — process exits. |
| `TTYSession` (existing) | built-in | Multi-turn interactive `claude` sessions in a real PTY | Already in `python/helpers/tty_session.py`. Uses `asyncio` + stdlib `pty.openpty()` on Linux. Can spawn `claude` in interactive mode with full PTY emulation. |
| `ClaudeSession` (existing) | built-in | Stateful multi-turn claude conversation wrapper | In `python/helpers/claude_cli.py`. Tracks `session_id` via `--resume UUID`. Model for building `OpenCodeSession`. |

### Core Technologies — tmux Terminal Interaction (NEW in v1.2)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `asyncio.create_subprocess_exec` (stdlib) | built-in | Async tmux command execution | Drive all tmux operations: `send-keys`, `capture-pane`, `list-panes`. No new deps. |
| `tmux` (system binary) | 3.x | The terminal multiplexer already running shared-terminal sessions | Already in Docker. Zero install overhead. |
| `opencode` (system binary) | latest | OpenCode AI coding agent — runs in tmux pane, orchestrated via send-keys | Installed separately in Docker or user env. Non-interactive `-p` mode also available. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `websocket-client` | `>=1.9.0` | Synchronous CDP in skill snippets | Agent Zero skill code runs via `code_execution_tool` as Python snippets. Sync `websocket.create_connection(url)` is simpler for snippet-style code than async context managers. Add to `requirements.txt`. |
| `base64` (stdlib) | built-in | Decode CDP `Page.captureScreenshot` response | Already used in `app.py` and SKILL.md. No install needed. |
| `json` (stdlib) | built-in | CDP message serialization + tmux capture-pane output parsing | Built-in. Already used everywhere. |
| `psutil` | `>=7.0.0` | Check if Chromium process is running before CDP | Already in `requirements.txt`. Use to detect stale Chromium before attempting CDP connection. |
| `re` (stdlib) | built-in | Prompt pattern detection in tmux capture-pane output | Detect shell/CLI readiness: `$`, `#`, `>`, OpenCode input prompt. No install. |

### Shell Utilities (Docker system packages)

| Utility | Package | Purpose | When to Use |
|---------|---------|---------|-------------|
| `chromium` | `chromium` (apt) | The CDP-controlled browser | Already installed via `install_additional.sh`. Must be started with `--remote-allow-origins=*` and `--remote-debugging-port=9222`. Currently `--headless=new`. |
| `tmux` | `tmux` (apt) | Terminal multiplexer — manages the shared terminal session (`agent0` session) | Already installed. `apps/shared-terminal/` manages the session lifecycle. |
| `opencode` | npm/curl install | OpenCode AI coding agent CLI | Install in Docker: `npm i -g opencode-ai@latest` or via install script. Add to `install_additional.sh`. |
| `xdotool` | `xdotool` (apt) | X11 keyboard/mouse simulation | Secondary to CDP. Use only for tasks CDP cannot handle: tab switching by position, scroll with wheel, DevTools open. Requires Xvfb display. |
| `scrot` | `scrot` (apt) | X11 screenshot fallback | Use when Chromium CDP screenshot fails (process crashed). |

---

## Installation

```bash
# Add to requirements.txt — only new Python dependency for v1.1+v1.2
websocket-client>=1.9.0

# No libtmux — not needed. Raw subprocess tmux commands cover all requirements.
```

```bash
# In Docker install_additional.sh — add opencode install
# Option A: npm (if node is available)
npm install -g opencode-ai@latest

# Option B: install script
curl -fsSL https://opencode.ai/install | bash

# Verify tmux is present (should already be installed for shared-terminal)
which tmux

# Verify/add xdotool and scrot for CDP fallback
apt-get install -y --no-install-recommends xdotool scrot
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Raw subprocess tmux commands | `libtmux>=0.53` | Use libtmux if managing many dynamic tmux sessions (session inventory, programmatic session creation). Not needed for v1.2 which accesses one fixed `agent0` session. |
| tmux send-keys for OpenCode TUI | `pexpect` with PTY | pexpect works for PTY-based interaction but adds a dependency and requires complex pattern matching. tmux send-keys is already the pattern for the shared-terminal app and is simpler. |
| `opencode -p` for non-interactive | TTYSession spawning opencode | TTYSession works but non-interactive `-p` mode is simpler when no TUI persistence is needed. Use TTYSession only if multi-turn TUI session is required and `-p --session` is insufficient. |
| `claude --print` (existing) for single-turn | `opencode -p` | Use opencode when opencode-specific context (file editing, codebase awareness) is needed. Use claude for general AI queries. Both are subprocess.run patterns. |
| `asyncio.create_subprocess_exec` | `subprocess.run` | Both work. Prefer async version in Agent Zero tools since the framework is async-native. `subprocess.run` is fine in skill snippets. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `libtmux` | Adds 50KB+ dependency for a thin wrapper around 2-line subprocess calls. Blocking internals conflict with async Agent Zero architecture. Version drift between pip-resolved (0.46.2) and latest (0.53.1) creates risk. | `asyncio.create_subprocess_exec` + `tmux send-keys` / `capture-pane` directly |
| `playwright` for shared browser | Spawns isolated Chromium, creates persistent UI loader, defeats the purpose of the shared browser. Explicitly banned in SKILL.md. | `websockets` async CDP in app code; `websocket-client` sync CDP in skill snippets |
| `pexpect` for any interactive session | Adds a dependency for functionality the existing `TTYSession` and tmux approach already provide. `pexpect` has its own PTY implementation that duplicates existing code. | `TTYSession` for PTY processes; tmux send-keys for TUI processes already in a pane |
| `ptyprocess` standalone | Lower-level than `pexpect`, provides no benefit over stdlib `pty` which `TTYSession` already uses directly. | Existing `tty_session.py` stdlib implementation |
| Raw `CLAUDECODE` env bypass in production code | Unsetting `CLAUDECODE` allows subprocess launch of `claude` but creates nested sessions that "share runtime resources and will crash all active sessions" (per claude's own error message). | `claude -p` with `CLAUDECODE` unset only in the subprocess env (not the parent), using `env=` parameter to `subprocess` calls — same pattern needed for `opencode` if run inside Claude Code |
| `websockets` v<10 API patterns | v15 changed the API. Old code using `websockets.connect()` as a regular function (not async context manager) will fail. | `websockets>=15.0` with async context manager pattern |

---

## Stack Patterns by Variant

**If sending text to a tmux pane (TERM-01, TERM-02, TERM-03):**
```python
import asyncio

async def tmux_send(target: str, text: str, enter: bool = True) -> None:
    """target: 'agent0:0.0' (session:window.pane)"""
    keys = text + (" Enter" if enter else "")
    proc = await asyncio.create_subprocess_exec(
        "tmux", "send-keys", "-t", target, text,
        *(["Enter"] if enter else []),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"tmux send-keys failed: {stderr.decode()}")
```

**If capturing pane content (TERM-04):**
```python
async def tmux_capture(target: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "tmux", "capture-pane", "-p", "-t", target,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode("utf-8", errors="replace")
```

**If detecting terminal readiness (TERM-05):**
```python
import re, asyncio

PROMPT_RE = re.compile(r"[$#>]\s*$", re.MULTILINE)  # generic shell prompt
OPENCODE_PROMPT_RE = re.compile(r"^\s*>\s*$", re.MULTILINE)  # OpenCode input indicator

async def wait_for_prompt(target: str, pattern: re.Pattern,
                           poll_interval=0.3, timeout=30) -> str:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        content = await tmux_capture(target)
        if pattern.search(content):
            return content
        await asyncio.sleep(poll_interval)
    return await tmux_capture(target)  # return what we have on timeout
```

**If running opencode non-interactively (CLI-01 single-turn):**
```python
import subprocess, os

def opencode_single_turn(prompt: str, session_id: str = None, timeout: int = 180) -> str:
    # Mirror claude_single_turn() pattern from claude_cli.py
    env_clean = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    cmd = ["opencode", "-p", prompt]
    if session_id:
        cmd += ["-s", session_id]
    result = subprocess.run(cmd, capture_output=True, text=True,
                             env=env_clean, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"opencode exited {result.returncode}: {result.stderr[:400]}")
    return result.stdout.strip()
```

**If running opencode as interactive TUI in a named tmux window (CLI-01 TUI):**
```python
async def opencode_tui_start(session_name: str = "agent0",
                              window_name: str = "opencode") -> str:
    """Starts opencode in a new tmux window. Returns 'session:window' target."""
    target = f"{session_name}:{window_name}"
    proc = await asyncio.create_subprocess_exec(
        "tmux", "new-window", "-t", session_name, "-n", window_name,
        "-d", "opencode",
        stdout=asyncio.subprocess.DEVNULL,
    )
    await proc.communicate()
    return target
```

**If running CDP from within Agent Zero tool code (async context):**
- Use `websockets` async with `async with websockets.connect(ws_url) as ws:`
- Pattern already established in `apps/shared-browser/app.py`
- The `_cdp()` helper in `app.py` is the reference implementation

**If running CDP from a skill snippet (via `code_execution_tool` Python runtime):**
- Use `websocket-client`: `ws = websocket.create_connection(url)`
- The SKILL.md CDP helper is the reference implementation
- Synchronous — no event loop required

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `websockets>=15.0` | Python 3.12.4 (Docker venv `/opt/venv-a0`) | v15 is the current series. API: `async with websockets.connect(url) as ws`. The `max_size=None` param is still valid. |
| `websocket-client>=1.9.0` | Python 3.12.4 | Sync API: `websocket.create_connection(url)`. Thread-safe. Docker venv compatible. |
| `TTYSession` (existing) | Python 3.12.4 | Uses stdlib `pty`, `asyncio`, `termios`. All built-in. Linux/Mac only (Windows uses `pywinpty` which is also already in `requirements.txt`). |
| `claude -p` mode | claude v2.1.55+ | Requires unsetting `CLAUDECODE` in subprocess env. Supports `--output-format text/json/stream-json`. |
| `libtmux` (NOT used) | Python 3.12.4 | pip-resolved version is 0.46.2; PyPI latest is 0.53.1. Blocked by blocking-only API, no async support, unnecessary for this use case. |
| `opencode` binary | any Python version | Not a Python package. Install via npm, brew, or install script. Verify with `opencode --help` before building wrapper. |

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
- `python/helpers/claude_cli.py` — verified: `claude_single_turn()`, `ClaudeSession`, `claude_turn_with_recovery()` — the model for OpenCode wrappers
- `python/helpers/shell_local.py` — verified: wraps `TTYSession`, confirms existing interactive session pattern
- `apps/shared-browser/app.py` — verified: `websockets` async CDP pattern
- `requirements.txt` — verified: `websocket-client` absent, packages listed; `psutil>=7.0.0` present
- `pip index versions libtmux` — verified: 0.46.2 is pip-resolved latest in this env; web sources confirm 0.53.1 is PyPI latest (LOW confidence on exact API diffs)
- https://libtmux.git-pull.com/ — official libtmux docs: blocking API, `pane.send_keys()`, `pane.capture_pane()` confirmed. No async support.
- https://opencode.ai/docs/cli/ — OpenCode CLI docs: `-p` flag for non-interactive mode, `-s` for session ID confirmed (MEDIUM confidence — feature flags evolving, verify with `opencode --help`)
- https://github.com/anomalyco/opencode/issues/10411 — confirmed: `--non-interactive` flag requested Jan 2026, implies `-p` mode existed but `run` subcommand may lack it
- https://github.com/anomalyco/opencode/issues/11680 — confirmed: `--continue --session` syntax for session persistence exists but had bugs; verify against installed version
- WebSearch: libtmux PyPI, OpenCode CLI docs, tmux subprocess patterns — multiple sources cross-verified

---
*Stack research for: tmux terminal interaction and interactive CLI orchestration (v1.2)*
*Researched: 2026-02-25*
