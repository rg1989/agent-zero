# Phase 15: CLI Orchestration Skill Documentation - Research

**Researched:** 2026-02-25
**Domain:** Skill document authoring — tmux_tool action reference + Read-Detect-Write-Verify cycle + OpenCode-specific patterns
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLI-06 | Agent Zero can follow documented orchestration patterns for any interactive CLI via `usr/skills/cli-orchestration/SKILL.md` | All content sourced from verified Phase 11–14 implementations and empirical Phase 13 observations. SKILL.md must cover: tmux_tool action reference, Read-Detect-Write-Verify cycle, execution context isolation warning, OpenCode-specific patterns including exit regression workaround. |
</phase_requirements>

---

## Summary

Phase 15 is a documentation-only phase. No code changes. The deliverable is `usr/skills/cli-orchestration/SKILL.md` — a skill document that captures every validated CLI orchestration pattern so any Agent Zero session can orchestrate interactive CLI tools correctly without re-discovering these patterns.

All source content already exists in the codebase. The research task is to extract the authoritative values, patterns, and warnings from phases 11–14 and organize them into the established skill format (modeled on `usr/skills/claude-cli/SKILL.md`). The skill must stand alone — an agent reading only the skill should be able to orchestrate any interactive CLI and specifically OpenCode without consulting implementation files.

The one open design question is whether to include OpenCodeSession (the high-level Python wrapper from Phase 14) alongside the low-level tmux_tool patterns. Both are in-scope given the CLI-06 requirement scope and the Phase 14 note that send() response extraction details are deferred to Phase 15 documentation.

**Primary recommendation:** Write `usr/skills/cli-orchestration/SKILL.md` following the `claude-cli/SKILL.md` format exactly: metadata block, overview, DEFAULT rule, stack table, pattern sections with copy-paste-ready code, decision guide, pitfalls table, and troubleshooting table.

---

## Standard Stack

### Core — What the skill documents

| Component | Version/Detail | Purpose |
|-----------|---------------|---------|
| `tmux_tool` | Agent Zero tool (python/tools/tmux_tool.py) | Primitive interface to shared tmux session — send, keys, read, wait_ready |
| `OpenCodeSession` | python/helpers/opencode_cli.py (Phase 14) | High-level wrapper exposing .start()/.send()/.exit() — hides tmux plumbing |
| OpenCode TUI | v1.2.14 at /root/.opencode/bin/opencode | Interactive CLI being orchestrated |
| tmux session | named "shared" | Shared terminal where interactive CLIs run |

### Execution Context Isolation — CRITICAL architectural fact

**`code_execution_tool` and the shared tmux session are separate, non-sharing execution contexts.**

- `code_execution_tool` (with `runtime="python"` or `runtime="bash"`) spawns isolated subshells/PTYs — not connected to the user-visible shared tmux session named "shared"
- Processes started in `code_execution_tool` are NOT visible in the shared terminal; processes running in the shared tmux session are NOT accessible to `code_execution_tool`
- This is why `TTYSession` (python/helpers/tty_session.py) is explicitly banned for shared terminal use (REQUIREMENTS.md Out of Scope): it creates an isolated PTY subprocess, not connected to the shared session
- Correct approach: `tmux_tool` sends commands TO the shared tmux session via subprocess calls to the tmux binary (which routes to the named session)

Source: REQUIREMENTS.md Out of Scope section; STATE.md v1.2 architecture decision ("TTYSession for shared terminal — Creates isolated PTY subprocess, not connected to user-visible tmux session").

### Supporting — Skill document format model

| File | Role |
|------|------|
| `usr/skills/claude-cli/SKILL.md` | Established format to follow — metadata, overview, DEFAULT rule, stack, patterns, decision guide, pitfalls, troubleshooting |
| `usr/skills/shared-browser/SKILL.md` | Second format reference — Observe-Act-Verify cycle documentation style |
| `prompts/agent.system.tool.tmux.md` | Existing tmux_tool prompt reference — already has CLI-01..04 OpenCode patterns; skill extends this |

