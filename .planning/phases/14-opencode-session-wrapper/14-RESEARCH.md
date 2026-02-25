# Phase 14: OpenCode Session Wrapper - Research

**Researched:** 2026-02-25
**Domain:** Python class design, tmux-based CLI orchestration wrapper, ClaudeSession pattern mirroring
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLI-05 | Agent Zero can use a pre-built `OpenCodeSession` wrapper with `.start()` / `.send(prompt)` / `.exit()` interface, mirroring `ClaudeSession` | `ClaudeSession` in `python/helpers/claude_cli.py` is the direct model to mirror. `OPENCODE_PROMPT_PATTERN` and `OPENCODE_START_TIMEOUT` are already exported from `python/tools/tmux_tool.py` for import. The three-step exit sequence (C-p → "exit" → wait_ready) is empirically verified and must be encoded in `.exit()`. |
</phase_requirements>

---

## Summary

Phase 14 creates `python/helpers/opencode_cli.py` — a Python helper module that wraps the Phase 13 tmux_tool primitives behind a clean `OpenCodeSession` class with `.start()`, `.send(prompt)`, and `.exit()` methods. The interface mirrors `ClaudeSession` in `python/helpers/claude_cli.py`: a stateful Python object that hides the plumbing (tmux subcommands, prompt patterns, exit sequences) so skill code can orchestrate OpenCode without any direct tmux knowledge.

The implementation has one key architectural difference from `ClaudeSession`: `ClaudeSession` wraps `subprocess.run()` (blocking, process-completion signal) while `OpenCodeSession` wraps async tmux calls (tmux send-keys + wait_ready polling). This means `OpenCodeSession` must be either an async class or a sync wrapper over asyncio — mirroring the pattern used by `TmuxTool` in `python/tools/tmux_tool.py`. Since `TmuxTool` methods are all `async def`, `OpenCodeSession` must call them via `asyncio.run()` or be an async class itself.

All empirical facts needed by Phase 14 already exist in Phase 13 artifacts: `OPENCODE_PROMPT_PATTERN` and `OPENCODE_START_TIMEOUT` are exported from `python/tools/tmux_tool.py`, the verified three-step exit sequence (Ctrl+P → "exit" → wait_ready) is documented in `prompts/agent.system.tool.tmux.md` and `13-02-SUMMARY.md`, and the full lifecycle (start → wait_ready → send → wait_ready → read → exit) is validated end-to-end. Phase 14 is pure encoding work: no new empirical discovery required.

**Primary recommendation:** Create `python/helpers/opencode_cli.py` modeled directly on `python/helpers/claude_cli.py` — same file structure, same class pattern (`OpenCodeSession` mirrors `ClaudeSession`), but calling `subprocess.run(["tmux", ...])` directly (like `TmuxTool` does) rather than subprocess.run on the opencode binary.

---

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `python/tools/tmux_tool.py` | Project-local (Phase 11/12) | Source of `OPENCODE_PROMPT_PATTERN`, `OPENCODE_START_TIMEOUT`, `ANSI_RE`, tmux command patterns | All four verified primitives and constants already implemented; Phase 14 imports, not re-implements |
| `python/helpers/claude_cli.py` | Project-local (Phase 9) | `ClaudeSession` — the exact interface pattern to mirror | `.start()` / `.send()` / `.exit()` maps to `ClaudeSession.__init__()` / `.turn()` / `.reset()` conceptually; adapt naming to match ROADMAP spec |
| Python stdlib `subprocess` | 3.x | `tmux send-keys` and `tmux capture-pane` calls | Same pattern as `TmuxTool._send()` / `_read()` / `_wait_ready()` — subprocess.run list-form only, never shell=True |
| Python stdlib `asyncio` | 3.x | Required because `TmuxTool` methods are async; `OpenCodeSession` is synchronous interface over async tmux calls | Use `asyncio.run()` wrapper OR implement as sync using direct subprocess calls (preferred — see Architecture) |
| Python stdlib `re`, `time` | 3.x | ANSI stripping, timeout polling in wait_ready | Already in `tmux_tool.py`; copy `ANSI_RE` pattern or import from tmux_tool |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `OPENCODE_PROMPT_PATTERN` (import from tmux_tool) | Phase 13 | Regex matching OpenCode TUI ready state | Used in `wait_ready` calls in `.start()` and `.send()` |
| `OPENCODE_START_TIMEOUT` (import from tmux_tool) | Phase 13 | 15s startup timeout | Used in `.start()` wait_ready call |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct subprocess tmux calls in opencode_cli.py | Importing and calling TmuxTool methods | TmuxTool is a `Tool` subclass with async execute(); calling it directly outside the Agent Zero tool dispatch loop is awkward. Direct subprocess calls (same 2-3 lines TmuxTool uses) are cleaner and don't require asyncio.run() boilerplate in the helper module. |
| `OpenCodeSession` as async class | Sync class with direct subprocess | Skill code uses `code_execution_tool` with Python runtime — synchronous by default. Sync class is simpler for callers. TmuxTool's subprocess calls are all blocking subprocess.run() anyway; the async in TmuxTool is only to yield control in the Agent Zero async loop. |
| Hard timeout + `process.terminate()` | tmux `C-c` key | The Phase 14 ROADMAP specifies "hard timeout with process.terminate() on expiry" for the v0.15 hang regression. However, v1.2.14 has the regression fixed. Implement the timeout guard in `.send()` as documented in ROADMAP — surface a clear error rather than hanging — but the terminate mechanism is against the tmux session process (send C-c), not a Python subprocess. |

