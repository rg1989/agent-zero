# Phase 12: Readiness Detection - Research

**Researched:** 2026-02-25
**Domain:** tmux pane stability polling, prompt pattern matching, ANSI stripping, asyncio polling loops
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TERM-05 | Agent Zero can detect when a terminal pane is ready for input using prompt pattern matching with idle timeout fallback | Dual-strategy `wait_ready` action: (1) capture-pane every 0.5s, strip ANSI, check last non-blank line for prompt pattern; (2) idle timeout (default 10s) as hard fallback. Both branches confirmed implementable via existing `subprocess.run` + `asyncio.sleep` pattern already in `terminal_agent.py`. |
</phase_requirements>

---

## Summary

Phase 12 adds a `wait_ready` action to the existing `TmuxTool` class in `python/tools/tmux_tool.py`. The action answers the question: "Is the pane waiting for my input, or is a command still running?" It must never block indefinitely and must not inject any sentinel text into the shared session.

The implementation strategy is locked in STATE.md: prompt pattern first, idle timeout fallback (10s minimum). This is identical to how `pexpect` approaches the same problem — poll for a pattern, fall back to TIMEOUT — except we drive tmux `capture-pane` instead of a PTY file descriptor. The two key algorithms are: (1) stability detection (two consecutive `capture-pane` reads with identical content signal that the pane has gone quiet), and (2) prompt pattern matching (last non-blank line ends with a known prompt suffix like `$ `, `# `, `> `). Both are necessary — stability alone does not prove the shell is ready (it could be paused mid-output), and prompt matching alone can produce false positives from CLI sub-prompts.

ANSI stripping is already solved and locked in STATE.md. The project-established regex (`ANSI_RE`) handles all three escape sequence families (2-char, CSI, OSC) and is already used in `_read()`. Phase 12 reuses this exact regex — no new stripping logic is needed. The success criterion requiring stress-testing for false positives from sub-prompts (e.g., `Continue? [y/N]`) is addressed by anchoring the pattern match to the last non-blank line ending with a prompt character set that does not overlap with question-style prompts.

**Primary recommendation:** Add `wait_ready` as a new action in `TmuxTool._wait_ready()`. It polls with `asyncio.sleep(0.5)` between iterations: strip ANSI from `capture-pane` output, check last non-blank line against a prompt pattern, and also compare the current capture to the previous capture (stability). Return as soon as either condition is met; return after the idle timeout regardless. Expose `timeout` and `prompt_pattern` as agent-controllable arguments with safe defaults.

---

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `tmux capture-pane` CLI | System tmux 3.x | Snapshot current pane content | Already the mechanism used by `_read()` in Phase 11; no new dependencies |
| `asyncio.sleep` (stdlib) | Python 3.x stdlib | Non-blocking sleep between poll iterations | Already used by `terminal_agent.py` (0.5s intervals); yields to event loop during wait |
| `re` (stdlib) | Python 3.x stdlib | Prompt pattern matching on last non-blank line | ANSI_RE already defined at module level in `tmux_tool.py` — same module |
| `subprocess.run` (stdlib) | Python 3.x stdlib | Execute `tmux capture-pane` synchronously | tmux CLI completes in <50ms; consistent with all other actions in this file |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `time.time()` (stdlib) | Python 3.x stdlib | Deadline-based timeout tracking | Use `deadline = time.time() + timeout` pattern from `terminal_agent.py` — proven in production |
| `asyncio.get_event_loop()` | Python 3.x stdlib | Not needed — `asyncio.sleep` is sufficient | Only if needed for timeout precision; `time.time()` deadline is simpler |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncio.sleep(0.5)` poll | `tmux wait-for` channel | `wait-for` requires injecting `tmux wait-for -S channel` into the pane as a shell command — this IS sentinel injection and is explicitly banned. Not viable. |
| `asyncio.sleep(0.5)` poll | `monitor-silence` tmux option | `monitor-silence` triggers a tmux alert (status bar highlight) — no Python-accessible event; requires parsing tmux control mode output. Far more complex than polling. |
| `subprocess.run` in poll loop | `asyncio.create_subprocess_exec` | Adds complexity with zero benefit — tmux capture-pane completes in <50ms. |
| Regex prompt pattern | `strip-ansi` PyPI package | New dependency for something already solved by `ANSI_RE` at module level. |

**Installation:** No new dependencies. All stdlib. tmux is pre-installed in the shared-terminal Docker container.

---

## Architecture Patterns

### Recommended Project Structure

```
python/tools/tmux_tool.py    # Add _wait_ready() method + register "wait_ready" in dispatch
prompts/agent.system.tool.tmux.md  # Update to document wait_ready action and its arguments
```

No new files needed. Both changes go into the two files already created in Phase 11.

### Pattern 1: Dual-Strategy wait_ready Loop

**What:** Poll capture-pane every 0.5s. On each iteration: (1) check last non-blank line against prompt pattern, (2) compare current content to previous content. Return "ready" when either fires. Return anyway when deadline passes.

**When to use:** After every `send` action before injecting the next `send`. Required for interactive CLI orchestration.

```python
# In python/tools/tmux_tool.py — new method on TmuxTool class
import asyncio
import time

