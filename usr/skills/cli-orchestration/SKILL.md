# CLI Orchestration Skill

## Metadata
- name: cli-orchestration
- version: 1.0
- description: Orchestrate interactive CLI tools (OpenCode, REPLs, any interactive process) via the shared tmux session using tmux_tool actions
- tags: [tmux, cli, opencode, interactive, terminal, orchestration]
- author: agent-zero

## Overview

`python/tools/tmux_tool.py` provides the primitive interface to the shared tmux session — four actions (send, keys, read, wait_ready) that route commands to the named "shared" session via subprocess calls to the tmux binary. `python/helpers/opencode_cli.py` provides the high-level `OpenCodeSession` wrapper that hides all tmux plumbing behind a clean `.start()` / `.send()` / `.exit()` lifecycle API. This skill documents both layers — the primitive tmux_tool actions for general interactive CLI orchestration, and the OpenCodeSession wrapper for OpenCode-specific use — along with all empirically verified patterns, timing values, and regression workarounds from Phases 11–14.

## DEFAULT CLI ORCHESTRATION RULE

**Load this skill when any task requires starting an interactive CLI (OpenCode, a REPL, any process that needs input/output after launch) in the shared terminal, OR any task that uses tmux_tool directly.**

---

## Stack

| Component | Location | Role |
|-----------|----------|------|
| tmux_tool | python/tools/tmux_tool.py | Primitive interface: send, keys, read, wait_ready |
| OpenCodeSession | python/helpers/opencode_cli.py | High-level wrapper: .start()/.send()/.exit() — hides tmux plumbing |
| OpenCode TUI | v1.2.14 at /root/.opencode/bin/opencode | Interactive CLI being orchestrated |
| tmux session | named "shared" | Shared terminal visible to user at /shared-terminal/ |

---

## CRITICAL: Execution Context Isolation

```
ISOLATION BOUNDARY — READ BEFORE ANY CLI ORCHESTRATION:

code_execution_tool (runtime="python" or runtime="bash") spawns ISOLATED subshells/PTYs.
These are NOT connected to the shared tmux session named "shared".

  - Processes started in code_execution_tool are NOT visible in the shared terminal.
  - Processes running in the shared tmux session are NOT accessible to code_execution_tool.
  - TTYSession (python/helpers/tty_session.py) is BANNED for shared terminal use:
    it creates an isolated PTY subprocess, not connected to the shared session.

CORRECT approach: use tmux_tool — it sends commands to the tmux binary which routes
to the named "shared" session. The shared terminal and code_execution_tool NEVER share state.

Warning signs that you violated this:
  - Commands run in code_execution_tool but shared terminal is unchanged.
  - pane reads return unexpected or empty content.
  - OpenCodeSession raises errors but no TUI is visible in shared-terminal/.
```

---

## tmux_tool Action Reference

All actions use tool invocation syntax. Source: python/tools/tmux_tool.py

### `send` — TERM-01: Type literal text + Enter

```json
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "ls -la"}}
```

- `text` is passed as a single literal string — tmux does NOT interpret words like "Tab" as key names
- "Enter" is added automatically by the action (separate final argument to tmux send-keys)
- Use for: running commands, submitting prompts, typing file paths, any input that ends with Enter

### `keys` — TERM-02/TERM-03: Send tmux key names without Enter

```json
{"tool_name": "tmux_tool", "tool_args": {"action": "keys", "keys": "C-c"}}
```

- `keys` is space-separated tmux key names, OR a list: `["C-p", "Enter"]`
- Key name reference:

| Key | tmux name | Use for |
|-----|-----------|---------|
| Ctrl+C | `C-c` | Interrupt running process |
| Ctrl+D | `C-d` | EOF / exit interactive REPL |
| Ctrl+P | `C-p` | OpenCode commands palette |
| Tab | `Tab` | Completion |
| Shift+Tab | `BTab` | Reverse tab |
| Escape | `Escape` | Cancel / close overlay |
| Enter | `Enter` | Confirm (when used with keys) |
| Arrow keys | `Up`, `Down`, `Left`, `Right` | Navigation |
| Backspace | `BSpace` | Delete character |
| Page Up/Down | `PPage`, `NPage` | Scroll |

- Use for: Ctrl+C to interrupt, Tab completion, y/n inline prompts, special sequences like Ctrl+P

### `read` — TERM-04: Capture current pane content

```json
{"tool_name": "tmux_tool", "tool_args": {"action": "read", "lines": 100}}
```

- `lines` (optional, default 100): scrollback lines to capture
- Returns ANSI-stripped plain text of pane content
- Use for: observing terminal state before or after actions; verifying what is on screen