**Installation:** No new packages required. All stdlib. No `pip install` step needed.

---

## Architecture Patterns

### Recommended Project Structure

```
python/helpers/opencode_cli.py      # New file — OpenCodeSession class
python/tools/tmux_tool.py           # Source of OPENCODE_PROMPT_PATTERN, OPENCODE_START_TIMEOUT (import from here)
python/helpers/claude_cli.py        # Reference model — study ClaudeSession interface
```

### Pattern 1: OpenCodeSession Interface (mirrors ClaudeSession)

**What:** A stateful Python class encapsulating the full OpenCode TUI lifecycle. Callers interact only with `.start()`, `.send(prompt)`, `.exit()`. No tmux knowledge required.

**When to use:** Any skill code that needs to orchestrate an OpenCode session.

**Interface spec (from ROADMAP success criteria):**

```python
# Source: .planning/ROADMAP.md Phase 14 Success Criteria + ClaudeSession pattern from claude_cli.py

class OpenCodeSession:
    """
    Stateful wrapper around OpenCode TUI lifecycle via tmux.

    Mirrors ClaudeSession from python/helpers/claude_cli.py.
    Hides tmux plumbing: OPENCODE_PROMPT_PATTERN, exit sequences, wait_ready loops.

    Usage:
        session = OpenCodeSession()
        session.start()
        response1 = session.send("What does /a0/python/tools/tmux_tool.py do?")
        response2 = session.send("How many lines is it?")
        session.exit()
    """

    def start(self) -> None:
        """
        Start OpenCode TUI in the shared tmux session.
        Sends 'opencode /a0' + Enter, waits for OPENCODE_PROMPT_PATTERN.
        Raises RuntimeError if TUI does not reach ready state within OPENCODE_START_TIMEOUT.
        """

    def send(self, prompt: str) -> str:
        """
        Send one prompt to the running OpenCode TUI. Returns response text.
        Types prompt + Enter, waits for OPENCODE_PROMPT_PATTERN (timeout=120s),
        then reads and returns the pane content.
        Raises RuntimeError if response timeout exceeded.
        """

    def exit(self) -> None:
        """
        Exit OpenCode cleanly via Ctrl+P palette + 'exit' + Enter.
        Waits for default shell prompt pattern to confirm shell returned.
        """
```

**Key differences from ClaudeSession:**

| `ClaudeSession` | `OpenCodeSession` |
|-----------------|-------------------|
| Wraps `subprocess.run(['claude', ...])` | Wraps `subprocess.run(['tmux', 'send-keys', ...])` |
| Completion signal: process returncode | Completion signal: `wait_ready` prompt pattern match |
| State: `_session_id` (UUID string) | State: `_running` (bool) |
| No terminal artifact handling | Must strip ANSI before returning response text |
| `turn()` method | `send()` method (per ROADMAP spec) |
| `reset()` method | `exit()` method (per ROADMAP spec) |

### Pattern 2: Implementing send() with Response Extraction

**What:** After sending a prompt and wait_ready, the captured pane contains TUI chrome (borders, model name, hints bar) mixed with the actual response. Response extraction requires stripping the boilerplate and returning only the message content.