---

## Architecture Patterns

### Skill Document Structure (follow claude-cli/SKILL.md exactly)

```
usr/skills/cli-orchestration/
└── SKILL.md
```

Required sections in order:
1. `## Metadata` — name, version, description, tags, author
2. `## Overview` — 1 paragraph, implementation module reference
3. `## DEFAULT CLI ORCHESTRATION RULE` — when to load the skill
4. `## Stack` — table of components
5. `## Execution Context Isolation` — CRITICAL warning (code_execution_tool != shared tmux)
6. `## tmux_tool Action Reference` — all four actions with invocation syntax
7. `## The Read-Detect-Write-Verify Cycle` — required interaction pattern
8. `## OpenCode-Specific Patterns` — startup, prompt patterns, exit, version workaround
9. `## Using OpenCodeSession (Recommended)` — high-level wrapper patterns
10. `## Decision Guide` — when to use tmux_tool vs OpenCodeSession vs other tools
11. `## Common Pitfalls` — table of pitfall + fix
12. `## Troubleshooting` — table of problem + fix

### Pattern 1: tmux_tool Action Reference

**What:** Complete invocation syntax for all four tmux_tool actions.

**`send` action — TERM-01:** Type literal text + Enter into pane
```json
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "ls -la"}}
```
- `text` is passed as a single literal string — tmux does NOT interpret words like "Tab" as key names
- "Enter" is added automatically by the action
- Use for: running commands, submitting prompts, typing file paths

**`keys` action — TERM-02/TERM-03:** Send tmux key names WITHOUT Enter
```json
{"tool_name": "tmux_tool", "tool_args": {"action": "keys", "keys": "C-c"}}
```
- `keys` is space-separated tmux key names, or a list: `["C-p", "Enter"]`
- Special key names: `C-c`, `C-d`, `C-p`, `Tab`, `BTab`, `Escape`, `Enter`, `Up`, `Down`, `Left`, `Right`, `BSpace`, `PPage`, `NPage`
- Use for: Ctrl+C to interrupt, Tab for completion, `y`/`n` for inline prompts, special sequences

**`read` action — TERM-04:** Capture current pane content
```json
{"tool_name": "tmux_tool", "tool_args": {"action": "read", "lines": 100}}
```
- `lines` (optional, default 100): scrollback lines to capture
- Returns ANSI-stripped plain text of pane content
- Use for: observing current terminal state before or after actions

**`wait_ready` action — TERM-05:** Poll pane until prompt pattern matches or timeout
```json
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 10, "prompt_pattern": "[$#>%]\\s*$"}}
```
- `timeout` (optional, default 10s): use 120 for AI CLI responses (OpenCode, claude)
- `prompt_pattern` (optional, default `"[$#>%]\\s*$"`): regex matched against last non-blank line
- Two detection strategies: (1) pattern match on last non-blank line (primary), (2) content stability (pane stopped changing, secondary)
- Returns current pane content when ready state detected
- Initial 0.3s delay before first capture prevents stale-prompt false positive

Source: python/tools/tmux_tool.py (verified implementation)

### Pattern 2: Read-Detect-Write-Verify Cycle

**What:** The required interaction pattern for all interactive CLI orchestration. Analogous to Observe-Act-Verify in the browser skill.

**Steps:**
1. **Read** — Capture current pane state before acting (`read` or `wait_ready`)
2. **Detect** — Confirm the CLI is at the expected ready state (prompt pattern matched)
3. **Write** — Send input (`send` for text+Enter, `keys` for special keys)
4. **Verify** — Wait for response completion (`wait_ready` with appropriate timeout and prompt_pattern), then `read` to confirm

