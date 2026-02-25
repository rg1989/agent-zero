# Pitfalls Research

**Domain:** tmux-based terminal orchestration + interactive CLI control added to an existing Agent Zero fork (v1.2 Terminal Orchestration milestone)
**Researched:** 2026-02-25
**Confidence:** HIGH (direct codebase analysis of existing TTYSession/code_execution_tool/shared-terminal, verified against tmux upstream issues and OpenCode issue tracker)

> **Scope note:** This document covers v1.2 (tmux_tool + OpenCode CLI orchestration). For v1.1 pitfalls (CDP browser + claude CLI subprocess), see the prior research on file — this document supersedes PITFALLS.md and focuses entirely on the new milestone domain.

---

## Critical Pitfalls

### Pitfall 1: capture-pane Reads Stale Output Because tmux Renders Asynchronously

**What goes wrong:**
`tmux capture-pane -p -t shared` executes and returns immediately with whatever is currently in the pane's render buffer. When called immediately after `tmux send-keys`, it reads the output that was present *before* the command finished, not after. The agent captures the previous command's output, not the new one, and incorrectly concludes the command is complete with stale results.

**Why it happens:**
tmux is event-driven. `send-keys` puts keystrokes into the pseudo-terminal's input buffer; the shell process reads them and starts executing asynchronously. `capture-pane` reads the *display buffer*, which is the terminal's rendered screen — it does not wait for any process to finish. The gap between keystroke injection and screen update can be 50–500ms under normal conditions and multiple seconds for long-running commands.

**How to avoid:**
Never call `capture-pane` immediately after `send-keys`. Always implement a polling loop:
1. Send keys.
2. Wait a minimum settle time (100–200ms) before first read.
3. Poll `capture-pane` at regular intervals (300–500ms), comparing successive captures.
4. Declare "done" only when the screen content has been stable (no change between two consecutive reads) AND the last line matches a known prompt pattern.

Use `tmux capture-pane -p -t shared -S -` to capture the full scrollback rather than just the visible pane area, so long output is not clipped.

**Warning signs:**
- Captured output contains the *previous* command's prompt line followed by the new command text, not the new command's output.
- Agent receives empty string from capture despite the command being long-running.
- Output appears correct on one run but truncated on another — timing sensitive.

**Phase to address:** TERM-04 (capture current screen content) and TERM-05 (readiness detection)

---

### Pitfall 2: Prompt Detection False Positives From Command Output That Resembles a Prompt

**What goes wrong:**
The existing `CodeExecution` tool uses prompt_patterns like `root@[^:]+:[^#]+# ?$` and `[a-zA-Z0-9_.-]+@[^:]+:[^$#]+[$#] ?$`. These match shell prompts reliably for *one-shot commands*. When orchestrating interactive CLIs in the shared terminal, the output from the program being run can contain text that matches these patterns. For example: OpenCode prints progress lines like `> Running tool` or a Python REPL echoes `>>> ` — both match prompt-like patterns. The agent thinks the CLI is done and ready for input when it's actually mid-response.

**Why it happens:**
The prompt_patterns in `code_execution_tool.py` were designed for the shell wrapper — they match the *shell's own prompt* that appears at the end of a command. When the shared terminal is running an interactive CLI like OpenCode, the shell prompt is hidden (OpenCode has taken over the terminal) and the CLI emits its own cursor/prompt characters. These are different patterns and were never accounted for.

**How to avoid:**
For tmux_tool interacting with the shared terminal running an interactive CLI:
- Do NOT reuse the shell prompt_patterns from `code_execution_tool.py`. These apply to a *bash* session, not an OpenCode session.
- Identify and hardcode the specific ready-state indicator for each CLI. For OpenCode TUI: the TUI renders a visible input area; the ready signal is when the screen stops changing (screen stability), not a specific text pattern. For `opencode run` (non-interactive mode): completion is indicated by process exit (exit code 0), not a prompt.
- For generic CLIs in the shared terminal, use screen-stability detection (two identical consecutive captures with no output change) plus a minimum wait time as the fallback.