**When to use:** Inside `send()` — after wait_ready returns "ready (prompt matched)" or "ready (stable)".

**Implementation approach:**

```python
# Source: 13-01-OBSERVATION.md — pane structure after response
# After response completes, the pane shows:
#   - Conversation history (messages above input area)
#   - Input widget (┃ lines with model selector)
#   - Hints bar: "ctrl+t variants  tab agents  ctrl+p commands    • OpenCode 1.2.14"
#   - Status bar: "/a0  ...  1.2.14" (initial state)
#
# Response text is the NEW content added since the last captured state.
# Simplest approach: return the full pane content and let the caller parse,
# OR diff the "before send" capture against the "after response" capture.
# For v1 (Phase 14), returning the full cleaned pane content is acceptable.

def send(self, prompt: str) -> str:
    # 1. Send the prompt
    subprocess.run(["tmux", "send-keys", "-t", _TMUX_SESSION, prompt, "Enter"],
                   capture_output=True, text=True)

    # 2. Wait for ready state (OpenCode TUI post-response pattern)
    ready_content = self._wait_ready(timeout=120, prompt_pattern=OPENCODE_PROMPT_PATTERN)

    # 3. Read full pane (300 lines captures full response)
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", _TMUX_SESSION, "-p", "-S", "-300"],
        capture_output=True, text=True
    )
    clean = ANSI_RE.sub("", result.stdout).rstrip()

    return clean  # Caller sees full clean pane; response is visible in context
```

**Note:** The ROADMAP says "receive the response" — full pane content is an acceptable v1 return. Phase 15 skill doc can document how callers should interpret it. A differential approach (capture before/after) is an enhancement, not a v1 requirement.

### Pattern 3: Implementing _wait_ready() (sync version of TmuxTool._wait_ready)

**What:** Synchronous polling loop — the same algorithm as `TmuxTool._wait_ready` but without `asyncio.sleep`. Uses `time.sleep(0.5)` instead.

**When to use:** Called internally by `start()` and `send()`.

```python
# Source: python/tools/tmux_tool.py _wait_ready() — direct sync translation
import time, subprocess, re

def _wait_ready(self, timeout: float, prompt_pattern: str) -> str:
    """
    Poll tmux pane until prompt_pattern matches last non-blank line, or timeout.
    Returns cleaned pane content.
    Raises RuntimeError on timeout.
    """
    prompt_re = re.compile(prompt_pattern)
    deadline = time.time() + timeout
    prev_content = None
    time.sleep(0.3)  # Brief initial delay (same as async version)

    while time.time() < deadline:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", _TMUX_SESSION, "-p", "-S", "-50"],
            capture_output=True, text=True
        )
        clean = ANSI_RE.sub("", result.stdout).rstrip()
        lines = [l for l in clean.splitlines() if l.strip()]

        # Strategy 1: prompt pattern match
        if lines and prompt_re.search(lines[-1]):
            return clean

        # Strategy 2: stability fallback
        if prev_content is not None and clean == prev_content:
            return clean

        prev_content = clean
        time.sleep(0.5)

    raise RuntimeError(f"OpenCode wait_ready timed out after {timeout}s")
```

### Pattern 4: Implementing exit() with Verified 3-Step Sequence

**What:** The empirically verified exit method for OpenCode v1.2.14. Direct `/exit` via `send` does NOT work — the `/` key opens the AGENT PICKER.

**When to use:** Called by `.exit()` method — always this exact sequence.

```python
# Source: 13-02-SUMMARY.md "Decisions Made" + prompts/agent.system.tool.tmux.md CLI-04 section
# Empirically verified: Ctrl+P (C-p) opens commands palette, 'exit' filters to
# "Exit the app", Enter executes it. Shell prompt returns in 1-2 seconds.

def exit(self) -> None:
    # Step 1: Open commands palette
    subprocess.run(["tmux", "send-keys", "-t", _TMUX_SESSION, "C-p"],
                   capture_output=True, text=True)
    time.sleep(0.2)  # Brief pause for palette to open

    # Step 2: Type 'exit' to filter command list
    subprocess.run(["tmux", "send-keys", "-t", _TMUX_SESSION, "exit", "Enter"],
                   capture_output=True, text=True)

    # Step 3: Wait for shell prompt to return
    self._wait_ready(timeout=15, prompt_pattern=r'[$#>%]\s*$')
    self._running = False
```

