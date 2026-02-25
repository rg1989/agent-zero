# Phase 11: tmux Primitive Infrastructure - Research

**Researched:** 2026-02-25
**Domain:** tmux CLI automation, Python subprocess, Agent Zero tool architecture
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TERM-01 | Agent Zero can send text + Enter to a named tmux pane in the shared terminal | `tmux send-keys -t shared <text> Enter` via subprocess.run — verified against existing terminal_agent.py pattern |
| TERM-02 | Agent Zero can send text without Enter to a named tmux pane (partial input for inline prompts) | `tmux send-keys -t shared <text>` (omit `Enter` key argument) — trivial variant of send action |
| TERM-03 | Agent Zero can send special keys (Ctrl+C, Ctrl+D, Tab, Escape, arrow keys) to a named tmux pane | `tmux send-keys -t shared C-c`, `Tab`, `Escape`, `Up`, `Down`, `Left`, `Right` — standard tmux key names confirmed |
| TERM-04 | Agent Zero can capture and read current terminal screen content from a tmux pane | `tmux capture-pane -t shared -p -S -500` (without `-e`) returns plain text; ANSI strip regex then cleans residuals |
</phase_requirements>

---

## Summary

Phase 11 creates `python/tools/tmux_tool.py` — a new Agent Zero tool providing four primitive actions (`send`, `keys`, `read`, plus a stub for `wait_ready` in Phase 12) against the shared tmux session (`shared:0.0` or just `shared`). This tool coexists with `terminal_agent.py` without conflict: the existing `terminal_agent.py` uses the sentinel pattern for non-interactive shell commands and must remain untouched per project requirements. The new `tmux_tool` is sentinel-free by design.

The technical implementation is straightforward: all four TERM-0x requirements map directly to 1-2 `tmux` CLI subcommands invoked via `subprocess.run`. The challenge is not the tmux API itself (well-documented, stable) but the constraints imposed by the shared-session design: no sentinel injection, ANSI stripping before parse, and correct target addressing (pane identifier format `session:window.pane` or short session name `shared`).

Agent Zero tool registration is automatic: place `tmux_tool.py` in `python/tools/` and `agent.system.tool.tmux.md` in `prompts/` — the `agent.system.tools.py` glob collects all `agent.system.tool.*.md` files automatically. No wiring in agent.py needed.

**Primary recommendation:** Create `tmux_tool.py` with actions dispatched via a `method` parameter (`send`, `keys`, `read`) modeled after how `code_execution_tool.py` dispatches on `runtime`. Use `subprocess.run` (not asyncio subprocess) to keep it simple — the tmux CLI completes instantly. Strip ANSI from `capture-pane` output using the pre-established project regex before returning to the agent.

---

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `tmux` CLI | System-installed in Docker (3.x) | Pane control via subprocess | Already the mechanism used by `terminal_agent.py`; shared session runs at `shared` |
| `subprocess.run` (stdlib) | Python 3.x stdlib | Synchronous tmux invocation | tmux commands complete instantly — no need for asyncio; matches terminal_agent.py precedent |
| `python/tools/Tool` base class | Project internal | Agent Zero tool contract | All tools subclass `Tool` and return `Response(message=..., break_loop=False)` |
| `re` (stdlib) | Python 3.x stdlib | ANSI strip regex on captured output | Pre-established project pattern from STATE.md and claude_cli.py |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `asyncio.sleep` (stdlib) | Python 3.x | Yield to event loop during polls | Only needed in Phase 12 `wait_ready`; Phase 11 primitives complete instantly |
| `prompts/agent.system.tool.tmux.md` | N/A | Agent-facing tool documentation | Required to teach agent the tool's actions, args, and usage examples |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `subprocess.run` | `asyncio.create_subprocess_exec` | Async version adds complexity with no benefit — tmux send-keys/capture-pane completes in <50ms |
| `subprocess.run` | `libtmux` Python library | Explicitly excluded in REQUIREMENTS.md: "Blocking-only API, version drift risk, just wraps 2-line subprocess calls" |
| `subprocess.run` | `pexpect` | Explicitly excluded in REQUIREMENTS.md: "Duplicates TTYSession + tmux approach; unnecessary dependency" |

