# Feature Research

**Domain:** tmux-based terminal interaction + interactive CLI orchestration (Agent Zero fork, v1.2)
**Researched:** 2026-02-25
**Confidence:** HIGH (findings derived from live code inspection — terminal_agent.py, code_execution_tool.py, tty_session.py, claude-cli SKILL.md — plus web research on OpenCode CLI behavior and tmux orchestration patterns)

---

## Context

This is the v1.2 Terminal Orchestration milestone. The goal is to give Agent Zero the ability to interact with the shared terminal and interactive CLIs as a human would — type, read screen, send special keys, detect readiness — enabling orchestration of any CLI agent (OpenCode first, generically second).

### What Already Exists (Do Not Re-Implement)

| Existing Capability | Where | Status |
|---------------------|-------|--------|
| Shared terminal (tmux `shared` session, ttyd) | `apps/shared-terminal/startup.sh` | Shipped v1.0 |
| `terminal_agent.py` — tmux send-keys + sentinel-based completion | `python/tools/terminal_agent.py` | Shipped v1.1 |
| `code_execution_tool.py` — PTY-based shell sessions, prompt detection, idle timeout | `python/tools/code_execution_tool.py` | Shipped v1.0 |
| `TTYSession` — PTY subprocess wrapper, send/read, idle-timeout collection | `python/helpers/tty_session.py` | Shipped v1.1 |
| `ClaudeSession` / `claude_turn()` — subprocess-based multi-turn with `--resume UUID` | `python/helpers/claude_cli.py` | Shipped v1.1 |
| claude-cli SKILL.md — all validated claude invocation patterns | `usr/skills/claude-cli/SKILL.md` | Shipped v1.1 |

### What the Existing `terminal_agent.py` Can and Cannot Do

The existing tool can:
- Run fire-and-forget shell commands in the shared tmux session with sentinel detection
- Return stdout after the command completes (exit code recovered from sentinel line)

The existing tool CANNOT:
- Send text without Enter (partial input to a waiting prompt)
- Send special keys (Ctrl+C, Ctrl+D, Tab, Escape, arrows)
- Interact with an interactive CLI already running in the pane (opencode TUI, python REPL, etc.)
- Capture current pane screen content for observation
- Detect when an interactive program is ready for input (vs. still processing)
- Support multi-turn send/observe cycles within a single session