**CRITICAL:** Do NOT use `tmux send-keys -t shared '/exit' Enter`. The `/` character immediately opens the AGENT PICKER in v1.2.14. This is documented in `13-02-SUMMARY.md` as the primary auto-fixed deviation.

### Pattern 5: Module Structure (mirrors claude_cli.py)

**What:** File organization mirroring `python/helpers/claude_cli.py` — module-level constants, standalone functions, then the class.

```python
# python/helpers/opencode_cli.py structure
"""
opencode_cli.py - OpenCode TUI session wrapper via tmux.

Implements OpenCodeSession: a stateful wrapper with .start()/.send()/.exit()
interface mirroring ClaudeSession in python/helpers/claude_cli.py.

Empirically verified: 2026-02-25, OpenCode v1.2.14, Docker aarch64.
"""
import subprocess
import re
import time

# Import verified constants from Phase 13 artifacts
from python.tools.tmux_tool import OPENCODE_PROMPT_PATTERN, OPENCODE_START_TIMEOUT, ANSI_RE

_TMUX_SESSION = "shared"
_OPENCODE_RESPONSE_TIMEOUT = 120  # seconds — AI response budget

# [Module-level docstring for constants]
# [OpenCodeSession class]
```

### Anti-Patterns to Avoid

- **Using `send "/exit"` for exit:** Direct `/exit` send opens AGENT PICKER in v1.2.14. Use the 3-step Ctrl+P sequence. This is the most critical gotcha from Phase 13.
- **Calling TmuxTool as an Agent Zero Tool dispatch:** `TmuxTool` is a `Tool` subclass designed for the Agent Zero async tool loop. Calling it from a helper module bypasses the Tool lifecycle. Use direct `subprocess.run(["tmux", ...])` calls instead — same commands, no Tool dispatch.
- **Making OpenCodeSession async:** Skill code runs synchronously in `code_execution_tool` Python runtime. An async class requires `asyncio.run()` boilerplate at every call site. Sync class with `time.sleep()` polling is correct.
- **Re-hardcoding OPENCODE_PROMPT_PATTERN:** Import it from `python.tools.tmux_tool`. It's already the verified constant. Do not copy-paste the regex string — importing ensures a single source of truth.
- **Using `shell=True` in subprocess.run:** The project-wide pattern is list-form subprocess only. `shell=True` creates security and escaping risks. All TmuxTool calls use list-form.
- **Assuming `/exit` enter behavior:** The observation showed that `send` action in TmuxTool appends Enter automatically. In `OpenCodeSession`, using direct `subprocess.run(["tmux", "send-keys", ..., "Exit", "Enter"])` must handle the Ctrl+P key separately — send-keys for `C-p` does NOT append Enter.
- **Not stripping ANSI before returning:** The pane content will contain residual TUI chrome. Always `ANSI_RE.sub("", raw)` before returning.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ANSI stripping | New regex pattern | `ANSI_RE` from `python.tools.tmux_tool` | Already handles OSC + CSI + 2-char sequences with correct branch ordering (Phase 11 decision) |
| OpenCode ready-state pattern | Invent new regex | `OPENCODE_PROMPT_PATTERN` from `python.tools.tmux_tool` | Empirically verified in Phase 13 against v1.2.14; encodes observed reality |
| Startup timeout value | Guess a number | `OPENCODE_START_TIMEOUT` from `python.tools.tmux_tool` | Observed 1.5s startup + 10x buffer; already the right value |
| wait_ready polling loop | New polling mechanism | Copy `_wait_ready` pattern from `TmuxTool._wait_ready` (sync translation) | The dual-strategy (prompt match + stability fallback) is already correct; just remove asyncio.sleep, use time.sleep |
| tmux send/capture commands | New subprocess patterns | Same `["tmux", "send-keys", "-t", pane, text, "Enter"]` / `["tmux", "capture-pane", "-t", pane, "-p", "-S", "-N"]` from `TmuxTool._send()` / `TmuxTool._read()` | Don't reinvent these; copy the exact subprocess calls |

**Key insight:** Phase 13 already assembled all the components. Phase 14 is a wiring job: put the verified pieces into a class with the right interface.

---

## Common Pitfalls

### Pitfall 1: Wrong exit sequence — AGENT PICKER trap