**Why this order matters:**
- Skip "Read" → you may send input to the wrong state (CLI still processing previous input)
- Skip "Detect" → you may send input before the CLI is ready, causing lost input or double-submission
- Skip "Verify" → you may read partial output or proceed before response is complete

**Generic CLI session example:**
```json
// Step 1+2: Read — confirm CLI is at ready state before sending anything
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 10}}

// Step 3: Write — send prompt
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "your prompt here"}}

// Step 4: Verify — wait for response
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 120, "prompt_pattern": "[$#>%]\\s*$"}}

// Read — capture result
{"tool_name": "tmux_tool", "tool_args": {"action": "read", "lines": 300}}
```

Source: Extracted from tmux_tool.py _wait_ready() docstring and Phase 12 readiness-detection decisions.

### Pattern 3: OpenCode-Specific Patterns (from Phase 13 empirical findings)

**All values empirically verified: 2026-02-25, OpenCode v1.2.14, Docker aarch64.**

#### Confirmed Prompt Patterns

```
OPENCODE_PROMPT_PATTERN = ^(?:\s*/a0\s+\d+\.\d+\.\d+\s*$|(?!.*esc interrupt).*ctrl\+t variants\s+tab agents)
```

Two branches cover two distinct ready states:
- **Branch 1 (startup):** `\s*/a0\s+\d+\.\d+\.\d+\s*$` — matches the TUI status bar at bottom-right showing project path + version (e.g., `  /a0  ...  1.2.14`). This is the initial startup ready state.
- **Branch 2 (post-response):** `(?!.*esc interrupt).*ctrl\+t variants\s+tab agents` — matches the hints bar that appears after any LLM response, WITHOUT the `esc interrupt` busy-state indicator.

Busy state (`esc interrupt` present in last non-blank line): **neither branch matches** — this is the correct behavior; wait_ready keeps polling.

```python
import re
OPENCODE_PROMPT_PATTERN = r'^(?:\s*/a0\s+\d+\.\d+\.\d+\s*$|(?!.*esc interrupt).*ctrl\+t variants\s+tab agents)'

# Verification (all assertions confirmed in Phase 13):
ready_initial = '  /a0                                              1.2.14'
ready_post = '                          ctrl+t variants  tab agents  ctrl+p commands    • OpenCode 1.2.14'
busy = '   ⬝⬝⬝⬝⬝⬝■■  esc interrupt      ctrl+t variants  tab agents  ctrl+p commands    • OpenCode 1.2.14'

assert bool(re.search(OPENCODE_PROMPT_PATTERN, ready_initial))   # True
assert bool(re.search(OPENCODE_PROMPT_PATTERN, ready_post))      # True
assert not bool(re.search(OPENCODE_PROMPT_PATTERN, busy))        # True (blocked by negative lookahead)
```

Source: 13-01-OBSERVATION.md, python/tools/tmux_tool.py OPENCODE_PROMPT_PATTERN constant.

#### Startup Sequence

1. Start OpenCode: `send` action with `"export PATH=/root/.opencode/bin:$PATH && opencode /a0"`
   - PATH export is defensive (no-op if already set); ensures binary is found
2. Wait 0.5s before first wait_ready (TUI input widget activation time — Phase 13 pitfall 3)
3. `wait_ready` with `timeout: 15` and `OPENCODE_PROMPT_PATTERN`
4. Observed startup time: ~1.5s; 15s timeout = 10x safety buffer

```json
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "export PATH=/root/.opencode/bin:$PATH && opencode /a0"}}
// Wait 0.5s (sleep in Python skill code, or use OpenCodeSession.start() which handles this)
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 15, "prompt_pattern": "^(?:\\s*/a0\\s+\\d+\\.\\d+\\.\\d+\\s*$|(?!.*esc interrupt).*ctrl\\+t variants\\s+tab agents)"}}
```

#### Exit Command and Version Hang Regression Workaround

**CRITICAL (v1.2.14 behavior):** Do NOT use `{"action": "send", "text": "/exit"}` directly.