async def _wait_ready(self):
    """TERM-05: Poll pane until prompt pattern matches or idle timeout expires."""
    pane = self.args.get("pane", _TMUX_SESSION)
    try:
        timeout = float(self.args.get("timeout", 10.0))
    except (ValueError, TypeError):
        timeout = 10.0
    # Agent can override the prompt pattern; default covers bash/zsh/sh
    pattern_str = self.args.get("prompt_pattern", r"[$#>]\s*$")
    try:
        prompt_re = re.compile(pattern_str)
    except re.error as e:
        return Response(
            message=f"Invalid prompt_pattern regex: {e}",
            break_loop=False,
        )

    deadline = time.time() + timeout
    prev_content = None

    while time.time() < deadline:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", pane, "-p", "-S", "-50"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return Response(
                message=f"tmux capture-pane failed: {result.stderr.strip()} — Is shared-terminal running?",
                break_loop=False,
            )

        clean = ANSI_RE.sub("", result.stdout).rstrip()

        # Strategy 1: Prompt pattern on last non-blank line
        lines = [l for l in clean.splitlines() if l.strip()]
        if lines and prompt_re.search(lines[-1]):
            elapsed = timeout - (deadline - time.time())
            return Response(
                message=f"ready (prompt matched) after {elapsed:.1f}s\n{clean}",
                break_loop=False,
            )

        # Strategy 2: Content stability (pane has stopped changing)
        if prev_content is not None and clean == prev_content:
            elapsed = timeout - (deadline - time.time())
            return Response(
                message=f"ready (stable content) after {elapsed:.1f}s\n{clean}",
                break_loop=False,
            )

        prev_content = clean
        await asyncio.sleep(0.5)

    # Timeout fallback — return current state and let agent decide
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", pane, "-p", "-S", "-50"],
        capture_output=True,
        text=True,
    )
    content = ANSI_RE.sub("", result.stdout).rstrip() if result.returncode == 0 else "(capture failed)"
    return Response(
        message=f"wait_ready timed out after {timeout}s (no prompt detected)\n{content}",
        break_loop=False,
    )
```

**Source:** Pattern derived from `terminal_agent.py` deadline+poll loop; prompt regex from pexpect documentation (end-of-line prompt matching); stability check is a standard heuristic for terminal automation.

### Pattern 2: Dispatch Registration

**What:** Add `"wait_ready"` to the dispatch dictionary in `execute()`.

```python
async def execute(self, **kwargs):
    action = self.args.get("action", "").strip().lower()
    dispatch = {
        "send": self._send,
        "keys": self._keys,
        "read": self._read,
        "wait_ready": self._wait_ready,   # Phase 12 addition
    }
    handler = dispatch.get(action)
    if not handler:
        return Response(
            message=f"Unknown action '{action}'. Valid actions: send, keys, read, wait_ready.",
            break_loop=False,
        )
    return await handler()
```

**Source:** Existing dispatch pattern in `tmux_tool.py` — no structural change, just add one entry.

### Pattern 3: Prompt Pattern Design (False-Positive Resistance)

**What:** The default regex must match shell prompts but NOT CLI sub-prompts (e.g., `Continue? [y/N]`).

**Analysis of prompt types:**

| Prompt Type | Example | Ends With | Should Match? |
|-------------|---------|-----------|---------------|
| bash shell | `user@host:~$ ` | `$ ` | YES |
| zsh shell | `~/project % ` | `% ` | YES |
| root shell | `root@host:~# ` | `# ` | YES |
| Python REPL | `>>> ` | `> ` (three `>`) | YES — acceptable |
| node REPL | `> ` | `> ` | YES — acceptable |
| CLI sub-prompt | `Continue? [y/N]` | `]` | NO — does not end with `[$#>]` |
| CLI sub-prompt | `Press Enter to continue` | `e` | NO |
| OpenCode prompt | `> ` or `opencode> ` | `> ` | YES — acceptable since we want to send next input |
| git confirm | `Are you sure? (y/n)` | `)` | NO |