**What goes wrong:** `session.exit()` calls `subprocess.run(["tmux", "send-keys", "-t", "shared", "/exit", "Enter"])`. The `/` character opens OpenCode's AGENT PICKER. "exit" goes into the agent search box. The TUI stays open. Shell prompt never returns.

**Why it happens:** In OpenCode v1.2.14, the `/` key in the TUI input area is bound to the AGENT PICKER shortcut — not command autocomplete as documented. This is a v1.2.14 behavior change discovered empirically in Phase 13, Plan 02.

**How to avoid:** Always use the 3-step Ctrl+P sequence: `send-keys C-p` (palette), `send-keys exit Enter` (filter + confirm), then `wait_ready(timeout=15)` with the default shell pattern. This is the ONLY verified exit method.

**Warning signs:** `exit()` returns but `_running` is still True; subsequent `send()` calls see TUI content instead of shell prompt. Or: `_wait_ready` times out in `exit()` because shell prompt never appears.

### Pitfall 2: Importing TmuxTool as a module causes circular import or wrong context

**What goes wrong:** Attempting to `from python.tools.tmux_tool import TmuxTool` and then calling `TmuxTool._send()` directly raises AttributeError or fails because the Tool class requires context injection.

**Why it happens:** `TmuxTool` is a `Tool` subclass; all its methods access `self.args` (tool call arguments) and return `Response` objects — it's designed for the Agent Zero tool dispatch loop, not direct Python calls.

**How to avoid:** Import ONLY constants from `tmux_tool`: `from python.tools.tmux_tool import OPENCODE_PROMPT_PATTERN, OPENCODE_START_TIMEOUT, ANSI_RE`. Implement tmux operations directly in `opencode_cli.py` using `subprocess.run(["tmux", ...])` — same commands, no Tool class involvement.

### Pitfall 3: send() timing issue on fresh TUI start

**What goes wrong:** The first `send()` call after `start()` sees the TUI but the Enter key from the first prompt is consumed before the TUI input widget is fully active. The prompt appears to be sent but no response arrives.

**Why it happens:** 13-02-SUMMARY.md "Issues Encountered" documents: "first prompt Enter was sent before the TUI fully registered the text — required sending a second explicit Enter. This is consistent with OBSERVATION.md note about split send + keys being more reliable for the initial fresh startup."

**How to avoid:** Add a 0.2-0.5s sleep between `start()` and the first `send()` call, OR have `send()` add a brief pause before sending on the first call. Document in the class docstring that callers should `start()` and then immediately call `send()` — the internal delay handles the timing.

**Warning signs:** First `send()` after `start()` times out or returns the startup screen content unchanged.

### Pitfall 4: ANSI_RE import ordering issue

**What goes wrong:** If `ANSI_RE` is defined independently in `opencode_cli.py` without the OSC branch ordering fix, ANSI stripping misses some sequences. Box-drawing characters from the TUI survive and appear in the returned response text.

**Why it happens:** The Phase 11 STATE.md decision: "ANSI_RE OSC branch must precede 2-char branch: `]` (0x5D) falls in `\-_` range so ordering matters." A naively written pattern fails on OSC sequences.

**How to avoid:** Import `ANSI_RE` from `python.tools.tmux_tool` — don't redefine it. The correct pattern is already validated and used throughout the project.

### Pitfall 5: Response timeout with no clear error

**What goes wrong:** `send()` blocks for 120 seconds and then returns an ambiguous "timed out" message. The caller doesn't know whether OpenCode is still processing, hung, or crashed.

**Why it happens:** AI response latency is variable. If Ollama is not running or a model is being pulled, OpenCode shows a spinner indefinitely.

**How to avoid:** The ROADMAP says to "surface a clear error rather than hanging indefinitely." Raise `RuntimeError` (not just return a timeout string) so the caller sees an exception. Message should include timeout value and hint about Ollama connectivity. From STATE.md: "If the OpenCode version is affected by the `opencode run` hang regression (v0.15+), the wrapper applies a hard timeout with `process.terminate()` on expiry." For the tmux-based wrapper, this means: after `_wait_ready` timeout, send `C-c` to interrupt the ongoing request, then surface the error.

### Pitfall 6: send() called before start()

**What goes wrong:** `session.send("hello")` before `session.start()` sends text to whatever is currently in the shared tmux pane (shell prompt, or another process). Unpredictable behavior.