These gaps are exactly what v1.2 must fill.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features required for the milestone goal to be met. Missing any of these means "Agent Zero can interact with the terminal as a human would" is false.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **TERM-01: Send text + Enter to named tmux pane** | The most fundamental action — type a command and submit it. Every terminal interaction starts here. | LOW | `tmux send-keys -t shared "text" Enter` — already used in `terminal_agent.py`. The new tmux_tool needs to expose this as a discrete action separate from fire-and-forget command execution. Key difference from existing tool: no sentinel appended, no completion-wait loop. |
| **TERM-02: Send text without Enter (partial input)** | Interactive CLIs show prompts mid-line (e.g., `Are you sure? [y/N]`) and expect a single character response without Enter. Also required for OpenCode: it shows an input field that accepts text before the user hits Enter. | LOW | `tmux send-keys -t shared "text"` (no `Enter` at end). Critical: `-l` flag may be needed to suppress tmux key-name interpretation (e.g., send literal `y` not key name `y`). Use `send-keys -l` for literal text, standard `send-keys` for key names. |
| **TERM-03: Send special keys to tmux pane** | Ctrl+C to interrupt a running process, Ctrl+D to send EOF, Tab for completion, Escape to cancel, arrow keys for navigation in interactive TUIs. These are the control signals that interactive programs depend on. | LOW | tmux key name syntax: `C-c` (Ctrl+C), `C-d` (Ctrl+D), `Escape`, `Tab`, `Up`, `Down`, `Left`, `Right`. `tmux send-keys -t shared C-c ""` — note: no `Enter` for control keys. The tmux_tool must expose a `key` parameter distinct from `text`. |
| **TERM-04: Capture current terminal screen content** | Agent must observe current state before acting — same principle as the browser skill's "screenshot before every action." Capture-pane gives the current screen buffer. Without this, Agent operates blind. | LOW | `tmux capture-pane -t shared -p -S -200` captures last 200 lines of scrollback. Already used in `terminal_agent.py`. The new tool exposes this as a standalone read action, not bundled with command execution. Key parameter: `-S -N` controls scrollback depth. |
| **TERM-05: Detect when terminal is ready for input** | Interactive CLIs have two states: processing (output flowing or spinner visible) and waiting (prompt displayed, expecting input). Sending input while processing corrupts the session. Agent must wait for the ready state. | HIGH | Dual strategy required: (1) prompt pattern matching on captured pane content (regex for `$ `, `# `, `> `, tool-specific prompts), (2) idle timeout fallback when no recognized prompt exists. `code_execution_tool.py` already implements this for its own PTY sessions — the same logic applies to tmux pane capture-pane polling. High complexity because interactive TUI prompts (OpenCode) are not simple regex matches — they contain ANSI color codes and may span multiple lines. |
| **CLI-01: Start an interactive CLI in shared terminal** | Before any interaction can occur, the CLI must be running in the pane. Agent must be able to launch opencode, python REPL, etc. in the shared session. | LOW | `terminal_agent.py` already does this for fire-and-forget commands. For interactive CLIs: `tmux send-keys -t shared "opencode" Enter` then wait for the initial prompt before proceeding. The launch step and the first prompt-wait are always coupled. |
| **CLI-02: Send prompts to running interactive CLI and read responses** | The core multi-turn interaction loop. Send text, wait for response to complete, read screen, repeat. This is what makes orchestration possible. | HIGH | Requires TERM-01 + TERM-04 + TERM-05 in sequence: send text + Enter → poll capture-pane until ready signal → read screen. The completion detection problem (TERM-05) is the hard part. Response may stream for seconds; premature capture returns partial output. Idle timeout is the fallback when no terminal prompt returns (e.g., opencode streaming response). |
| **CLI-03: Detect when CLI has finished responding** | Agent must not send the next prompt before the CLI is done with the current one. Over-eager input corrupts state. | HIGH | Strategy depends on CLI type. For opencode non-interactive (`opencode run`): process exit is the signal (no detection needed — subprocess.run blocks). For opencode TUI: screen-scrape for the input field re-appearing. For generic interactive CLIs: idle timeout after output stops flowing. This is the highest-complexity feature of the milestone. |
| **CLI-04: Interrupt or exit an interactive CLI session** | Ctrl+C to cancel a long-running response, `/quit` or `q` to exit gracefully, Ctrl+D for EOF-based exit. Failure to exit cleanly leaves orphan processes in the shared terminal pane. | LOW | Requires TERM-03 for Ctrl+C/Ctrl+D. For opencode: `/quit` command or `q` then Enter. For Python REPL: `exit()` or Ctrl+D. The skill must document per-CLI exit sequences. |
| **CLI-06: Generic CLI orchestration skill document** | Without a SKILL.md, Agent Zero will reinvent patterns incorrectly in each session. The skill is how validated patterns persist and become reusable. | LOW | Write `usr/skills/cli-orchestration/SKILL.md` documenting: tmux_tool actions, generic send/observe/detect/read loop, per-CLI prompt patterns, exit sequences, and the OpenCode-specific wrapper. Must follow the same structure as `claude-cli/SKILL.md`. |

### Differentiators (Competitive Advantage)