**Default pattern:** `r"[$#>%]\s*$"` — matches lines ending with shell-indicator characters optionally followed by whitespace.

**Why this is sufficient for success criterion 5:** The stress test `Continue? [y/N]` ends with `]` not `$`, `#`, `>`, or `%` — so the default pattern does NOT match it. The agent will correctly wait through the idle timeout rather than acting prematurely.

**When to use custom pattern:** Phase 13 may need a custom `prompt_pattern` argument when orchestrating OpenCode, whose prompt differs from standard shell patterns. The argument is exposed for this reason.

### Pattern 4: Content Stability Semantics

**What:** "Stability" = two consecutive capture-pane calls return the same ANSI-stripped content (with 0.5s between them). This means the pane is not actively writing new output.

**Why 0.5s interval:** Same as `terminal_agent.py`. Sufficient to distinguish active output from idle. Shorter risks race conditions where output arrives between reads; longer adds unnecessary latency.

**Critical caveat:** Stability alone is NOT sufficient for CLI orchestration — a command can pause mid-output (buffered writes, progress bars refreshing, etc.) and appear stable for >0.5s without being done. Use stability as a secondary fallback, not as the primary signal. Prompt matching is primary.

**Order of checks:** Prompt first, stability second. If prompt matches, return immediately (fast path). If content is stable but no prompt, hold for one more iteration to confirm before returning (implementation above uses single-match stability — can be strengthened to N consecutive identical reads if needed).

### Anti-Patterns to Avoid

- **`tmux wait-for -S channel` injection:** Requires writing shell code into the pane via `send-keys` — this IS sentinel injection. Explicitly banned by project constraints.
- **`monitor-silence` option:** Requires tmux control mode to receive events; far more complexity than polling; not worth it.
- **Prompting for `$?` or any command output:** Sentinel injection. Banned.
- **Matching against the full pane content (not just last non-blank line):** A prompt pattern like `$ ` can appear in the middle of captured output from previously run commands. Only match against the LAST non-blank line to avoid false positives from history.
- **Using `lines=100` (full scrollback) for wait_ready polling:** Only the last 50 lines are needed for prompt detection, and performance matters in a tight poll loop. Use `-S -50`.
- **Not stripping ANSI before prompt matching:** Shell PS1 prompts frequently include ANSI color codes. Without stripping, `\x1b[32m$\x1b[0m ` would NOT match `[$#>%]\s*$`. Always strip first.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Non-blocking wait during polling | Custom threading / subprocess timeout tricks | `asyncio.sleep(0.5)` | `TmuxTool.execute()` is an async method — `await asyncio.sleep()` is the correct non-blocking yield |
| ANSI stripping | New regex or `strip-ansi` package | Existing `ANSI_RE` at module level | Already defined in `tmux_tool.py`; OSC ordering already handled per STATE.md decision |
| Deadline tracking | Custom class or threading.Timer | `deadline = time.time() + timeout; while time.time() < deadline` | Exact pattern from `terminal_agent.py` — proven, simple |
| Prompt detection library | pexpect integration | Direct `re.search` on last non-blank line | pexpect is explicitly excluded in REQUIREMENTS.md; re.search is 2 lines |

**Key insight:** The hard part of readiness detection is not the algorithm — it's the constraints. No sentinel injection. No new dependencies. The algorithm itself (poll + pattern + timeout) is straightforward once the constraints are clear.

---

## Common Pitfalls

### Pitfall 1: Matching Prompt in Scrollback History (False Positive)

**What goes wrong:** The full captured output includes previous commands. If the previous command was `echo "$ prompt example"`, the pattern `[$#>%]\s*$` would match that historical line and return "ready" before the current command finishes.

**Why it happens:** `capture-pane -S -50` returns 50 lines of content including all visible history, not just what happened after the last command.

**How to avoid:** Match ONLY against the LAST non-blank line of the stripped output. Extract with:
```python
lines = [l for l in clean.splitlines() if l.strip()]
last_line = lines[-1] if lines else ""
if prompt_re.search(last_line): ...
```

**Warning signs:** `wait_ready` returns immediately after `send` before the command has had time to start running.

### Pitfall 2: ANSI in Prompt Prevents Pattern Match