**Warning signs:**
- Agent sends the next prompt while OpenCode is still generating, causing garbled input.
- Rapid fire of multiple inputs because each line of verbose output triggers a false "ready" detection.
- `> ` or `>>>` appearing in OpenCode progress output triggers early return.

**Phase to address:** TERM-05 (readiness detection), CLI-03 (CLI done-response detection)

---

### Pitfall 3: ANSI Escape Sequences and OSC Sequences Corrupt capture-pane Output

**What goes wrong:**
By default, `tmux capture-pane` returns the pane content with ANSI color/formatting codes *stripped* — this sounds correct, but it is not the whole picture. tmux passes through OSC sequences (Operating System Commands, e.g. `\x1b]0;title\x07` for terminal title setting) and some CSI sequences that it does not interpret. Interactive CLIs like OpenCode emit heavy ANSI output including cursor movement (`\x1b[A`, `\x1b[2K`), inline progress spinners (which overwrite previous lines), and bracketed paste mode markers. Even after capture-pane's basic ANSI stripping, the resulting text contains these sequences mixed into what appears to be plain text.

The `-e` flag to `capture-pane` *preserves* escape sequences (adds them back for display purposes) and should never be used for programmatic parsing.

**Why it happens:**
`capture-pane` outputs what the terminal *displays*, not what the program *wrote*. A TUI like OpenCode renders using absolute cursor positioning — lines get overwritten in place. The captured output may show partial lines, spinner artifacts (`⠋`, `⠙`), or duplicate content from cursor-up-then-rewrite sequences.

**How to avoid:**
- Always strip the captured output through a comprehensive ANSI regex before processing: `re.sub(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07)', '', text)`.
- After stripping, also strip bare `\r` (carriage returns without `\n`) and collapse runs of blank lines.
- For OpenCode TUI specifically: use `opencode run <prompt>` (non-interactive mode) instead of injecting into the TUI via send-keys wherever possible. The `run` subcommand outputs cleaner text to stdout without TUI rendering artifacts.
- Never try to parse cursor-positioning sequences to reconstruct "what's on screen line N" — use `capture-pane` whole-buffer captures and strip aggressively.