In OpenCode v1.2.14, the `/` character typed into the TUI input area immediately opens the **AGENT PICKER** (showing "build native", "plan native" agents — NOT the command autocomplete). The "exit" text then goes into the agent search box. TUI stays open, shell never returns.

Verified exit sequence (3 steps):
```json
// Step 1: Open commands palette (C-p = Ctrl+P)
{"tool_name": "tmux_tool", "tool_args": {"action": "keys", "keys": "C-p"}}

// Step 2: Wait 0.2s for palette to open, then filter + execute
// (In raw tmux_tool usage: send "exit" after a sleep; or use OpenCodeSession.exit())
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "exit"}}

// Step 3: Wait for shell prompt (default pattern — OpenCode pattern NOT needed)
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 15}}
```

The `exit` text in the palette search filters to "Exit the app" and Enter executes it. OpenCode exits in 1-2 seconds and prints: `Session [name]` / `Continue  opencode -s ses_[SESSION_ID]` before returning to shell.

Source: 13-02-SUMMARY.md "Deviations — Auto-fixed Issues", python/helpers/opencode_cli.py exit() docstring.

#### Timeout Values (empirically derived)

| Operation | Timeout | Basis |
|-----------|---------|-------|
| CLI-01 startup wait_ready | 15s | Observed startup ~1.5s; 10x buffer |
| CLI-02/03 response wait_ready | 120s | AI response budget for real models |
| CLI-04 exit wait_ready | 15s | Shell return observed in 1-2s; 10x buffer |

#### First-Ever-Start Behaviors (non-blocking, document for awareness)

- Database migration: on the FIRST ever start in a fresh container, OpenCode runs a one-time DB migration ("Performing one time database migration...") before TUI launches. Takes < 3s. Does NOT occur on subsequent starts.
- "Getting started" dialog: appears after the FIRST LLM response. Overlays the right panel but does NOT block input. Last non-blank line is unaffected. Ignore for automated use.

Source: 13-01-OBSERVATION.md "Startup Behaviors — Additional Findings"

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenCode session lifecycle | Custom tmux subprocess calls in skill code | `OpenCodeSession` from `python/helpers/opencode_cli.py` | Handles ANSI stripping, Ctrl+P exit sequence, wait_ready polling, timeouts, pre-start guard — all verified correct |
| ANSI stripping | Custom regex | `ANSI_RE = re.compile(r'\x1b(?:\][^\x07]*\x07|[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')` | OSC branch must precede 2-char branch — ordering matters (STATE.md Phase 11 decision); hand-rolling commonly gets this wrong |
| Prompt pattern for OpenCode | Custom heuristics | `OPENCODE_PROMPT_PATTERN` constant (see above) | Two-branch regex covers both startup and post-response states; busy-state differentiation via negative lookahead is non-obvious |
| Exit sequence for OpenCode | Direct `/exit` send | Ctrl+P palette sequence | `/exit` triggers agent picker in v1.2.14 — direct send causes silent failure |

**Key insight:** The Phase 13 empirical observation (13-01-OBSERVATION.md) and Phase 14 implementation (opencode_cli.py) encode months of testing. The SKILL.md must surface these findings so agents never re-discover them.

---

## Common Pitfalls

### Pitfall 1: Using code_execution_tool to interact with shared terminal
**What goes wrong:** Agent runs commands in `code_execution_tool` expecting them to appear in the shared terminal, or reads shared terminal state via `code_execution_tool`.
**Why it happens:** Both look like "running Python/bash". The isolation boundary is invisible.
**How to avoid:** State the boundary explicitly in skill: `code_execution_tool` spawns isolated contexts; `tmux_tool` routes to the named shared session. These are never the same.
**Warning signs:** Commands run but shared terminal is unchanged; pane reads return unexpected content.