Features that make the orchestration significantly more robust but are not the minimum to close the milestone.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **CLI-05: Pre-built OpenCode CLI wrapper (`opencode_session()`)** | Following the `ClaudeSession` pattern from v1.1, an `OpenCodeSession` class would abstract session lifecycle, prompt detection, and response extraction behind a simple `session.run("prompt")` interface. Callers don't implement the send/wait/capture loop themselves. | HIGH | Complexity is in the OpenCode-specific prompt detection. OpenCode TUI uses ANSI color codes to render its input field — detecting "ready for input" requires ANSI-aware pattern matching (or stripping ANSI and matching the stripped text). The non-interactive `opencode run` mode is simpler: subprocess exit = done. Recommendation: implement via `opencode run "prompt"` subprocess first (mirrors ClaudeSession pattern), add TUI interaction only if needed. |
| **Pane-specific targeting (named panes, not just `shared`)** | Allows Agent to target different panes within the shared terminal — e.g., run opencode in pane 1 while monitoring output in pane 2. Enables parallel CLI sessions. | MEDIUM | `tmux send-keys -t shared:0.1` targets window 0, pane 1. The tmux_tool needs a `pane` parameter. Low implementation cost per pane, but multi-pane coordination logic adds complexity. |
| **ANSI stripping before prompt pattern matching** | Raw capture-pane output contains ANSI escape sequences (`\x1b[...m`). Matching `$ ` in ANSI-decorated text requires stripping first. Without this, prompt patterns fail against color-decorated prompts. | LOW | Python: `re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', raw)`. Already implicitly needed by TERM-05. Should be a utility function in the tmux_tool or the skill. `code_execution_tool.py`'s `fix_full_output()` does a partial version of this — reference implementation. |
| **Scrollback depth control for capture-pane** | Default capture may miss response content for long outputs. Parameterizing `-S -N` lets callers get more history without always pulling maximum scrollback. | LOW | Simple parameter addition. Default of -200 lines covers most cases. Increase to -1000 for verbose CLI tools. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Using `TTYSession` for the shared terminal** | TTYSession is available in the codebase and provides PTY-based interaction. Might seem like the right tool for interactive CLI orchestration. | TTYSession spawns a NEW subprocess. The shared terminal is an EXISTING tmux session that the user can see and interact with. Creating a TTYSession to "control" the shared terminal doesn't interact with the shared session — it creates an invisible parallel process. The user's terminal view becomes inconsistent with what the agent is doing. | Use tmux send-keys + capture-pane for ALL interaction with the shared terminal. TTYSession is the right tool for isolated headless subprocess control (which has different use cases). |
| **Running opencode with `browser_agent` (Playwright)** | Playwright can interact with web-based TUIs. OpenCode might have a web interface. | OpenCode's TUI is a terminal application, not a browser tab. Playwright cannot interact with terminal content. This is a category error. | Use tmux send-keys + capture-pane for terminal TUI control. If OpenCode ever ships a web UI, revisit. |
| **Infinite polling loop without timeout** | "Just keep polling capture-pane until the prompt appears." | Without a max-wait timeout, any deadlocked CLI (crashed, waiting for a keypress the agent doesn't know about) causes the agent to hang forever. This blocks the entire Agent Zero session. | Always pair polling loops with a `max_total_timeout` (e.g., 120s for long AI responses, 30s for quick commands). Log the pane content on timeout so the agent can diagnose the state. |
| **Sending raw escape sequences via send-keys** | "Send `\x1b[A` for up-arrow instead of tmux key names." | Raw escape sequences may be interpreted differently depending on tmux terminal settings and the target application's input handling. tmux key names (`Up`, `Escape`, `C-c`) are portable and well-defined across tmux versions. | Use tmux key name syntax exclusively: `tmux send-keys -t target Escape ""`, `tmux send-keys -t target Up ""`. |
| **Running opencode interactively inside `code_execution_tool`** | Seems like the simplest approach — start opencode in an existing Agent Zero PTY session. | `code_execution_tool` prompt patterns (`$ `, `# `, `PS >`) will match before opencode has finished responding, causing premature output capture. The sentinel pattern (`__A0_xyz:0`) added to commands won't work for interactive CLIs that don't exit. The PTY sessions are Agent Zero's own work shells — injecting another interactive process creates state confusion. | Run opencode in the shared tmux session (separate from Agent Zero's PTY shells) and interact via tmux send-keys + capture-pane. This is visually transparent to the user and does not contaminate Agent Zero's work sessions. |
| **Expecting subprocess exit for TUI opencode completion** | The claude CLI `--print` mode exits cleanly when done. Reuse same pattern for opencode TUI. | OpenCode TUI does not exit after each prompt — it stays running and waits for the next input. The TUI is a persistent process, not a request-response subprocess. Process exit is NOT the completion signal for TUI mode. | For opencode TUI: screen-scrape input prompt re-appearance. For opencode non-interactive: use `opencode run "prompt"` which DOES exit after one turn — matching the subprocess-exit pattern from ClaudeSession. |

---

## Feature Dependencies