**Installation:** No new dependencies. All stdlib. tmux is pre-installed in the shared-terminal Docker container.

---

## Architecture Patterns

### Recommended Project Structure

```
python/tools/tmux_tool.py        # New tool — send/keys/read actions
prompts/agent.system.tool.tmux.md  # Agent-facing documentation (auto-loaded by glob)
```

No other files needed for Phase 11. `wait_ready` action is Phase 12.

### Pattern 1: Tool Class Structure (matches existing project conventions)

**What:** Single `Tool` subclass dispatching on `method` argument, returning `Response`.
**When to use:** All four TERM-0x requirements handled as actions within one tool class.

```python
# python/tools/tmux_tool.py
import subprocess
import re
from python.helpers.tool import Tool, Response

_TMUX_SESSION = "shared"

# ANSI strip regex — pre-established project standard (STATE.md, claude_cli.py)
# Handles: 2-char ESC sequences, CSI sequences (color, cursor), OSC sequences (title)
ANSI_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07)')

class TmuxTool(Tool):

    async def execute(self, **kwargs):
        action = self.args.get("action", "").strip().lower()

        if action == "send":
            return await self._send()
        elif action == "keys":
            return await self._keys()
        elif action == "read":
            return await self._read()
        else:
            return Response(
                message=f"Unknown action '{action}'. Valid: send, keys, read.",
                break_loop=False,
            )
```

**Source:** Mirrors `code_execution_tool.py` dispatch pattern and `terminal_agent.py` tmux usage.

### Pattern 2: send Action (TERM-01)

**What:** Send text followed by Enter to the named pane. Command executes visibly in the user's terminal.
**When to use:** Running shell commands, submitting interactive prompts that require Enter.

```python
    async def _send(self):
        text = self.args.get("text", "").strip()
        pane = self.args.get("pane", _TMUX_SESSION)
        if not text:
            return Response(message="'text' argument is required for send action.", break_loop=False)

        result = subprocess.run(
            ["tmux", "send-keys", "-t", pane, text, "Enter"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return Response(
                message=f"tmux send failed: {result.stderr.strip()}\nIs shared-terminal running?",
                break_loop=False,
            )
        return Response(message=f"Sent to {pane}: {text!r} + Enter", break_loop=False)
```

### Pattern 3: keys Action (TERM-02 + TERM-03)

**What:** Send raw key sequences WITHOUT Enter. Supports both literal text (partial input) and special key names.
**When to use:** TERM-02 — partial text to inline prompt (`y/N`). TERM-03 — special keys (Ctrl+C, Tab, arrow keys).

```python
    async def _keys(self):
        keys = self.args.get("keys", "")
        pane = self.args.get("pane", _TMUX_SESSION)
        # keys is a list or space-separated string of tmux key names
        # e.g. ["C-c"] or "C-c" or "Tab" or "Escape" or "Up"
        if isinstance(keys, list):
            key_args = keys
        else:
            key_args = keys.split() if keys else []

        if not key_args:
            return Response(message="'keys' argument is required for keys action.", break_loop=False)

        result = subprocess.run(
            ["tmux", "send-keys", "-t", pane] + key_args,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return Response(
                message=f"tmux send-keys failed: {result.stderr.strip()}",
                break_loop=False,
            )
        return Response(message=f"Keys sent to {pane}: {key_args}", break_loop=False)
```

**Key names verified from tmux man page (man7.org):**

| Special Key | tmux send-keys Argument |
|-------------|------------------------|
| Ctrl+C | `C-c` |
| Ctrl+D | `C-d` |
| Tab | `Tab` |
| Escape | `Escape` |
| Arrow Up | `Up` |
| Arrow Down | `Down` |
| Arrow Left | `Left` |
| Arrow Right | `Right` |
| Enter | `Enter` |
| Backspace | `BSpace` |
| Shift+Tab | `BTab` |
| Page Up | `PPage` |
| Page Down | `NPage` |