### Pitfall 2: Missing the 0.5s sleep before first wait_ready after OpenCode start
**What goes wrong:** First `wait_ready` returns immediately (stale-prompt false positive) or first prompt is lost.
**Why it happens:** TUI input widget needs a brief moment to fully activate after process starts. 0.3s initial delay inside `_wait_ready` prevents stale-prompt false positive, but the 0.5s sleep in `start()` is an additional buffer for the TUI widget activation (different concern).
**How to avoid:** Use `OpenCodeSession.start()` which encodes both delays. For raw tmux_tool usage, add a 0.5s pause between the send that starts OpenCode and the first `wait_ready`.

### Pitfall 3: Using /exit instead of Ctrl+P palette to exit OpenCode
**What goes wrong:** TUI stays open; shell never returns; subsequent `wait_ready` with default shell pattern never matches.
**Why it happens:** The `/` character in OpenCode v1.2.14 opens the Agent Picker, not command autocomplete.
**How to avoid:** Always use the 3-step Ctrl+P sequence. Use `OpenCodeSession.exit()` which encodes this.
**Warning signs:** After "exit" attempt, `read` shows agent picker UI (build native, plan native) or TUI is still visible.

### Pitfall 4: Using default 10s timeout for AI CLI responses
**What goes wrong:** `wait_ready` times out before the model finishes responding; incomplete or no response captured.
**Why it happens:** Default `wait_ready` timeout is 10s — correct for shell commands, too short for AI model responses.
**How to avoid:** Always use `timeout: 120` (or higher) when waiting on OpenCode/claude AI responses.
**Warning signs:** `wait_ready` returns "timed out" message; pane shows in-progress generation.

### Pitfall 5: ANSI regex with incorrect branch order
**What goes wrong:** OSC title sequences (window title, cursor position) survive the strip and appear as garbage in parsed output.
**Why it happens:** The OSC branch `\][^\x07]*\x07` must come BEFORE the 2-char branch `[@-Z\\-_]` because `]` (0x5D) falls in the `\-_` range — without the OSC branch first, `\x1b]` gets matched by the 2-char branch, leaving the rest of the OSC sequence unstripped.
**How to avoid:** Use the established `ANSI_RE` constant exactly as defined in `tmux_tool.py` and `opencode_cli.py`. Never write a new ANSI regex.

### Pitfall 6: prompt_pattern matched against wrong line
**What goes wrong:** `wait_ready` falsely triggers on a sub-prompt like `Continue? [y/N]` when waiting for shell return.
**Why it happens:** Default pattern `[$#>%]\s*$` matches `%` which appears in some sub-prompts.
**How to avoid:** For interactive prompts requiring user confirmation, use `keys` action with `"y"` or `"n"` rather than sending text. For OpenCode, use `OPENCODE_PROMPT_PATTERN` which is specific enough to avoid false positives.

Source: prompts/agent.system.tool.tmux.md warnings; STATE.md Phase 12 decisions.

---

## Code Examples

### Complete OpenCode session via OpenCodeSession (recommended)

```python
import sys
sys.path.insert(0, '/a0')
from python.helpers.opencode_cli import OpenCodeSession

session = OpenCodeSession()
session.start()                                      # starts TUI, waits for ready state (~1.5s)
r1 = session.send("What does /a0/python/tools/tmux_tool.py do?")
r2 = session.send("How many actions does TmuxTool implement?")
session.exit()                                        # Ctrl+P palette exit, waits for shell prompt

# r1 and r2 contain ANSI-stripped full pane content (300 lines)
# TUI chrome is included; response text is visible within the content
```

Source: python/helpers/opencode_cli.py module docstring; 14-01-SUMMARY.md validation results.

### Complete OpenCode session via raw tmux_tool (for reference / non-Python skill contexts)