**Why it happens:** No guard on the running state.

**How to avoid:** Add a `_running` flag. `send()` raises `RuntimeError("OpenCodeSession not started — call start() first")` if `_running` is False. `start()` sets `_running = True`. `exit()` sets `_running = False`.

---

## Code Examples

Verified patterns from project source:

### Full OpenCodeSession class skeleton

```python
# Source: pattern from python/helpers/claude_cli.py ClaudeSession + tmux_tool.py _wait_ready()
import subprocess
import re
import time

from python.tools.tmux_tool import OPENCODE_PROMPT_PATTERN, OPENCODE_START_TIMEOUT, ANSI_RE

_TMUX_SESSION = "shared"
_OPENCODE_RESPONSE_TIMEOUT = 120


class OpenCodeSession:
    """
    Stateful wrapper around OpenCode TUI lifecycle via tmux.
    Mirrors ClaudeSession from python/helpers/claude_cli.py.

    All empirical patterns from Phase 13 (13-01-OBSERVATION.md, 13-02-SUMMARY.md).

    Usage:
        session = OpenCodeSession()
        session.start()
        r1 = session.send("What does /a0/python/tools/tmux_tool.py do?")
        r2 = session.send("How many lines is it?")
        session.exit()
    """

    def __init__(self, response_timeout: int = _OPENCODE_RESPONSE_TIMEOUT):
        self._running = False
        self._response_timeout = response_timeout

    def start(self) -> None:
        """Start OpenCode TUI, wait for initial ready state."""
        subprocess.run(
            ["tmux", "send-keys", "-t", _TMUX_SESSION,
             "export PATH=/root/.opencode/bin:$PATH && opencode /a0", "Enter"],
            capture_output=True, text=True,
        )
        self._wait_ready(timeout=OPENCODE_START_TIMEOUT, prompt_pattern=OPENCODE_PROMPT_PATTERN)
        self._running = True

    def send(self, prompt: str) -> str:
        """Send one prompt, wait for response, return cleaned pane content."""
        if not self._running:
            raise RuntimeError("OpenCodeSession not started — call start() first")
        subprocess.run(
            ["tmux", "send-keys", "-t", _TMUX_SESSION, prompt, "Enter"],
            capture_output=True, text=True,
        )
        self._wait_ready(timeout=self._response_timeout, prompt_pattern=OPENCODE_PROMPT_PATTERN)
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", _TMUX_SESSION, "-p", "-S", "-300"],
            capture_output=True, text=True,
        )
        return ANSI_RE.sub("", result.stdout).rstrip()

    def exit(self) -> None:
        """Exit via Ctrl+P palette + 'exit' + Enter. Wait for shell prompt return."""
        if not self._running:
            return
        # Step 1: Open commands palette
        subprocess.run(["tmux", "send-keys", "-t", _TMUX_SESSION, "C-p"],
                       capture_output=True, text=True)
        time.sleep(0.2)
        # Step 2: Filter to 'Exit the app' and execute
        subprocess.run(["tmux", "send-keys", "-t", _TMUX_SESSION, "exit", "Enter"],
                       capture_output=True, text=True)
        # Step 3: Wait for shell prompt
        self._wait_ready(timeout=15, prompt_pattern=r'[$#>%]\s*$')
        self._running = False

    def _wait_ready(self, timeout: float, prompt_pattern: str) -> str:
        """Synchronous polling until prompt_pattern matches or timeout. Raises RuntimeError."""
        prompt_re = re.compile(prompt_pattern)
        deadline = time.time() + timeout
        prev_content = None
        time.sleep(0.3)  # Initial delay (Phase 12 decision)

        while time.time() < deadline:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", _TMUX_SESSION, "-p", "-S", "-50"],
                capture_output=True, text=True,
            )
            clean = ANSI_RE.sub("", result.stdout).rstrip()
            lines = [l for l in clean.splitlines() if l.strip()]
            if lines and prompt_re.search(lines[-1]):
                return clean
            if prev_content is not None and clean == prev_content:
                return clean
            prev_content = clean
            time.sleep(0.5)

        # Timeout — interrupt ongoing request with C-c and raise
        subprocess.run(["tmux", "send-keys", "-t", _TMUX_SESSION, "C-c"],
                       capture_output=True, text=True)
        raise RuntimeError(
            f"OpenCode wait_ready timed out after {timeout}s. "
            "Check Ollama is running (host:11434) and OpenCode TUI is active."
        )

    @property
    def running(self) -> bool:
        """True if session has been started and not yet exited."""
        return self._running
```