### Pattern 4: read Action (TERM-04)

**What:** Capture current pane screen content. Returns plain text stripped of ANSI artifacts.
**When to use:** Reading terminal output, checking what is currently on screen.

```python
    async def _read(self):
        pane = self.args.get("pane", _TMUX_SESSION)
        lines = int(self.args.get("lines", 100))  # -S -N = last N lines of scrollback

        result = subprocess.run(
            ["tmux", "capture-pane", "-t", pane, "-p", "-S", f"-{lines}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return Response(
                message=f"tmux capture-pane failed: {result.stderr.strip()}\nIs shared-terminal running?",
                break_loop=False,
            )

        # Strip ANSI escape sequences before returning
        clean = ANSI_RE.sub('', result.stdout).rstrip()
        return Response(message=clean or "(pane is empty)", break_loop=False)
```

**CRITICAL:** Do NOT pass `-e` flag to `capture-pane`. Without `-e`, tmux strips most escape sequences before output. ANSI_RE handles any residuals (OSC title sequences, etc.).

### Pattern 5: Tool Prompt Auto-Registration

**What:** Agent Zero auto-loads all `agent.system.tool.*.md` files from the `prompts/` directory.
**When to use:** Whenever adding a new tool — no changes to agent.py needed.

The `prompts/agent.system.tools.py` plugin globs `agent.system.tool.*.md` and concatenates them into the `{{tools}}` variable in the system prompt. Creating `prompts/agent.system.tool.tmux.md` is sufficient to register the tool with the agent.

```markdown
<!-- prompts/agent.system.tool.tmux.md -->
### tmux_tool:

Interact with the shared tmux terminal session (the same terminal visible to the user).

#### Arguments:
* `action` (string, required) — one of: `send`, `keys`, `read`
* `text` (string) — for `send`: text to type followed by Enter
* `keys` (string or list) — for `keys`: tmux key names (e.g. `"C-c"`, `"Tab"`, `"Escape"`)
* `pane` (string, optional) — tmux pane target (default: `"shared"`)

#### Usage: run a command (send + Enter)
...
#### Usage: respond to inline prompt without Enter
...
#### Usage: interrupt a running process (Ctrl+C)
...
#### Usage: read current screen content
...
```

### Pane Target Format

The shared tmux session is named `shared` (created by `apps/shared-terminal/startup.sh`). The tmux target can be:
- Short name: `"shared"` — targets the first window, first pane (sufficient for this project)
- Full format: `"shared:0.0"` — explicit session:window.pane (use when needed for Phase 13+ multi-pane)

Default target in all actions: `"shared"`.

### Anti-Patterns to Avoid

- **Sentinel injection in `tmux_tool`:** Never write `echo MARKER:$?` or any marker text via `send-keys`. This tool replaces the sentinel pattern with screen capture + stability polling. Sentinels are reserved for `terminal_agent.py` only.
- **Using `-e` with `capture-pane`:** Requesting ANSI preservation defeats the purpose — output would require heavy parsing. Omit `-e` and apply ANSI_RE to clean residuals.
- **Using `subprocess.run` with `shell=True`:** Unnecessary for known tmux subcommand — use list form for safety.
- **Touching `terminal_agent.py`:** That tool uses the sentinel pattern for non-interactive shell commands. Do not modify it. Both tools coexist.
- **Using `asyncio.create_subprocess_exec`:** Overkill for tmux CLI calls that complete in <50ms. Use synchronous `subprocess.run`.
- **Using `libtmux` or `pexpect`:** Explicitly excluded in REQUIREMENTS.md.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mapping key names to terminal escape sequences | Custom key table / escape code injector | `tmux send-keys` with tmux key names | tmux handles all terminal-specific translation; handles terminfo differences across terminal emulators |
| PTY interaction for the shared session | TTYSession / pexpect / manual PTY | `tmux send-keys` + `capture-pane` | TTYSession creates isolated PTY subprocess — not connected to the user-visible tmux session (explicitly excluded in REQUIREMENTS.md) |
| ANSI parsing / terminal state tracking | State machine for VT100 sequences | Strip with ANSI_RE, work with plain text | Only need plain text content; full VT100 parsing is vastly more complex and not needed |