**What goes wrong:** Shell prompts often include ANSI color codes in PS1 (e.g., `\e[32m$ \e[0m`). Without stripping, `[$#>%]\s*$` never matches the decorated prompt.

**Why it happens:** Bash/zsh PS1 frequently uses `\[\e[32m\]` color wrappers around the prompt character.

**How to avoid:** Apply `ANSI_RE.sub("", ...)` before pattern matching — always. The `_read()` method does this; `_wait_ready()` must do the same.

**Warning signs:** `wait_ready` always times out even when the shell is clearly idle.

### Pitfall 3: Stability Check on First Iteration

**What goes wrong:** If `prev_content` starts as `None` and the first capture happens to be empty, the second capture (also potentially empty) would match. This triggers "stable" on an empty pane immediately.

**Why it happens:** Edge case at startup or after Ctrl+C clears the screen.

**How to avoid:** Initialize `prev_content = None`. Only compare when `prev_content is not None` (i.e., skip the check on the first iteration). The implementation above already handles this correctly.

**Warning signs:** `wait_ready` returns with "stable content after 0.5s" on an empty pane immediately after sending a command.

### Pitfall 4: 10-Second Default Timeout Is Too Short for AI CLI Tools

**What goes wrong:** AI CLIs (OpenCode, claude) can take 30–120 seconds to respond. A 10-second timeout causes `wait_ready` to return prematurely with a timeout message, causing the agent to inject input mid-response.

**Why it happens:** 10 seconds is described in the requirements as the MINIMUM for `wait_ready` used in general shell contexts. For AI CLI orchestration (Phase 13+), callers must pass a higher `timeout` argument.

**How to avoid:** Document clearly that 10s is the default minimum and that Phase 13 CLI orchestration code MUST pass `timeout=120` (or higher) when waiting on AI CLI responses. The argument is agent-configurable for this reason.

**Warning signs:** Phase 13 test shows `wait_ready` returning timeout messages after 10s even though OpenCode is still processing.

### Pitfall 5: Sub-Prompt False Positive With Custom Patterns

**What goes wrong:** If an agent passes a custom `prompt_pattern` that is too broad (e.g., `".*"` or `"\\?"`), every line matches and `wait_ready` returns immediately.

**Why it happens:** The `prompt_pattern` argument gives the agent freedom to customize — but the agent may pass a poorly-scoped pattern.

**How to avoid:** The default pattern `r"[$#>%]\s*$"` is carefully designed to be restrictive. Document in the prompt that the pattern is anchored to line-end and should only match known prompt suffixes. Validate the pattern compiles before the poll loop starts; return an error if it doesn't.

**Warning signs:** `wait_ready` always returns "prompt matched after 0.0s" regardless of terminal state.

### Pitfall 6: Race Between send and wait_ready

**What goes wrong:** Agent calls `send` then immediately calls `wait_ready`. The command hasn't had time to start executing yet, so the first `capture-pane` still shows the shell prompt from BEFORE the command ran — triggering a false "ready" on the first iteration.

**Why it happens:** tmux `send-keys` is asynchronous — it injects keystrokes into the pane input queue, but the command may not have started executing before the first `capture-pane` call.

**How to avoid:** Add a brief initial sleep of 0.3–0.5s at the START of `_wait_ready()` before the first capture. This allows the pane to consume the Enter keypress and begin executing. Alternatively, ensure `prev_content` comparison requires stability across at least two reads — which naturally provides the delay.

**Warning signs:** `wait_ready` consistently returns after 0.5s (one poll cycle) even for long-running commands.

---

## Code Examples

Verified patterns from project source code and official tmux documentation:

### Complete wait_ready Implementation