### `wait_ready` — TERM-05: Poll pane until prompt detected or timeout

```json
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 10, "prompt_pattern": "[$#>%]\\s*$"}}
```

- `timeout` (optional, default 10s): use **120** for AI CLI responses (OpenCode, claude) — default 10s is for shell commands only
- `prompt_pattern` (optional, default `"[$#>%]\\s*$"`): regex matched against last non-blank ANSI-stripped line
- Two detection strategies:
  1. **Prompt pattern match** on last non-blank line — primary signal
  2. **Content stability** — consecutive captures are identical, pane stopped changing — secondary signal
- Initial 0.3s delay before first capture prevents stale-prompt false positive at send/wait boundary
- Returns current pane content when ready state detected
- Timeout fallback: returns with "timed out" message, never hangs indefinitely

---

## The Read-Detect-Write-Verify Cycle

**This is the required interaction pattern for ALL interactive CLI orchestration.** Analogous to the Observe-Act-Verify cycle in the browser skill.

### Steps

1. **Read** — Capture current pane state before acting (`wait_ready` or `read`)
2. **Detect** — Confirm the CLI is at the expected ready state (prompt pattern matched)
3. **Write** — Send input (`send` for text+Enter, `keys` for special keys)
4. **Verify** — Wait for response completion (`wait_ready` with appropriate timeout and prompt_pattern), then `read` to confirm

### Why ordering matters

- **Skip "Read"** → you may send input to the wrong state (CLI still processing previous input)
- **Skip "Detect"** → you may send input before the CLI is ready, causing lost input or double-submission
- **Skip "Verify"** → you may read partial output or proceed before response is complete

### Generic CLI Session Example (python3 -i REPL)

```json
// 1. Confirm shell is at ready state
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 10}}

// 2. Start interactive CLI
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "python3 -i"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 10, "prompt_pattern": ">>> $"}}

// 3. Send prompt — Read-Detect done by wait_ready above; Write:
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "print('hello')"}}

// 4. Verify — wait for response, then read
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 10, "prompt_pattern": ">>> $"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "read", "lines": 50}}

// 5. Exit REPL
{"tool_name": "tmux_tool", "tool_args": {"action": "keys", "keys": "C-d"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 10}}
```

---

## OpenCode-Specific Patterns

**All values empirically verified: 2026-02-25, OpenCode v1.2.14, Docker aarch64.**

### OPENCODE_PROMPT_PATTERN

```python
OPENCODE_PROMPT_PATTERN = r'^(?:\s*/a0\s+\d+\.\d+\.\d+\s*$|(?!.*esc interrupt).*ctrl\+t variants\s+tab agents)'
```

Two branches cover two distinct ready states:

**Branch 1 — Startup:** `\s*/a0\s+\d+\.\d+\.\d+\s*$`
Matches the TUI status bar at bottom-right showing project path + version (e.g., `  /a0  ...  1.2.14`).
This is the initial startup ready state.

**Branch 2 — Post-response:** `(?!.*esc interrupt).*ctrl\+t variants\s+tab agents`
Matches the hints bar that appears after any LLM response, WITHOUT the `esc interrupt` busy-state indicator.

**Busy state:** When `esc interrupt` appears in the last non-blank line, NEITHER branch matches. This is correct behavior — `wait_ready` keeps polling until the response completes.

Verification:
```python
import re
OPENCODE_PROMPT_PATTERN = r'^(?:\s*/a0\s+\d+\.\d+\.\d+\s*$|(?!.*esc interrupt).*ctrl\+t variants\s+tab agents)'

ready_initial = '  /a0                                              1.2.14'
ready_post = '                          ctrl+t variants  tab agents  ctrl+p commands    • OpenCode 1.2.14'
busy = '   ⬝⬝⬝⬝⬝⬝■■  esc interrupt      ctrl+t variants  tab agents  ctrl+p commands    • OpenCode 1.2.14'

assert bool(re.search(OPENCODE_PROMPT_PATTERN, ready_initial))   # True
assert bool(re.search(OPENCODE_PROMPT_PATTERN, ready_post))      # True
assert not bool(re.search(OPENCODE_PROMPT_PATTERN, busy))        # True — blocked by negative lookahead
```

### Startup Sequence