**Key insight:** tmux itself is the PTY multiplexer. Let tmux handle terminal encoding, key translation, and ANSI rendering. Our job is only to drive tmux via its CLI.

---

## Common Pitfalls

### Pitfall 1: ANSI Artifacts in capture-pane Output
**What goes wrong:** Even without `-e`, `tmux capture-pane` can include OSC sequences (terminal title updates, `\e]0;text\x07`) and some cursor positioning artifacts in scrollback. These corrupt pattern matching in Phase 12.
**Why it happens:** Applications running in the pane (bash, shells with PS1 tricks, CLI tools) emit OSC/control sequences as part of their normal operation. tmux's default mode strips color/attribute SGR codes but passes OSC title sequences through.
**How to avoid:** Always apply `ANSI_RE.sub('', text)` before returning `capture-pane` output. The regex is established in STATE.md:
```python
ANSI_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07)')
```
**Warning signs:** Captured output contains `\x1b]0;` or similar sequences when printed.

### Pitfall 2: Wrong Pane Target
**What goes wrong:** `tmux send-keys -t shared` fails with "no server running on..." or "can't find target pane" if the shared-terminal app is not running.
**Why it happens:** The shared tmux session is created by `apps/shared-terminal/startup.sh` only when the app is started. If the app is not running, there is no tmux server or no `shared` session.
**How to avoid:** Check `result.returncode != 0` and return a helpful error message directing the agent to open the shared-terminal app first (`open_app` with `app: "shared-terminal"`).
**Warning signs:** `tmux` returns non-zero with stderr "no server running" or "can't find session".

### Pitfall 3: send-keys Without -l Flag Interprets Special Characters
**What goes wrong:** If `text` contains key names like `Tab` or `Enter` as literal words, tmux may interpret them as key presses.
**Why it happens:** `tmux send-keys` performs key name lookup on each space-separated token by default.
**How to avoid:** For the `send` action (literal text + Enter), pass the text as a SINGLE argument to send-keys (no splitting). tmux treats a single quoted/list-element argument as literal text to type. The `Enter` key is passed as a separate argument.
```python
["tmux", "send-keys", "-t", pane, text, "Enter"]
#                                    ^^^^ literal string  ^^^^^ key name
```
For `keys` action, each element of `key_args` IS a key name — this is intentional.
**Warning signs:** Sending `"Tab"` as text types the key Tab instead of the characters T-a-b.

### Pitfall 4: Capturing Too Many Scrollback Lines (Performance)
**What goes wrong:** Using `-S -5000` to capture 5000 lines of history is slow and returns megabytes of data.
**Why it happens:** tmux scrollback buffer can be large; `-S -N` captures N lines of history above the current view.
**How to avoid:** Default to `-S -100` (100 lines). Allow agent to specify more via `lines` argument. `terminal_agent.py` uses `-S -500` — 100 is sufficient for primitive screen reading.
**Warning signs:** `read` action returns very slowly or floods the agent context with terminal history.

### Pitfall 5: Mistaking `send` for `keys` (or vice versa)
**What goes wrong:** Agent uses `send` action to send `"C-c"` expecting Ctrl+C — but `send` adds Enter after the literal characters C-c.
**Why it happens:** Two actions with similar purposes but different semantics.
**How to avoid:** Clear prompt documentation distinguishing `send` (text + Enter) vs `keys` (key names, no Enter).
- `send`: Type text and press Enter — for running commands
- `keys`: Send key sequence without Enter — for special keys and partial input

---

## Code Examples

Verified patterns from official sources and project code:

### Complete tmux_tool.py Skeleton