**Warning signs:**
- Captured text contains `\x1b[2K` (clear line), `\x1b[A` (cursor up), or spinner characters (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`).
- Line-by-line parsing produces duplicate content (same line appears twice from cursor-up-rewrite pattern).
- OpenCode's multi-line response appears as a single garbled line with embedded escape codes.

**Phase to address:** TERM-04 (screen capture), CLI-02 (read CLI responses)

---

### Pitfall 4: Sentinel Echo Leaks into the Shared Terminal and Corrupts the Interactive Session

**What goes wrong:**
The existing `code_execution_tool.py` / `shell_local.py` uses a sentinel-based end-of-command detection: it runs the actual command, then immediately runs `echo SENTINEL_<uuid>` and waits for that exact string in output to know the command has finished. This pattern works cleanly in the *agent's own isolated PTY sessions*. But if anyone applies this same pattern in the *shared terminal* (the tmux `shared` session that's also visible to human users via ttyd), the sentinel echo appears visibly in the browser terminal and breaks any interactive CLI currently running there.

**Why it happens:**
The shared terminal (`tmux new-session -s shared`) is shared between the agent and the user. It is a persistent, interactive session — not an isolated subprocess. Injecting `echo SENTINEL_XYZ` via `tmux send-keys` sends that text as keyboard input to *whatever process currently has focus* in that pane — which might be `bash`, `opencode`, a Python REPL, or a running `less` pager. The sentinel appears as user-typed text, corrupts the running program's input buffer, and is permanently visible in the terminal scrollback.

**How to avoid:**
- The shared terminal must NEVER receive sentinel injection. This is an absolute rule.
- For the shared terminal, use *screen-stability detection* (compare successive `capture-pane` outputs) plus *prompt-pattern matching* as the only readiness signals.
- For any operation that requires sentinel-based detection, use a *separate, dedicated tmux window or session* (`tmux new-session -d -s agent-scratch`) that is NOT the `shared` session. The agent gets its own isolated window; the human sees only the `shared` window.
- Document this boundary clearly in the tmux_tool implementation: commands to `shared` use stability polling; commands to agent-private windows can use sentinels.

**Warning signs:**
- The shared browser terminal (ttyd) shows `echo SENTINEL_abc123` appearing mid-CLI-output.
- Interactive program (Python REPL, OpenCode) receives unexpected text and crashes or throws an error.
- Human user reports "random text appearing" in the terminal.

**Phase to address:** TERM-01 (send text to tmux pane) — establish the no-sentinel-in-shared rule before any code is written

---

### Pitfall 5: tmux Session Name Collision Causes Silent Failure or Wrong Target

**What goes wrong:**
The shared terminal uses session name `shared`. If the agent creates additional tmux sessions (for scratch work, for running isolated commands), name collisions cause two types of failures:

1. `tmux new-session -s shared` fails with exit code 1 ("session 'shared' already exists") — silently skipped with `|| true` in most scripts, leaving the agent targeting the wrong existing session.
2. Session names containing special characters (`.`, `:`, `%`, `$`, `@`) break the `-t` target format parser. tmux uses `.` as a pane separator and `:` as a window separator — a session named `agent.task:1` is parsed as `session=agent`, `window=task`, `pane=1`.

**Why it happens:**
The `startup.sh` pre-creates `shared` with `tmux new-session -d -s shared 2>/dev/null || true`. This is correct for the startup script. But if tmux_tool creates additional sessions programmatically without checking for collisions, and names them with app-name-style strings that contain dots or colons, the targeting silently breaks.

**How to avoid:**
- For programmatic agent-private sessions: use `tmux new-session -d -s agent-$(date +%s)` or include a UUID fragment: `agent-$(python3 -c "import uuid; print(str(uuid.uuid4())[:8])")`. Avoid dots and colons in session names entirely.
- Before creating any session: `tmux has-session -t <name> 2>/dev/null && echo EXISTS`. If it exists and is agent-private, kill and recreate; if it's `shared`, never destroy it.
- Use tmux's stable ID format (`$N` for sessions, `@N` for windows, `%N` for panes) when targeting from scripts — IDs are stable even if sessions are renamed.
- For the `shared` session specifically: always check `tmux has-session -t shared` returns 0 before sending keys, and never attempt to create or destroy it from tmux_tool.

**Warning signs:**
- `tmux send-keys -t shared` returns exit code 1 — session was accidentally killed.
- Agent sends commands to `agent-scratch` but they appear in the user-visible `shared` session — collision caused wrong session to be targeted.
- `tmux new-session` succeeds but `tmux ls` shows two sessions with similar names.

**Phase to address:** TERM-01 (send text to named tmux pane), CLI-01 (start CLI session)

---

### Pitfall 6: code_execution_tool Shell Sessions and tmux_tool Operate in Separate Shell Environments

**What goes wrong:**
Agent Zero's existing `code_execution_tool` (via `LocalInteractiveSession` / `TTYSession`) manages its own private PTY sessions — completely separate from the shared terminal. A command run through `code_execution_tool runtime=terminal` is NOT visible in the shared browser terminal and has NO access to anything running in the `shared` tmux session. Developers may mistakenly assume that `cd /some/dir` in a `code_execution_tool` session has any effect on what the shared terminal sees — it does not.

Conversely, the new `tmux_tool` (sending keys to the `shared` session) operates in the user-visible shell. If the user's shell has an active virtual environment or changed directory, those state changes are NOT reflected in any `code_execution_tool` session.

**Why it happens:**
These are separate processes with separate environments. `code_execution_tool` creates subprocess shells via `TTYSession(runtime.get_terminal_executable())`. The `shared` tmux session is a completely different bash process managed by tmux and ttyd. There is no shared state between them.

**How to avoid:**
- Never use `code_execution_tool` to "set up" state for commands that will be sent to the shared terminal via tmux_tool, or vice versa.
- Document this boundary in both the tmux_tool docstring and the CLI orchestration skill.
- If the agent needs to run setup commands before starting an interactive CLI, run those setup commands via tmux send-keys in the same shared session — do not mix execution contexts.
- For OpenCode CLI: if you need to set environment variables (e.g. `ANTHROPIC_API_KEY`) before running opencode in the shared terminal, send those via tmux send-keys to the same session: `tmux send-keys -t shared "export ANTHROPIC_API_KEY=$KEY && opencode run 'prompt'" Enter`.

**Warning signs:**
- Agent sets `PATH` or activates a venv via `code_execution_tool`, then tries to run a binary in the shared terminal that can't be found.
- `cd` commands in `code_execution_tool` have no effect on the shared terminal's working directory.
- Environment variables set in one context are missing in the other.

**Phase to address:** TERM-01, CLI-01 — establish execution context model in skill documentation before writing code

---

### Pitfall 7: opencode run Hangs Indefinitely on v0.15+ — Process Never Exits

**What goes wrong:**
In OpenCode versions 0.15.0 through at least 0.15.2, `opencode run <prompt>` (non-interactive mode) completes its output stream but the process never exits. It finishes generating the response, prints it, then hangs — requiring `Ctrl+C` (SIGINT) to return control to the shell. When Agent Zero wraps this in a subprocess call or a tmux send-keys pattern expecting process exit as the done signal, it waits forever.

This is a confirmed, documented regression (GitHub issue #3213, sst/opencode). Downgrading to 0.14.7 is the only known workaround as of the research date.

**Why it happens:**
The 0.15.0 rewrite of OpenCode's TUI architecture (moving from go+bubbletea to an in-house zig+solidjs framework called OpenTUI) introduced a process lifecycle bug where the server component continues running after the TUI client exits. Because `opencode run` starts both components internally, the process hangs on the server side even after the client-side response is complete.

**How to avoid:**
- Pin OpenCode to a version where `opencode run` exits cleanly (e.g. `<0.15.0` or verify on the exact installed version before writing automation code).
- Do not rely on process exit as the sole done signal. Use an alternative: capture output until it stops changing (screen stability with timeout), then send the interrupt if the process is still alive.
- If using `subprocess.Popen` to run `opencode run`: set a hard `timeout` and follow it with `process.terminate()` if it does not exit cleanly.
- Check the installed version: `opencode --version` before building any automation. Document the tested version in the CLI orchestration skill.
- Consider using the OpenCode HTTP server mode (`opencode serve`) + API calls instead of `opencode run` for programmatic use — the server mode is explicitly designed for scripting and does not have the hang bug.

**Warning signs:**
- `opencode run "prompt"` prints the response and then the terminal cursor hangs — no shell prompt returns.
- `subprocess.Popen.wait()` or `process.communicate()` never returns.
- `tmux send-keys -t shared "opencode run 'prompt'" Enter` followed by screen-stability polling shows stable output but the shell prompt never reappears.

**Phase to address:** CLI-02 (send prompts, read responses), CLI-03 (detect CLI done), CLI-05 (OpenCode wrapper)

---

### Pitfall 8: Interactive CLI State Machine Confusion — CLI Sees Prior Session's Partial Input

**What goes wrong:**
When tmux_tool sends input to an interactive CLI (OpenCode TUI or a Python REPL) and then the agent needs to interrupt (Ctrl+C), the CLI's input buffer may contain a partially-typed command. The next time input is sent, it appends to the partial buffer rather than starting fresh. Result: the next command is corrupted with leftover characters from the previous interaction.

This also occurs on session resume: if Agent Zero crashed mid-interaction or the connection was lost, the tmux pane still has the interactive CLI waiting at a partial input state. The next agent run resumes injection into a poisoned buffer.

**Why it happens:**
Interactive CLIs maintain their own line-editing state (readline, the TUI framework). `Ctrl+C` cancels the *current running command* but does not clear the line buffer if the CLI was waiting for input with partial text already entered. tmux send-keys sends raw keystrokes and has no concept of "is the buffer empty?"

**How to avoid:**
- Before injecting any new command into an interactive CLI, send a "clean state" sequence:
  1. `Ctrl+C` — cancel any running operation.
  2. Wait for screen stability.
  3. `Ctrl+U` — clear the current line buffer (works in bash, Python REPL, many CLIs).
  4. Verify the captured screen shows an empty prompt line before injecting new input.
- After a crash/resume, assume the CLI is in unknown state and restart it:
  1. Try `Ctrl+D` or `exit` to exit the CLI gracefully.
  2. If the CLI exits, re-launch it cleanly.
  3. If `Ctrl+D` doesn't exit (the CLI is stuck), send `Ctrl+C` repeatedly, then kill the process by its PID.

**Warning signs:**
- Commands sent to OpenCode arrive as `<previous partial text><new command>`, producing syntax errors.
- CLI reports `KeyboardInterrupt` on the injected command — the `Ctrl+C` cleared the partial input correctly but the command was interpreted as a new input, not an interrupt.
- Screen shows `>>> f` before the agent sends `compute_something()` — result is `>>> fcompute_something()`.

**Phase to address:** CLI-02 (send prompts to running CLI), CLI-04 (interrupt / exit)

---

### Pitfall 9: `tmux send-keys` Injects Before the Shell Is Ready After Session Attach or CLI Exit

**What goes wrong:**
After attaching to a tmux session that has just started (e.g. `startup.sh` runs `tmux new-session -d -s shared`), or after an interactive CLI exits and drops back to the shell prompt, there is a short window where the shell is initializing (loading `.bashrc`, setting `$PS1`, etc.). If tmux_tool immediately sends keys during this window, the keystrokes are received by the shell but processed incorrectly: they appear at the prompt but are not executed, or they are executed before the shell's readline is ready, causing them to be treated as raw text rather than commands.

This is the same race condition documented in claude-code's own issue tracker (#23513) when spawning team agents in tmux panes.

**Why it happens:**
`tmux new-session` returns success as soon as the pty process is forked — not when the shell inside has finished initialization. On systems with heavy `~/.bashrc` (nvm, conda, rbenv, custom prompts), initialization can take 500ms–2s. The agent's polling starts immediately and sees a "ready" prompt that is actually a partially-initialized shell.

**How to avoid:**
- After any session creation or CLI exit, wait for the shell prompt pattern to appear in `capture-pane` output before sending new commands. Do not rely on a fixed sleep.
- Use the poll-and-compare pattern: capture screen, wait 300ms, capture again. If the second capture shows a stable shell prompt line (matching one of `code_execution_tool.py`'s `prompt_patterns`), the shell is ready.
- For the `shared` session on startup: the `startup.sh` already pre-creates it — the health check should verify the session exists and shows a stable prompt before the agent attempts any injection.

**Warning signs:**
- First command sent to a fresh session appears as partial text in the prompt but does not execute.
- Shell shows the command text but no output — it was echoed without execution.
- Works when there's a manual `sleep 2` between session create and send, fails without it.

**Phase to address:** TERM-01 (send text to tmux pane), CLI-01 (start interactive CLI session)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Fixed `sleep` after `send-keys` before `capture-pane` | Simple, no polling logic | Race condition on slow hosts; over-waits on fast ones | Never for production; use poll-and-compare instead |
| Screen stability as sole readiness signal (no prompt detection) | Works for any CLI | Slow commands with periodic output (progress bars) will never appear stable until complete; timeout becomes the fallback | Acceptable as fallback only — combine with prompt detection where possible |
| Sharing `code_execution_tool` shell sessions with tmux_tool | Reuses existing infrastructure | Completely different execution contexts; state assumptions will fail | Never — they are separate environments; document and enforce boundary |
| Using `opencode run` without version pin | Latest features | Hang bug on ≥0.15.0 may return in any release | Only when version is pinned to a tested build |
| Sentinel injection into shared terminal | Reliable end detection | Visually corrupts the terminal; breaks any running interactive program | Never — shared terminal is user-visible; sentinels are for isolated sessions only |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `tmux capture-pane` after `send-keys` | Call immediately after sending keys | Wait minimum 200ms, then poll until stable |
| `capture-pane` output parsing | Treat as plain text | Strip ANSI sequences (`\x1b[...m`, `\x1b[...K`, OSC `\x1b]...\x07`) before processing |
| OpenCode `opencode run` | Expect process to exit normally | Set a hard timeout; terminate if process does not exit; verify installed version |
| Shared terminal vs. agent sessions | Use `code_execution_tool` to set up state for tmux commands | Each context is completely isolated — set up state within the same execution context |
| `tmux new-session -s shared` | Always runs, even if session already exists | Check with `has-session` first; the shared session must never be recreated or destroyed by automation |
| Interactive CLI input buffer | Inject new command without clearing buffer | Send Ctrl+U before injecting to clear any partial input |
| Special characters in tmux `-t` targets | Use dots/colons in session names | Only use alphanumeric + hyphens in programmatic session names; use `$N` IDs for stability |
| OpenCode TUI mode vs. run mode | Run OpenCode TUI for programmatic use | Use `opencode run <prompt>` for scripting; TUI mode is interactive-only and not automatable |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| High-frequency `capture-pane` polling (< 100ms interval) | Excessive subprocess spawn overhead; tmux socket contention | Poll at 300–500ms intervals; use a stable-count check (N consecutive identical captures) | At any polling rate — tmux is not designed for sub-100ms polling |
| Reading full scrollback on every poll (`-S -` flag) | Large output buffers slow string comparison; high memory use | Only read visible pane (`-S 0`) during polling; use full scrollback only for final content extraction | When the terminal has > ~10K lines of history |
| Launching `opencode run` as a new process per agent message | Each invocation pays full cold-boot cost (MCP server startup, ~3–5s) | Use `opencode serve` and send API requests; or keep a persistent `opencode` process and reuse it | Every invocation — MCP server cold boot adds 3–5s overhead per turn |
| Using TTYSession to drive shared terminal instead of tmux subcommands | TTYSession creates a new shell process; not connected to the shared tmux session at all | Use `subprocess.run(['tmux', 'send-keys', '-t', 'shared', cmd, 'Enter'])` for tmux interaction | Immediately — TTYSession and tmux are completely orthogonal |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Sending user-supplied text directly to `tmux send-keys` without sanitization | Shell injection: user prompt "foo; rm -rf /" becomes a shell command | Wrap user-supplied content in a single-use heredoc or write it to a temp file first; never pass raw user text as a `send-keys` argument |
| Agent-visible scratch tmux sessions accessible from the shared terminal | Agent's private commands appear in user-visible terminal | Use separate sessions (not windows of `shared`) and document that `shared` is user-facing only |
| `ANTHROPIC_API_KEY` visible in `tmux` pane history | Key appears in `tmux capture-pane` output and Agent Zero chat logs | Set env vars before launching opencode in the same `send-keys` chain but mask the key in any captured output before logging |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Agent injects commands into the shared terminal while the user is typing | User's in-progress input is clobbered; their partially-typed command executes unexpectedly | Detect user activity before injecting: capture screen, wait 1s, capture again — if content changed without agent intervention, abort injection and wait |
| Agent leaves interactive CLI running in shared terminal after task completes | User opens the terminal and sees a foreign CLI they didn't start | Always clean up: send Ctrl+D or `exit` when done; verify the CLI exited before returning |
| Agent sends many rapid commands to shared terminal during debugging | User's terminal becomes a blur of injected text; unusable | Rate-limit agent injections; batch multi-step interactions with visible progress in Agent Zero's own UI rather than raw terminal injection |
| Screen-stability detection fails during progress spinners | Spinner keeps changing screen → stability never detected → timeout fires → agent proceeds with incomplete state | Detect spinner patterns in captured output; if spinner is the only change between captures, treat as stable |

---

## "Looks Done But Isn't" Checklist

- [ ] **tmux send-keys:** Command was sent — verify `capture-pane` eventually shows the command's output (not just the command echoed at the prompt)
- [ ] **Prompt detection:** Shell prompt pattern matched — verify it is the *shell's* prompt, not a CLI sub-prompt (Python `>>>`, opencode `>`) that happens to match
- [ ] **ANSI stripping:** `re.sub` was applied — verify by asserting `\x1b[` does not appear in the result string
- [ ] **Shared session safety:** tmux_tool sends to `shared` — verify no sentinel text appears by reviewing the next capture-pane output
- [ ] **OpenCode run completion:** Output stopped — verify the `opencode` process has actually exited via `pgrep opencode` or process.poll(), not just that output stopped
- [ ] **Interactive CLI startup:** `opencode` was launched in the shared terminal — verify `capture-pane` shows OpenCode's ready state (TUI rendered or `run` mode cursor at input), not a shell error message
- [ ] **Session isolation:** tmux_tool routes to the correct session — verify the target session name matches `tmux ls` output and is the intended session, not an alias match

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| capture-pane race / stale output | LOW | Add minimum settle wait + stability polling loop; no architecture change |
| Sentinel leaked into shared terminal | MEDIUM | Kill and restart the interactive CLI; scroll back to audit damage; add the no-sentinel rule to code review checklist |
| opencode run hang (v0.15+ bug) | LOW | `process.terminate()` after timeout; pin to working version; switch to `opencode serve` API mode |
| Partial input buffer contamination | LOW | Send Ctrl+C + Ctrl+U before each new injection; treat shared terminal as always-dirty on resume |
| Session name collision | LOW | `tmux kill-session -t <name>` for agent-private sessions; `has-session` check at every creation point |
| code_execution_tool / tmux environment confusion | MEDIUM | Document the boundary; grep codebase for any code that attempts cross-context state setup and refactor |
| Shell not ready after session create | LOW | Replace fixed sleeps with poll-until-stable-prompt pattern; 2-3 second total wait cap |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| capture-pane reads stale output | TERM-04, TERM-05 | Two consecutive identical captures + prompt match before returning |
| Prompt detection false positives from CLI output | TERM-05, CLI-03 | Test with OpenCode TUI running: false-positive rate = 0 |
| ANSI/OSC sequences in capture-pane output | TERM-04, CLI-02 | Captured text asserts no `\x1b[` after stripping pass |
| Sentinel injection into shared terminal | TERM-01 | Review + integration test: no sentinel text appears in shared terminal during any agent operation |
| Session name collision | TERM-01, CLI-01 | `tmux ls` shows correct sessions; `shared` is never recreated or destroyed |
| code_execution_tool / tmux context boundary | TERM-01 (docs), CLI-06 (skill) | Skill documents the isolation; no cross-context state assumptions in implementation |
| opencode run hang (version-specific) | CLI-05 | `opencode --version` verified; process exits cleanly within timeout |
| Interactive CLI buffer contamination | CLI-02, CLI-04 | Ctrl+U pre-injection confirmed; garbled command test = 0 occurrences |
| Shell not ready race after session create | TERM-01, CLI-01 | Fixed sleeps replaced with poll-and-wait; stress test on slow machine |
| User activity collision in shared terminal | CLI-01 through CLI-04 (docs) | Document the user-activity check; no agent injection during active user typing |

---

## Sources

- Direct codebase analysis: `python/tools/code_execution_tool.py`, `python/helpers/tty_session.py`, `python/helpers/shell_local.py`, `apps/shared-terminal/startup.sh`, `usr/skills/claude-cli/SKILL.md`
- tmux upstream: [race condition with shell initialization (claude-code #23513)](https://github.com/anthropics/claude-code/issues/23513), [capture-pane timing (tmux #1412)](https://github.com/tmux/tmux/issues/1412), [ANSI sequences in tmux (tmux #2254)](https://github.com/tmux/tmux/issues/2254), [new-session -A with -d (tmux #2211)](https://github.com/tmux/tmux/issues/2211)
- OpenCode issue tracker: [`opencode run` hang on v0.15+ (#3213)](https://github.com/sst/opencode/issues/3213), [TUI exits but process hangs (#1717)](https://github.com/sst/opencode/issues/1717), [`opencode run` hangs on API errors (#8203)](https://github.com/anomalyco/opencode/issues/8203), [subprocess.Popen hang with opencode (#11891)](https://github.com/anomalyco/opencode/issues/11891)
- OpenCode architecture: server-centric TUI (zig+solidjs OpenTUI in v1.0 rewrite); `opencode serve` HTTP API mode for programmatic use
- libtmux documentation: capture_pane API, escape_sequences parameter behavior — MEDIUM confidence on exact flag behavior
- General PTY/tmux automation patterns: HIGH confidence from training knowledge

---
*Pitfalls research for: tmux-based terminal orchestration + interactive CLI control (v1.2 Terminal Orchestration milestone)*
*Researched: 2026-02-25*