```
[TERM-01: Send text + Enter]
    └──required by──> [CLI-01: Start interactive CLI]
    └──required by──> [CLI-02: Send prompts / multi-turn]
    └──required by──> [CLI-05: opencode_session()]

[TERM-02: Send text without Enter]
    └──required by──> [CLI-02: Send prompts — for single-char responses to inline prompts]

[TERM-03: Send special keys]
    └──required by──> [CLI-04: Interrupt/exit CLI]
    └──enhances──> [CLI-02: Send prompts — for navigation in TUI]

[TERM-04: Capture pane screen content]
    └──required by──> [TERM-05: Detect readiness]
    └──required by──> [CLI-02: Read response after sending]
    └──required by──> [CLI-03: Detect when CLI is done]

[TERM-05: Detect readiness]
    └──requires──> [TERM-04: Capture pane]
    └──required by──> [CLI-02: Send prompts — must wait before sending]
    └──required by──> [CLI-03: Detect completion]
    └──required by──> [CLI-05: opencode_session()]

[CLI-01: Start interactive CLI]
    └──requires──> [TERM-01]
    └──requires──> [TERM-05 — wait for initial prompt before first interaction]

[CLI-02: Send prompts + read responses]
    └──requires──> [TERM-01 + TERM-02 + TERM-04 + TERM-05]

[CLI-03: Detect completion]
    └──requires──> [TERM-04 + TERM-05]

[CLI-04: Interrupt/exit]
    └──requires──> [TERM-03]

[CLI-05: opencode_session() wrapper]
    └──requires──> [CLI-01 + CLI-02 + CLI-03 + CLI-04]
    └──follows pattern of──> [ClaudeSession from python/helpers/claude_cli.py]

[CLI-06: Generic CLI orchestration SKILL.md]
    └──requires──> [CLI-01..05 all validated]
    └──documents──> [tmux_tool API + per-CLI patterns]
```

### Dependency Notes

- **TERM-04 + TERM-05 are the core difficulty:** Everything else is straightforward tmux invocation. Screen capture and readiness detection are where the complexity lives, because terminal output is noisy (ANSI codes, partial lines, spinner characters) and interactive TUIs don't emit stable "I'm done" signals.

- **TERM-01..04 can all be implemented in a single `tmux_tool` with action dispatch:** One new Python tool `python/tools/tmux_tool.py` with `action` parameter (`send`, `send_keys`, `capture`, `send_and_wait`). This is lower overhead than four separate tools.