```python
# python/tools/tmux_tool.py
import subprocess
import re
from python.helpers.tool import Tool, Response

_TMUX_SESSION = "shared"

# Pre-established project ANSI strip regex (STATE.md, claude_cli.py)
# Covers: 2-char ESC sequences, CSI color/cursor, OSC title sequences
ANSI_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07)')


class TmuxTool(Tool):
    """
    Primitive tmux interface for the shared terminal session.

    Actions:
      send  — type text + Enter (TERM-01)
      keys  — send key sequence without Enter (TERM-02, TERM-03)
      read  — capture current pane screen content (TERM-04)

    Coexists with terminal_agent.py (sentinel pattern). This tool is
    sentinel-free: observation via capture-pane + stability polling only.
    """

    async def execute(self, **kwargs):
        action = self.args.get("action", "").strip().lower()
        dispatch = {
            "send": self._send,
            "keys": self._keys,
            "read": self._read,
        }
        handler = dispatch.get(action)
        if not handler:
            return Response(
                message=f"Unknown action '{action}'. Valid actions: send, keys, read.",
                break_loop=False,
            )
        return await handler()

    async def _send(self):
        text = self.args.get("text", "")
        pane = self.args.get("pane", _TMUX_SESSION)
        if not text:
            return Response(message="'text' is required for send.", break_loop=False)
        result = subprocess.run(
            ["tmux", "send-keys", "-t", pane, text, "Enter"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return Response(
                message=f"send failed: {result.stderr.strip()}\nIs shared-terminal running?",
                break_loop=False,
            )
        return Response(message=f"Sent: {text!r} + Enter", break_loop=False)

    async def _keys(self):
        keys = self.args.get("keys", "")
        pane = self.args.get("pane", _TMUX_SESSION)
        if isinstance(keys, list):
            key_args = keys
        elif isinstance(keys, str):
            key_args = keys.split() if keys.strip() else []
        else:
            key_args = []
        if not key_args:
            return Response(message="'keys' is required for keys action.", break_loop=False)
        result = subprocess.run(
            ["tmux", "send-keys", "-t", pane] + key_args,
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return Response(
                message=f"keys failed: {result.stderr.strip()}",
                break_loop=False,
            )
        return Response(message=f"Keys sent: {key_args}", break_loop=False)

    async def _read(self):
        pane = self.args.get("pane", _TMUX_SESSION)
        lines = int(self.args.get("lines", 100))
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", pane, "-p", "-S", f"-{lines}"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return Response(
                message=f"read failed: {result.stderr.strip()}\nIs shared-terminal running?",
                break_loop=False,
            )
        clean = ANSI_RE.sub('', result.stdout).rstrip()
        return Response(message=clean or "(pane is empty)", break_loop=False)
```

### Tool Prompt Template (agent.system.tool.tmux.md)

```markdown
### tmux_tool:

Interact directly with the shared tmux terminal (same session visible to the user).
Use this tool for interactive CLI orchestration — NOT for simple shell commands (use `terminal_agent` for those).

**REQUIRED STEP BEFORE USE**: call `open_app` first with `{ "action": "open", "app": "shared-terminal" }`

!!! The shared tmux session is named `shared` — all actions target it by default
!!! `send` types text + Enter; `keys` sends key sequences without Enter
!!! `read` captures what is currently visible on screen (ANSI-stripped plain text)
!!! No sentinel markers are ever injected — screen capture is the only observation mechanism

#### Arguments:
* `action` (string, required) — `send` | `keys` | `read`
* `text` (string) — for `send`: the text to type (Enter is added automatically)
* `keys` (string or list) — for `keys`: tmux key names separated by spaces e.g. `"C-c"`, `"Tab"`, `"Escape"`, `"Up Down Left Right"`
* `pane` (string, optional) — tmux pane target (default: `"shared"`)
* `lines` (number, optional) — for `read`: number of scrollback lines to capture (default: 100)

#### Usage: run a command
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "send", "text": "ls -la" } }
```

#### Usage: answer inline y/N prompt (no Enter)
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "keys", "keys": "y" } }
```

#### Usage: interrupt running process
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "keys", "keys": "C-c" } }
```