```json
// CLI-01: Start OpenCode
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "export PATH=/root/.opencode/bin:$PATH && opencode /a0"}}
// (0.5s pause in surrounding code before wait_ready)
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 15, "prompt_pattern": "^(?:\\s*/a0\\s+\\d+\\.\\d+\\.\\d+\\s*$|(?!.*esc interrupt).*ctrl\\+t variants\\s+tab agents)"}}

// CLI-02+03: Send prompt and wait for response
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "What is 2+2? Reply with just the number."}}
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 120, "prompt_pattern": "^(?:\\s*/a0\\s+\\d+\\.\\d+\\.\\d+\\s*$|(?!.*esc interrupt).*ctrl\\+t variants\\s+tab agents)"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "read", "lines": 300}}

// CLI-04: Exit cleanly
{"tool_name": "tmux_tool", "tool_args": {"action": "keys", "keys": "C-p"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "exit"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 15}}
```

Source: prompts/agent.system.tool.tmux.md "OpenCode Lifecycle Pattern" section; 13-02-SUMMARY.md.

### ANSI stripping (for inline skill code that processes pane output)

```python
import re
# CRITICAL: OSC branch (\][^\x07]*\x07) MUST come before 2-char branch ([@-Z\\-_])
# because ] (0x5D) falls in the \-_ range — ordering matters
ANSI_RE = re.compile(r'\x1b(?:\][^\x07]*\x07|[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
clean = ANSI_RE.sub('', raw_pane_content).rstrip()
```

Source: python/tools/tmux_tool.py; STATE.md Phase 11 decision; python/helpers/opencode_cli.py.

### Generic interactive CLI session (not OpenCode — pattern applies to any REPL/interactive tool)