```json
// Step 1: Start OpenCode (PATH export is defensive — no-op if already set)
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "export PATH=/root/.opencode/bin:$PATH && opencode /a0"}}

// Step 2: Wait 0.5s in surrounding code before wait_ready
// (TUI input widget activation time — Phase 13 pitfall 3)
// In Python skill code: time.sleep(0.5)
// Or use OpenCodeSession.start() which encodes this delay automatically.

// Step 3: Wait for ready state
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 15, "prompt_pattern": "^(?:\\s*/a0\\s+\\d+\\.\\d+\\.\\d+\\s*$|(?!.*esc interrupt).*ctrl\\+t variants\\s+tab agents)"}}
```

### Timeout Values

| Operation | Timeout | Basis |
|-----------|---------|-------|
| CLI-01 startup wait_ready | 15s | Observed startup ~1.5s; 10x buffer |
| CLI-02/03 response wait_ready | 120s | AI response budget for real models |
| CLI-04 exit wait_ready | 15s | Shell return observed in 1-2s; 10x buffer |

### CRITICAL: Exit Sequence — Do NOT use /exit

```
CRITICAL: Do NOT use {"action": "send", "text": "/exit"}.

In OpenCode v1.2.14, the "/" character typed into the TUI input area immediately opens
the AGENT PICKER (showing "build native", "plan native" agents).
"exit" then goes into the agent search box — TUI stays open, shell never returns.

Verified exit sequence: Ctrl+P palette (3 steps).
```

Verified 3-step exit sequence:

```json
// Step 1: Open commands palette (Ctrl+P)
{"tool_name": "tmux_tool", "tool_args": {"action": "keys", "keys": "C-p"}}

// Step 2: Wait 0.2s for palette to open (time.sleep(0.2) in Python code), then filter + execute
// "exit" filters the palette to "Exit the app" and Enter executes it
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "exit"}}

// Step 3: Wait for shell prompt to confirm TUI exited
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 15}}
```

OpenCode exits in 1-2 seconds and shell prompt returns.

### First-Ever-Start Behaviors (non-blocking, awareness only)

- **DB migration:** On the FIRST ever start in a fresh container, OpenCode runs a one-time DB migration ("Performing one time database migration...") before TUI launches. Takes < 3s. Does NOT recur on subsequent starts. The 15s startup timeout handles this.
- **"Getting started" dialog:** Appears after the FIRST LLM response. Overlays the right panel but does NOT block input. Last non-blank line is unaffected. Ignore for automated use.

### Session Resumption (informational)

At exit, OpenCode prints: `Continue  opencode -s ses_[SESSION_ID]`

To resume a previous conversation: use `send` action with `"opencode -s ses_[SESSION_ID] /a0"`.

### Complete Raw tmux_tool Example

```json
// CLI-01: Start OpenCode
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "export PATH=/root/.opencode/bin:$PATH && opencode /a0"}}
// (0.5s pause in surrounding Python code before wait_ready)
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 15, "prompt_pattern": "^(?:\\s*/a0\\s+\\d+\\.\\d+\\.\\d+\\s*$|(?!.*esc interrupt).*ctrl\\+t variants\\s+tab agents)"}}

// CLI-02+03: Send prompt and wait for response
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "What is 2+2? Reply with just the number."}}
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 120, "prompt_pattern": "^(?:\\s*/a0\\s+\\d+\\.\\d+\\.\\d+\\s*$|(?!.*esc interrupt).*ctrl\\+t variants\\s+tab agents)"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "read", "lines": 300}}

// CLI-04: Exit cleanly via Ctrl+P palette
{"tool_name": "tmux_tool", "tool_args": {"action": "keys", "keys": "C-p"}}
// (0.2s pause before sending "exit")
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "exit"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 15}}
```

---

## Using OpenCodeSession (Recommended)

**This is the recommended approach for OpenCode orchestration.** `OpenCodeSession` hides all tmux plumbing, encodes all empirically verified patterns (ANSI stripping, Ctrl+P exit sequence, wait_ready polling, timeouts, pre-start guard).

### Import

```python
import sys
sys.path.insert(0, '/a0')
from python.helpers.opencode_cli import OpenCodeSession
```

### Lifecycle

```python
session = OpenCodeSession()
session.start()                                      # starts TUI, waits for ready state (~1.5s)
r1 = session.send("What does /a0/python/tools/tmux_tool.py do?")
r2 = session.send("How many actions does TmuxTool implement?")
session.exit()                                        # Ctrl+P palette exit, waits for shell prompt
```

### Method Reference

**`OpenCodeSession(response_timeout=120)`**
Instantiate the session wrapper. `response_timeout` is the max seconds to wait for an OpenCode AI response. Default 120s. Adjust upward for slow models or large file analysis tasks.