#### Usage: read current terminal screen
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "read" } }
```

#### Special key names:
`C-c` (Ctrl+C), `C-d` (Ctrl+D), `Tab`, `BTab` (Shift+Tab), `Escape`, `Enter`,
`Up`, `Down`, `Left`, `Right`, `BSpace`, `PPage` (Page Up), `NPage` (Page Down)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `terminal_agent.py` sentinel pattern | New `tmux_tool` without sentinel | Phase 11 | Enables interactive CLI use — sentinel breaks interactive programs |
| Single monolithic terminal tool | Two coexisting tools (terminal_agent + tmux_tool) | Phase 11 | `terminal_agent` stays for simple commands; `tmux_tool` for interactive sessions |
| Single action per tool | Action dispatch on `method` arg | Already present in code_execution_tool | Consolidates related primitives in one tool class |

**Deprecated/outdated:**
- `TTYSession` for shared terminal interaction: Explicitly excluded — creates isolated PTY not connected to the user-visible tmux session.

---

## Open Questions

1. **`keys` action argument format: string vs list**
   - What we know: Agent Zero tool args are JSON — the agent can pass a JSON array for `keys` or a space-separated string
   - What's unclear: Whether the LLM will reliably produce a JSON array vs a string; which is easier to prompt for
   - Recommendation: Accept both in `_keys()` (already handled in skeleton above); prompt documentation should show space-separated string format as primary example (`"C-c"`, `"Tab Escape"`)

2. **Phase 11 plan scope: one plan or two?**
   - The ROADMAP lists a single plan: `11-01-PLAN.md — Create python/tools/tmux_tool.py ... and prompts/agent.system.tool.tmux.md`
   - This is appropriate — both files are small and coupled; a single plan is correct
   - Recommendation: Single plan covering both files

3. **Default `lines` for `read` action**
   - `terminal_agent.py` uses `-S -500`; 100 is more conservative
   - What's unclear: Whether 100 lines is sufficient for Phase 12+ use cases (prompt detection needs to see the last prompt)
   - Recommendation: Use 100 as default; document that agent can override with `lines: 200` etc.

---

## Sources

### Primary (HIGH confidence)
- `/Users/rgv250cc/Documents/Projects/agent-zero/python/tools/terminal_agent.py` — existing tmux send-keys + capture-pane pattern (direct code reading)
- `/Users/rgv250cc/Documents/Projects/agent-zero/python/helpers/tool.py` — Tool base class and Response dataclass (direct code reading)
- `/Users/rgv250cc/Documents/Projects/agent-zero/prompts/agent.system.tools.py` — tool auto-registration via `agent.system.tool.*.md` glob (direct code reading)
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/REQUIREMENTS.md` — explicit exclusions: libtmux, pexpect, TTYSession, sentinel in shared session (direct read)
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/STATE.md` — locked decisions: ANSI regex, no sentinel, `tmux_tool` as new class (direct read)
- [tmux man page — man7.org](https://man7.org/linux/man-pages/man1/tmux.1.html) — `capture-pane` flags (`-p`, `-S`, `-e`), `send-keys` special key names (WebFetch verified)

### Secondary (MEDIUM confidence)
- [What Are the Valid Keys for tmux — Baeldung](https://www.baeldung.com/linux/tmux-keys) — key name table verified against man page
- [How to use tmux send-keys — tmuxai.dev](https://tmuxai.dev/tmux-send-keys/) — usage patterns cross-verified with existing terminal_agent.py code

### Tertiary (LOW confidence)
- None — all critical claims verified against project source code or official documentation.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components confirmed from project source code (terminal_agent.py, tool.py, requirements)
- Architecture patterns: HIGH — tool structure confirmed from code_execution_tool.py precedent; tmux API verified from man page
- Pitfalls: HIGH — ANSI and pane-not-found pitfalls confirmed from existing terminal_agent.py code and STATE.md decisions; send-keys literal vs key-name behavior confirmed from tmux man page

**Research date:** 2026-02-25
**Valid until:** 2026-08-25 (tmux CLI is extremely stable; tool registration pattern is project-internal)