```json
// 1. Open shared-terminal app first
{"tool_name": "open_app", "tool_args": {"action": "open", "app": "shared-terminal"}}

// 2. Read — confirm shell is at ready state
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 10}}

// 3. Start the interactive CLI
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "python3 -i"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 10, "prompt_pattern": ">>> $"}}

// 4. Send prompt + wait
{"tool_name": "tmux_tool", "tool_args": {"action": "send", "text": "print('hello')"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 10, "prompt_pattern": ">>> $"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "read"}}

// 5. Exit
{"tool_name": "tmux_tool", "tool_args": {"action": "keys", "keys": "C-d"}}
{"tool_name": "tmux_tool", "tool_args": {"action": "wait_ready", "timeout": 10}}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `sleep N` after starting CLI before sending input | `wait_ready` with prompt_pattern (Phase 12) | 2026-02-25 | Eliminates timing guesses; pattern match gives reliable ready detection |
| Direct `/exit` send for OpenCode | Ctrl+P palette sequence | Phase 13 (2026-02-25) | `/exit` triggers agent picker in v1.2.14; Ctrl+P is the only reliable exit |
| `TTYSession` for interactive CLIs | `tmux_tool` actions | Phase 11 (2026-02-25) | TTYSession creates isolated PTY, not connected to shared session |
| Importing constants from tmux_tool | Copying with source comment | Phase 14 (2026-02-25) | Direct import fails (agent.py → nest_asyncio not in standalone Python context) |

**Deprecated/outdated (do not document in skill as current patterns):**
- `TTYSession` for shared terminal orchestration — creates isolated PTY subprocess
- `pexpect` — duplicates TTYSession approach; not installed
- `libtmux` — blocking-only API; just wraps subprocess calls; not installed
- Direct `/exit` send to OpenCode — v1.2.14 regression; Ctrl+P is correct

---

## Open Questions

1. **Differential response extraction from send()**
   - What we know: `OpenCodeSession.send()` returns full 300-line ANSI-stripped pane content including TUI chrome. The assistant response is visible but not isolated. Phase 14 summary explicitly notes: "differential extraction (before/after capture diff) deferred to Phase 15 SKILL.md as a known enhancement"
   - What's unclear: Whether the skill should document a before/after diff pattern for extracting just the response text, or simply document that callers receive full pane content and must locate the response visually/programmatically
   - Recommendation: Document the current behavior (full pane content returned) and note the workaround (capture pane content before send, capture after wait_ready, diff to isolate new content). Mark as "enhancement" rather than blocking. The Phase 14 scope decision was explicit that response isolation is NOT required for v1.

2. **Session resumption pattern for OpenCode**
   - What we know: OpenCode prints `Continue  opencode -s ses_[SESSION_ID]` at exit. This session ID can be used with `opencode -s ses_[ID]` to resume a previous conversation.
   - What's unclear: Whether the skill should document session ID capture and resumption as a documented pattern, or defer to future phases (CLI-EXT-02 scope)
   - Recommendation: Include a brief note about session resumption in the "Notes" section of the OpenCode lifecycle — it's a useful capability surfaced in Phase 13 observations. Mark as informational, not a primary pattern.

---

## Sources

### Primary (HIGH confidence)
- `python/tools/tmux_tool.py` — TmuxTool implementation; ANSI_RE, OPENCODE_PROMPT_PATTERN, OPENCODE_START_TIMEOUT constants; action invocation syntax; _wait_ready algorithm
- `python/helpers/opencode_cli.py` — OpenCodeSession implementation; all lifecycle patterns; Ctrl+P exit sequence; timeout values; import fallback rationale
- `.planning/phases/13-interactive-cli-session-lifecycle/13-01-OBSERVATION.md` — Empirical OpenCode v1.2.14 behavior: startup timing, ready state captures, busy state, exit sequence observation
- `.planning/phases/13-interactive-cli-session-lifecycle/13-02-SUMMARY.md` — CLI-04 exit regression discovery (/ triggers agent picker); Ctrl+P palette exit confirmation
- `.planning/phases/14-opencode-session-wrapper/14-VERIFICATION.md` — Phase 14 verification; multi-turn validated; send() return format confirmed
- `prompts/agent.system.tool.tmux.md` — Existing OpenCode lifecycle patterns for agent self-use; established invocation JSON format
- `usr/skills/claude-cli/SKILL.md` — Format model: metadata block, DEFAULT rule, stack table, patterns, decision guide, pitfalls, troubleshooting
- `.planning/REQUIREMENTS.md` — CLI-06 requirement definition; Out of Scope table (TTYSession, libtmux, pexpect, Playwright)
- `.planning/STATE.md` — Accumulated decisions from phases 11–14; ANSI_RE branch ordering decision; wait_ready timing decisions

### Secondary (MEDIUM confidence)
- `usr/skills/shared-browser/SKILL.md` — Additional format reference for Observe-Act-Verify pattern documentation style

### Tertiary (LOW confidence)
- None — all content sourced directly from project implementation files and verified empirical observations.

---

## Metadata

**Confidence breakdown:**
- tmux_tool action reference: HIGH — sourced from verified implementation in python/tools/tmux_tool.py
- Read-Detect-Write-Verify cycle: HIGH — derived from tmux_tool.py algorithm and Phase 12 design decisions in STATE.md
- Execution context isolation warning: HIGH — documented in REQUIREMENTS.md Out of Scope; confirmed by TTYSession exclusion rationale
- OpenCode prompt patterns: HIGH — empirically verified in Phase 13 (13-01-OBSERVATION.md) with assertion tests; constants in tmux_tool.py and opencode_cli.py
- OpenCode exit regression workaround: HIGH — discovered empirically in Phase 13-02 and encoded in opencode_cli.py exit() with explicit docstring warning
- ANSI_RE branch ordering: HIGH — STATE.md Phase 11 explicit decision with explanation
- Skill format: HIGH — modeled on existing claude-cli/SKILL.md

**Research date:** 2026-02-25
**Valid until:** Stable — document authoring task; patterns already validated. Content validity tied to OpenCode TUI behavior which could change with future OpenCode versions (currently v1.2.14).