- **CLI-05 (opencode wrapper) should use `opencode run` non-interactive first:** The `opencode run "prompt"` mode exits after one turn, giving process-exit completion detection — identical to `ClaudeSession`. Only escalate to TUI interaction if multi-turn with session memory is required. Session continuation in non-interactive mode uses `--continue` or `--session` flag (similar to claude's `--resume UUID`).

- **OpenCode session continuity note:** OpenCode `--continue` flag continues the most recent session; `--session <id>` targets a specific session. The session memory issue in non-interactive mode (GitHub Issue #917) is real — verify session memory works before relying on it. Fallback: embed prior context in each prompt (less elegant but reliable).

---

## OpenCode CLI Behavior Reference

Research findings on what OpenCode expects from an orchestrator (MEDIUM confidence — web sources, not direct CLI interrogation of local binary).

### Non-Interactive Mode (`opencode run`)

```bash
# Single-turn — process exits after response
opencode run "Explain the use of context in Go"

# With quiet flag (suppress spinner — needed for scripting)
opencode run -q "prompt"

# With JSON output format
opencode run -f json "prompt"

# Continue most recent session
opencode run --continue "follow-up prompt"

# Target specific session
opencode run --session <session-id> "prompt"

# Allow specific tools only
opencode run --allowedTools "bash,read_file" "prompt"

# Title for the session (scripting/logging)
opencode run --title "Task name" "prompt"
```

**Completion signal:** Process exits (returncode 0 = success). Identical pattern to `claude --print`.

**Known issue (subprocess.Popen hang):** GitHub Issue #11891 documents that `opencode run --format json` can hang indefinitely when launched via Python `subprocess.Popen` + `readline()`. Mitigation: use `subprocess.run` (blocking, captures all output at once) rather than streaming. Matches the `ClaudeSession` subprocess.run pattern exactly.

**Known issue (session memory in non-interactive):** GitHub Issue #917 reports session memory is not reliably passed in non-interactive mode. Test this before depending on `--continue` for multi-turn state.

### Interactive TUI Mode (`opencode` with no args)

```
Starts a full TUI with:
  - Input field at bottom
  - Response streaming above
  - Spinner while processing
  - Input field disappears during processing
  - Input field reappears when ready for next prompt
```

**Completion signal for TUI:** Input field re-appearance in the pane. No structured exit code. Must screen-scrape via `tmux capture-pane`.

**Prompt detection strategy for TUI:** ANSI strip the captured pane, then look for the input field indicator. The exact prompt string varies by opencode version and theme. Fallback: idle timeout after output stops flowing (no new content in capture-pane across N polls).

**ForgeFlow precedent:** The ForgeFlow project (September 2025, GitHub: Kingson4Wu/ForgeFlow) documents this exact adapter pattern for interactive AI CLIs in tmux. Its approach: (1) ANSI-aware capture, (2) regex detection of tool-specific "ready" prompts, (3) configurable rules system. Validates that the approach is technically sound and not novel.

### Exit Signals

| Exit Method | Use When | tmux Command |
|-------------|----------|--------------|
| `/quit` then Enter | OpenCode TUI graceful exit | `send-keys -t shared "/quit" Enter` |
| `q` then Enter | OpenCode compact exit command | `send-keys -t shared "q" Enter` |
| Ctrl+C | Interrupt ongoing response | `send-keys -t shared C-c ""` |
| Ctrl+D | EOF signal (some CLIs) | `send-keys -t shared C-d ""` |
| Process kill | Last resort — may leave tmux pane in bad state | `tmux send-keys -t shared C-c ""` then verify |

---

## MVP Definition

### Launch With (v1.2)

Minimum to satisfy TERM-01..05 and CLI-01..04, CLI-06 from PROJECT.md.

- [ ] **TERM-01:** `tmux_tool` with `send` action — sends text + Enter to shared pane
- [ ] **TERM-02:** `tmux_tool` with `send_literal` action — sends text without Enter (literal characters)
- [ ] **TERM-03:** `tmux_tool` with `send_key` action — sends named special keys (C-c, C-d, Escape, Tab, Up, Down)
- [ ] **TERM-04:** `tmux_tool` with `capture` action — returns current pane content (last N lines of scrollback)
- [ ] **TERM-05:** `tmux_tool` with `send_and_wait` action — sends text + Enter then polls capture-pane for prompt pattern or idle timeout
- [ ] **CLI-01..04:** `send_and_wait` action handles the start/interact/read/interrupt lifecycle for generic interactive CLIs
- [ ] **CLI-05:** `opencode_session()` helper in `python/helpers/opencode_cli.py` — uses `opencode run` subprocess (not TUI) following `ClaudeSession` pattern
- [ ] **CLI-06:** `usr/skills/cli-orchestration/SKILL.md` — documents tmux_tool API, generic orchestration loop, OpenCode patterns, and per-CLI prompt/exit reference

### Add After Validation (v1.x)

- [ ] **TUI-mode opencode interaction** — only if `opencode run` session memory proves unreliable. Trigger: need for stateful multi-turn with opencode where `--continue` fails.
- [ ] **Multi-pane targeting** — only if parallel CLI sessions become a use case. Trigger: need to run two CLIs simultaneously.
- [ ] **Scrollback depth parameter** — expose `-S -N` as a parameter in capture action. Trigger: verbose CLI output truncated.

### Future Consideration (v2+)

- [ ] **MCP-based tmux control** — structured tmux MCP servers (bnomei/tmux-mcp, Jonrad/tmux-mcp) provide typed APIs over raw shell commands. Defer until raw tmux approach proves insufficient.
- [ ] **OpenCode streaming JSON** — `opencode run -f json` streams structured events. Complex to pipe in real-time. Defer until streaming output to Agent Zero UI is a validated need.
- [ ] **Other interactive CLI wrappers** — aider, Codex CLI, custom REPLs. Defer until the generic pattern is proven and a specific tool is needed.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| TERM-01: send text + Enter | HIGH | LOW | P1 — foundational, everything depends on it |
| TERM-04: capture pane | HIGH | LOW | P1 — agent's eyes on the terminal |
| TERM-05: prompt detection / idle wait | HIGH | HIGH | P1 — required for safe interaction |
| TERM-02: send without Enter | MEDIUM | LOW | P1 — needed for inline prompt responses |
| TERM-03: send special keys | MEDIUM | LOW | P1 — needed for CLI-04 interrupt/exit |
| CLI-01: start interactive CLI | HIGH | LOW | P1 — depends on TERM-01 + TERM-05 |
| CLI-02: send prompts + read | HIGH | MEDIUM | P1 — core orchestration loop |
| CLI-03: detect completion | HIGH | HIGH | P1 — without this, agent sends blind |
| CLI-04: interrupt/exit | MEDIUM | LOW | P1 — prevents orphan processes |
| CLI-05: opencode_session() | HIGH | MEDIUM | P2 — ClaudeSession pattern, after generic works |
| CLI-06: SKILL.md | HIGH | LOW | P1 — but last, after all patterns validated |
| ANSI stripping utility | MEDIUM | LOW | P1 — needed before TERM-05 can work |
| Multi-pane targeting | LOW | LOW | P3 — future parallel sessions |
| TUI-mode opencode | LOW | HIGH | P3 — non-interactive mode is sufficient |

**Priority key:**
- P1: Must have for v1.2 launch
- P2: Should have, add when core is proven
- P3: Nice to have, future consideration

---

## Existing Infrastructure Dependencies

All of these must be present and working for v1.2. All confirmed present from v1.0/v1.1.

| Capability | Where | Required By |
|------------|-------|-------------|
| tmux `shared` session | `apps/shared-terminal/startup.sh` | All TERM-* and CLI-* features |
| `tmux send-keys` available in Agent Zero environment | Host PATH (or Docker) | TERM-01..03 |
| `tmux capture-pane` available | Host PATH (or Docker) | TERM-04..05 |
| `code_execution_tool.py` prompt patterns + idle detection | `python/tools/code_execution_tool.py` | Reference implementation for TERM-05 |
| `TTYSession` idle-timeout pattern | `python/helpers/tty_session.py` | Reference for CLI-02/03 collection loop |
| `ClaudeSession` subprocess.run pattern | `python/helpers/claude_cli.py` | Reference for CLI-05 opencode wrapper |
| opencode binary available on host PATH | `~/.local/bin/opencode` or `opencode` on PATH | CLI-05 |
| `CLAUDECODE` env fix pattern | `python/helpers/claude_cli.py` | N/A for opencode (not claude — different env check) |

---

## Sources

- `/Users/rgv250cc/Documents/Projects/agent-zero/python/tools/terminal_agent.py` — existing tmux tool, shows send-keys + sentinel pattern (live file)
- `/Users/rgv250cc/Documents/Projects/agent-zero/python/tools/code_execution_tool.py` — prompt detection patterns, idle timeout, dialog detection (live file)
- `/Users/rgv250cc/Documents/Projects/agent-zero/python/helpers/tty_session.py` — TTYSession read_chunks_until_idle pattern (live file)
- `/Users/rgv250cc/Documents/Projects/agent-zero/python/helpers/claude_cli.py` — ClaudeSession pattern to replicate for opencode_session (live file)
- `/Users/rgv250cc/Documents/Projects/agent-zero/usr/skills/claude-cli/SKILL.md` — Observe→Act→Verify analog for CLI interaction (live file)
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/PROJECT.md` — v1.2 milestone requirements TERM-01..05, CLI-01..06 (live file)
- [OpenCode CLI docs](https://opencode.ai/docs/cli/) — non-interactive mode, -q flag, --continue, --session flags (MEDIUM confidence)
- [OpenCode GitHub Issue #917: Session memory in non-interactive](https://github.com/sst/opencode/issues/917) — confirms session memory risk (MEDIUM confidence)
- [OpenCode GitHub Issue #11891: subprocess.Popen hang with JSON format](https://github.com/anomalyco/opencode/issues/11891) — confirms use subprocess.run not Popen (MEDIUM confidence)
- [ForgeFlow: AI CLI automation in tmux](https://dev.to/kingson4ng/forgeflow-engineering-grade-automation-for-ai-clis-inside-tmux-36fj) — validates ANSI-aware prompt detection approach (MEDIUM confidence)
- [tmux send-keys key names](https://tao-of-tmux.readthedocs.io/en/latest/manuscript/10-scripting.html) — C-c, Escape, Up/Down syntax confirmed (HIGH confidence)
- [GitHub: Kingson4Wu/ForgeFlow](https://github.com/Kingson4Wu/ForgeFlow) — adapter+rules architecture for interactive CLI orchestration (MEDIUM confidence)
- [Claude Code Agent Farm](https://github.com/Dicklesworthstone/claude_code_agent_farm) — --idle-timeout pattern for tmux-based agent orchestration (MEDIUM confidence)

---

*Feature research for: Agent Zero v1.2 — tmux terminal interaction + interactive CLI orchestration*
*Researched: 2026-02-25*