**`start() -> None`**
Sends `export PATH=/root/.opencode/bin:$PATH && opencode /a0` + Enter. Sleeps 0.5s (TUI input widget activation). Waits for `OPENCODE_PROMPT_PATTERN` to match.
Raises `RuntimeError` if OpenCode does not reach ready state within 15s.
Sets `session.running = True` on success.

**`send(prompt) -> str`**
Types `prompt` + Enter into the running TUI. Waits for `OPENCODE_PROMPT_PATTERN` to match (indicating response is complete). Returns full 300-line ANSI-stripped pane content. TUI chrome is included; the assistant response is visible within the returned content.
Raises `RuntimeError` if called before `start()`.
Raises `RuntimeError` if response not received within `response_timeout` seconds (sends C-c to interrupt before raising).
Multi-turn: OpenCode TUI process stays running between `send()` calls — conversation context is preserved automatically.

**`exit() -> None`**
Ctrl+P palette exit sequence: opens palette, types "exit" + Enter, waits for shell prompt. Idempotent — no-op if session is not running. Sets `session.running = False` on success.

**`session.running`**
Bool property. `True` after `start()`, `False` after `exit()` or before `start()`.

### Response Extraction Note

`send()` returns full pane content (300 lines) including TUI chrome. The assistant response is visible in the returned content alongside UI elements.

Enhancement (not required for v1): capture pane content before `send()`, capture after `wait_ready`, diff to isolate only the new response text.

---

## Decision Guide

| Need | Use |
|------|-----|
| Start OpenCode, send prompts, exit cleanly | `OpenCodeSession` (recommended) |
| Run a shell command in shared terminal | `tmux_tool` `send` action |
| Send Ctrl+C / interrupt a running process | `tmux_tool` `keys` action: `"C-c"` |
| Check current terminal state | `tmux_tool` `read` action |
| Wait for a non-OpenCode CLI to be ready | `tmux_tool` `wait_ready` with tool-specific `prompt_pattern` |
| Orchestrate any interactive REPL (python3 -i, node, etc.) | `tmux_tool` `send` + `wait_ready` with custom `prompt_pattern` |
| OpenCode multi-turn conversation | `OpenCodeSession` multi-turn (`TUI context persists between `send()` calls`) |
| Need isolated subprocess (not shared terminal) | `code_execution_tool` — but NOT for shared terminal interaction |

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Using `code_execution_tool` to interact with shared terminal | Use `tmux_tool` — `code_execution_tool` spawns isolated contexts; they never share state with the shared tmux session |
| Sending `/exit` to OpenCode | Use 3-step Ctrl+P palette sequence or `OpenCodeSession.exit()` — `/` opens agent picker in v1.2.14 |
| Using default 10s timeout for AI responses | Use `timeout: 120` for OpenCode/claude responses — default 10s is for shell commands only |
| Missing 0.5s sleep before first `wait_ready` after OpenCode start | Use `OpenCodeSession.start()` which encodes this delay; for raw `tmux_tool` usage, add `sleep(0.5)` before `wait_ready` |
| Writing a new ANSI regex instead of using `ANSI_RE` | Copy `ANSI_RE` exactly from `tmux_tool.py` — OSC branch (`\][^\x07]*\x07`) MUST come before 2-char branch (`[@-Z\\-_]`) because `]` (0x5D) falls in the `\-_` range |
| Default `prompt_pattern` `[$#>%]\s*$` false-positive on sub-prompts | For OpenCode, use `OPENCODE_PROMPT_PATTERN`; for other tools, write a specific enough pattern to exclude sub-prompts |
| `TTYSession` for shared terminal | `TTYSession` creates isolated PTY subprocess — NOT connected to shared session; use `tmux_tool` exclusively |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| After "exit" attempt, TUI still shows agent picker / build native / plan native | `/` triggered agent picker instead of command — press Escape, then use Ctrl+P palette sequence |
| `wait_ready` times out on AI response | Increase timeout to 120s+; verify Ollama is running at host:11434 and model is loaded |
| Pane read returns empty or unexpected content | Confirm tmux session "shared" exists: run `tmux ls` in `code_execution_tool` |
| Commands run in `code_execution_tool` but shared terminal unchanged | You are using wrong execution context — switch to `tmux_tool` for shared terminal interaction |
| `OpenCodeSession.start()` raises `RuntimeError` timeout | Check OpenCode binary exists at `/root/.opencode/bin/opencode`; check Ollama connectivity |
| `send()` returns TUI chrome with no recognizable response | Response was likely cut off by timeout — increase `response_timeout` in `OpenCodeSession` constructor |
| First start shows DB migration text before TUI | Normal first-ever-start behavior — `wait_ready` with 15s timeout handles this; does not recur |