### Skill code usage pattern (what CLI-05 enables)

```python
# Source: REQUIREMENTS.md CLI-05 + ClaudeSession SKILL.md usage pattern
import sys
sys.path.insert(0, '/a0')
from python.helpers.opencode_cli import OpenCodeSession

session = OpenCodeSession()
session.start()

r1 = session.send("Explain what /a0/python/tools/tmux_tool.py does in one paragraph.")
r2 = session.send("How many actions does TmuxTool implement?")

session.exit()
```

### Validation test pattern for Plan 14-01

```python
# Source: claude_cli.py test pattern; adapted for opencode_cli.py validation
import sys
sys.path.insert(0, '/a0')
from python.helpers.opencode_cli import OpenCodeSession

session = OpenCodeSession(response_timeout=60)
session.start()
print("started:", session.running)

response = session.send("What is 2+2? Reply with just the number.")
print("response received, length:", len(response))
assert "4" in response, f"Expected '4' in response, got: {response[:200]}"

session.exit()
print("exited:", not session.running)
print("PASS")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Skill code calls tmux_tool actions directly with raw tmux parameters | `OpenCodeSession` wrapper hides all tmux plumbing | Phase 14 (this phase) | Skill code is simpler, cannot misuse exit sequence, cannot forget prompt_pattern |
| Direct `/exit` send for exit | 3-step Ctrl+P palette sequence | Phase 13 (13-02 deviation) | The only verified exit method for v1.2.14; wrapper encodes this so callers never need to know |
| Async TmuxTool._wait_ready with asyncio.sleep | Sync `_wait_ready` with time.sleep in opencode_cli.py | Phase 14 design decision | Helper modules are synchronous; skill code runs sync; keep asyncio in the Tool layer only |
| Polling with 10s minimum timeout | Per-operation timeouts (15s startup, 120s response, 15s exit) | Phase 13 empirical findings | Correct timeouts prevent false timeouts while still bounding hangs |

**Deprecated/outdated:**
- Direct `opencode run` subprocess approach: would hang on permission dialogs (issue #11891, OPEN). The tmux TUI approach avoids this entirely. `"permission": "allow"` in config is still set as a precaution.
- `TTYSession` for OpenCode: explicitly OUT OF SCOPE (REQUIREMENTS.md). Creates isolated PTY — not connected to user-visible tmux session.

---

## Open Questions

1. **Import path for `python.tools.tmux_tool` from helper modules**
   - What we know: `claude_cli.py` uses `from python.helpers.tool import Tool` which works. The project uses `sys.path.insert(0, '/a0')` in skill code. `python/tools/tmux_tool.py` defines `OPENCODE_PROMPT_PATTERN` at module level.
   - What's unclear: Whether `from python.tools.tmux_tool import OPENCODE_PROMPT_PATTERN` works when `opencode_cli.py` is imported in Agent Zero's runtime (which sets the Python path to `/a0`). If not, the constants may need to be re-declared in `opencode_cli.py`.
   - Recommendation: In Plan 14-01, verify the import with `python3 -c "import sys; sys.path.insert(0, '/a0'); from python.tools.tmux_tool import OPENCODE_PROMPT_PATTERN; print(OPENCODE_PROMPT_PATTERN)"`. If import fails, copy the constants into `opencode_cli.py` with a comment referencing the source.

2. **PATH for opencode binary in `start()` command**
   - What we know: The PATH is set in `/root/.bashrc` (`export PATH=/root/.opencode/bin:$PATH`). The shared tmux session sources `.bashrc` on interactive login. The `install_additional.sh` adds the PATH permanently.
   - What's unclear: Whether the shared tmux pane's environment already has `/root/.opencode/bin` on PATH when `start()` is called, or whether `start()` needs to include `export PATH=...` in the command string.
   - Recommendation: Be defensive — include `export PATH=/root/.opencode/bin:$PATH && opencode /a0` as the start command (as was done in Phase 13 validation). If PATH is already set, the export is a no-op. Document this in the class docstring.

3. **Response text extraction — full pane vs. differential**
   - What we know: `send()` returning the full ANSI-stripped pane content works and contains the response. The response is interspersed with TUI chrome (model name, hints bar, input widget borders). Callers must parse to find the actual assistant response.
   - What's unclear: Whether Phase 14 should do differential extraction (before-capture vs. after-capture to isolate just the new response text) or return full pane and document parsing for Phase 15.
   - Recommendation: Return full pane content for v1 (Phase 14 scope). Phase 15 SKILL.md can document how callers should interpret the content. Differential extraction is an enhancement — flag as future work in code comments.

4. **Session persistence for multi-turn (session ID passing)**
   - What we know: OpenCode TUI maintains session context automatically within the TUI process. The `send()` / `send()` / `send()` pattern is multi-turn by definition — the TUI process stays running. Session ID is shown at exit (`opencode -s ses_[SESSION_ID]`) for resumption.
   - What's unclear: Whether `OpenCodeSession` needs to capture and expose the session ID from the exit output (for resumption use case). `ClaudeSession` has `session_id` property.
   - Recommendation: v1 does NOT need a `session_id` property — OpenCodeSession.exit() captures pane content after exit but doesn't need to parse the session ID. Add a TODO comment for future enhancement if the SKILL.md reveals a resume use case.

---

## Sources

### Primary (HIGH confidence)

- `/Users/rgv250cc/Documents/Projects/agent-zero/python/helpers/claude_cli.py` — `ClaudeSession` class (lines 219–324): direct pattern to mirror for `OpenCodeSession`. Interface: `__init__`, `turn()`, `reset()`, `session_id` property. Implementation: stateful wrapper over `claude_turn()`.
- `/Users/rgv250cc/Documents/Projects/agent-zero/python/tools/tmux_tool.py` — `OPENCODE_PROMPT_PATTERN` (line 18), `OPENCODE_START_TIMEOUT` (line 21), `ANSI_RE` (line 11), `_wait_ready()` (lines 131–202), `_send()` (lines 54–78), `_read()` (lines 108–129): all primitives to use in `OpenCodeSession`.
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/phases/13-interactive-cli-session-lifecycle/13-01-OBSERVATION.md` — Full lifecycle empirical findings: startup times, ready states, busy state, exit sequence, prompt patterns with verification.
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/phases/13-interactive-cli-session-lifecycle/13-02-SUMMARY.md` — Decisions Made section: CLI-04 exit via Ctrl+P (not `/exit`); confirmed deviation that MUST be encoded in `OpenCodeSession.exit()`.
- `/Users/rgv250cc/Documents/Projects/agent-zero/prompts/agent.system.tool.tmux.md` — "OpenCode Lifecycle Pattern" section: verified tmux_tool call sequences for CLI-01..04 with exact argument values.
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/REQUIREMENTS.md` — CLI-05 definition; explicit exclusions (pexpect, libtmux, TTYSession, sentinel injection, TmuxTool class direct calls).
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/ROADMAP.md` — Phase 14 success criteria defining the exact interface (`.start()` / `.send(prompt)` / `.exit()`); hang regression handling requirement.
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/STATE.md` — Accumulated decisions: ANSI_RE ordering fix; no sentinel injection; CLI-04 exit via Ctrl+P palette.

### Secondary (MEDIUM confidence)

- `/Users/rgv250cc/Documents/Projects/agent-zero/usr/skills/claude-cli/SKILL.md` — Usage examples, decision guide, anti-patterns for `ClaudeSession`: reference for what the Phase 14 equivalent should look like from a skill author's perspective.

### Tertiary (LOW confidence)

- None required — all critical facts come from Phase 13 primary sources (HIGH confidence).

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components are project-internal; no external library unknowns
- Architecture (class design): HIGH — direct model exists in `ClaudeSession`; interface spec defined in ROADMAP; all implementation building blocks verified
- Exit sequence: HIGH — empirically verified in Phase 13; documented in two sources (OBSERVATION.md, SUMMARY.md)
- Import path question: MEDIUM — likely works based on project conventions, but should be verified in Plan 14-01 Task 1
- Response extraction: MEDIUM — full pane return is simple and sufficient for v1; differential extraction is a known enhancement path

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 — OpenCode v1.2.14 patterns stable; project code patterns stable. If OpenCode is updated in Docker, re-verify exit sequence (the Ctrl+P vs `/exit` distinction is version-specific to v1.2.14+).