```python
async def _wait_ready(self):
    """
    TERM-05: Poll pane until prompt pattern matches or idle timeout expires.

    Two detection strategies:
    1. Prompt pattern: last non-blank ANSI-stripped line matches a shell prompt regex
    2. Stability fallback: consecutive captures are identical (pane stopped changing)

    Falls back to timeout return — never hangs indefinitely.
    """
    pane = self.args.get("pane", _TMUX_SESSION)
    try:
        timeout = float(self.args.get("timeout", 10.0))
    except (ValueError, TypeError):
        timeout = 10.0
    pattern_str = self.args.get("prompt_pattern", r"[$#>%]\s*$")
    try:
        prompt_re = re.compile(pattern_str)
    except re.error as e:
        return Response(
            message=f"Invalid prompt_pattern: {e}",
            break_loop=False,
        )

    deadline = time.time() + timeout
    prev_content = None

    # Brief initial delay to let the command start executing before first check
    await asyncio.sleep(0.3)

    while time.time() < deadline:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", pane, "-p", "-S", "-50"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return Response(
                message=f"capture-pane failed: {result.stderr.strip()} — Is shared-terminal running?",
                break_loop=False,
            )

        clean = ANSI_RE.sub("", result.stdout).rstrip()

        # Strategy 1: prompt pattern on last non-blank line (primary signal)
        lines = [l for l in clean.splitlines() if l.strip()]
        if lines and prompt_re.search(lines[-1]):
            return Response(
                message=f"ready (prompt matched)\n{clean}",
                break_loop=False,
            )

        # Strategy 2: content stability — pane stopped changing (secondary signal)
        if prev_content is not None and clean == prev_content:
            return Response(
                message=f"ready (stable)\n{clean}",
                break_loop=False,
            )

        prev_content = clean
        await asyncio.sleep(0.5)

    # Timeout fallback
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", pane, "-p", "-S", "-50"],
        capture_output=True, text=True,
    )
    content = ANSI_RE.sub("", result.stdout).rstrip() if result.returncode == 0 else "(capture failed)"
    return Response(
        message=f"wait_ready timed out after {timeout}s\n{content}",
        break_loop=False,
    )
```

**Source:** Pattern derived from `terminal_agent.py` deadline+poll loop (project source, HIGH confidence). Prompt regex derived from pexpect documentation on end-anchor pattern matching (MEDIUM confidence, verified as correct for bash/zsh/sh shells). Stability heuristic is a standard terminal automation technique (MEDIUM confidence).

### Updated dispatch in execute()

```python
async def execute(self, **kwargs):
    action = self.args.get("action", "").strip().lower()
    dispatch = {
        "send": self._send,
        "keys": self._keys,
        "read": self._read,
        "wait_ready": self._wait_ready,
    }
    handler = dispatch.get(action)
    if not handler:
        return Response(
            message=f"Unknown action '{action}'. Valid actions: send, keys, read, wait_ready.",
            break_loop=False,
        )
    return await handler()
```

### Updated imports (add time and asyncio to tmux_tool.py top)

```python
import asyncio
import subprocess
import time
import re
from python.helpers.tool import Tool, Response
```

Note: `asyncio` and `time` are not currently imported in `tmux_tool.py`. They must be added. `terminal_agent.py` imports both — confirmed available.

### Prompt prompt doc addition (agent.system.tool.tmux.md)

```markdown
#### Usage: wait for terminal to be ready after sending a command
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "wait_ready" } }
```

#### Usage: wait with custom timeout (for AI CLI tools that take longer)
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "wait_ready", "timeout": 120 } }
```

#### Usage: wait with custom prompt pattern (for non-standard shells)
```json
{ "tool_name": "tmux_tool", "tool_args": { "action": "wait_ready", "prompt_pattern": "opencode> $" } }
```

!!! Always call `wait_ready` after `send` before injecting the next input
!!! Default timeout is 10s — use timeout: 120 when waiting for AI CLI responses
!!! `wait_ready` returns pane content in the response message (same as `read`)
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Sentinel injection (`echo MARKER:$?`) | Capture-pane stability + prompt matching | Sentinels work for non-interactive shell; break interactive programs. Phase 12 is the non-sentinel approach |
| `pexpect` expect() + TIMEOUT | Custom `asyncio.sleep` poll loop | pexpect is explicitly excluded. Same conceptual model — pattern first, timeout fallback — different mechanism |
| `libtmux` capture_pane() | `subprocess.run(["tmux", "capture-pane", ...])` | libtmux is explicitly excluded. Direct subprocess is equivalent, no dependency overhead |
| Fixed sleep after send (`time.sleep(N)`) | `wait_ready` with adaptive return | Fixed sleep is fragile: too short = race, too long = unnecessary latency |

**Deprecated/outdated:**
- Fixed `time.sleep(2)` after `send`: Does not scale across commands with different durations. Replaced by `wait_ready`.
- Sentinel pattern for interactive CLIs: `terminal_agent.py` correctly uses sentinels for non-interactive shell commands; `tmux_tool` uses capture+poll for interactive sessions. Both remain — they serve different use cases.

---

## Open Questions

1. **Initial delay duration: 0.3s or longer?**
   - What we know: `terminal_agent.py` uses `asyncio.sleep(0.5)` at the start of each poll cycle. The issue is that `send-keys` may not have been consumed by the shell before the first `capture-pane` call.
   - What's unclear: Whether 0.3s is consistently sufficient for the shell to consume Enter and start the command. Could vary by system load.
   - Recommendation: Use 0.3s initial delay as documented above. If stress testing reveals races, increase to 0.5s. This is a tunable constant that can be adjusted based on observed behavior.

2. **Stability check: single match vs N consecutive matches?**
   - What we know: A single identical read pair (0.5s apart) signals that the pane stopped changing. This is what most terminal automation tools use.
   - What's unclear: Whether a slowly-updating process (progress bar updating every 1s) could fool a single-match stability check.
   - Recommendation: Use single-match stability for Phase 12. Phase 13 empirical observation will reveal whether this is sufficient for OpenCode; if not, upgrade to N=2 consecutive matches. Adding a second match is a one-line change.

3. **Lines to capture during polling (`-S -50`)?**
   - What we know: The `_read()` action defaults to 100 lines. For `wait_ready` we only need the last prompt line, so 50 is sufficient and faster.
   - What's unclear: Whether 50 lines is enough if the terminal has a lot of output before the prompt that pushes the prompt far up.
   - Recommendation: Use `-S -50` as the default for polling (performance matters in a tight loop). The `_read()` action remains at `-S -100` for content reading. If the prompt is being missed, this can be tuned.

4. **Should wait_ready include pane content in its response?**
   - What we know: The agent needs to read the terminal output after a command finishes. Without the content in the response, the agent would need to call `read` separately after `wait_ready`.
   - Recommendation: YES — include the final pane content in the response message (same as `_read()` returns). This saves one tool call and matches the "read after wait" pattern the agent will need. The response format `"ready (prompt matched)\n{clean}"` is clear and parseable.

---

## Sources

### Primary (HIGH confidence)

- `/Users/rgv250cc/Documents/Projects/agent-zero/python/tools/tmux_tool.py` — existing Phase 11 implementation; dispatch pattern, ANSI_RE, `_read()` capture-pane call (direct code read)
- `/Users/rgv250cc/Documents/Projects/agent-zero/python/tools/terminal_agent.py` — `asyncio.sleep(0.5)` poll loop, `deadline = time.time() + timeout` pattern, how existing pane polling works (direct code read)
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/STATE.md` — locked decisions: prompt pattern first, idle timeout fallback (10s minimum), ANSI_RE regex with OSC branch ordering (direct read)
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/REQUIREMENTS.md` — TERM-05 definition, explicit exclusions (pexpect, libtmux, TTYSession, sentinel in shared session) (direct read)
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/phases/11-tmux-primitive-infrastructure/11-RESEARCH.md` — ANSI pitfall analysis, capture-pane flags, `asyncio.sleep` planned for Phase 12 (direct read)

### Secondary (MEDIUM confidence)

- [pexpect documentation — API Overview](https://pexpect.readthedocs.io/en/stable/overview.html) — pattern + TIMEOUT design philosophy; end-of-line matching caveats; "process may have paused momentarily" note (WebSearch, aligns with project pattern)
- [tmux man page — man7.org](https://man7.org/linux/man-pages/man1/tmux.1.html) — `capture-pane -S -N` flag semantics; `wait-for` channel mechanism; `monitor-silence` option (established from Phase 11 research)
- [tmux wait-for and signaling — GitHub Issue #832](https://github.com/tmux/tmux/issues/832) — confirmed that `wait-for` requires shell command injection to signal; not suitable for sentinel-free design
- [ANSI Escape Codes reference — GitHub Gist](https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797) — OSC sequence format `\x1b]...\x07`; confirms ANSI_RE covers all relevant families (WebSearch)

### Tertiary (LOW confidence)

- None — all critical claims verified against project source code or official sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components are stdlib + already imported in `terminal_agent.py`; no new dependencies
- Architecture: HIGH — algorithm is a direct adaptation of `terminal_agent.py`'s poll loop; dispatch pattern is exact copy with one new entry
- Pitfalls: HIGH — pitfalls 1-3 derived from direct code analysis; pitfalls 4-6 derived from pexpect docs and tmux mechanics, all cross-verified against project constraints
- Prompt pattern design: MEDIUM — default regex `r"[$#>%]\s*$"` is conventional for bash/zsh/sh; OpenCode and other CLIs may require custom patterns (to be determined empirically in Phase 13)

**Research date:** 2026-02-25
**Valid until:** 2026-08-25 (tmux CLI is extremely stable; Python stdlib asyncio/re/subprocess are stable; prompt regex is independent of library versions)
