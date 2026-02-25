# Project Research Summary

**Project:** Agent Zero Fork — v1.2 Terminal Orchestration Milestone
**Domain:** tmux-based terminal interaction + interactive CLI orchestration in Python/FastAPI
**Researched:** 2026-02-25
**Confidence:** HIGH

## Executive Summary

The v1.2 milestone adds a critical capability the existing tool set cannot provide: Agent Zero interacting with the shared terminal and interactive CLI tools (starting with OpenCode) as a human operator would — type commands, observe output, send special keys, detect readiness, and execute multi-turn conversations. The existing `terminal_agent.py` covers only fire-and-forget shell commands with sentinel-based completion detection. It is fundamentally incompatible with interactive CLIs: sentinel injection (`echo MARKER:$?`) would be fed as keyboard input to any running interactive program, corrupting its state and appearing visibly to the human user in the shared browser terminal. The solution is a new `tmux_tool` Python Tool class, a new `opencode_cli.py` helper mirroring the existing `ClaudeSession` pattern, and a `cli-orchestration/SKILL.md` to make patterns reusable across agent sessions.

The recommended approach requires zero new Python dependencies. All tmux interaction uses `asyncio.create_subprocess_exec` (stdlib) to invoke `tmux send-keys`, `tmux capture-pane`, and `tmux list-sessions` as subprocesses — the same pattern used throughout the codebase. OpenCode is operated via its non-interactive `opencode run <prompt>` mode first (subprocess exit signals completion, mirrors `claude --print` exactly), with TUI mode deferred until session-memory limitations force it. Three implementation contracts are non-negotiable: ANSI stripping before any capture-pane parsing, dual-strategy readiness detection (prompt pattern matching + idle timeout fallback), and an absolute no-sentinel-in-shared-terminal rule.

The highest risk in this milestone is not the tmux plumbing — that is well-understood and already partially implemented in `terminal_agent.py` — but OpenCode-specific behavior. The `opencode run` command hangs indefinitely on versions 0.15.0+ due to a confirmed server lifecycle regression, and non-interactive session memory (`--continue`, `--session`) has a documented reliability issue. Phase 3 of the roadmap must begin with empirical observation of the installed OpenCode binary to capture its exact prompt patterns, startup time, and response boundaries before any detection logic is written.

## Key Findings

### Recommended Stack

The v1.2 stack adds no new Python packages to the existing codebase. All tmux orchestration uses `asyncio.create_subprocess_exec` (stdlib) to invoke tmux subcommands directly. `libtmux` was explicitly evaluated and rejected: it is a synchronous-only library wrapping the exact 2-line subprocess calls this project needs, adds 50KB+ of dependency overhead, and has a version mismatch between the pip-resolved package (0.46.2) and the PyPI latest (0.53.1) that introduces API drift risk. The only addition to `requirements.txt` is `websocket-client>=1.9.0` for synchronous CDP in skill snippets — this is a carry-over from v1.1, not new for v1.2.

**Core technologies:**
- `asyncio.create_subprocess_exec` (stdlib): drive all tmux commands — zero new dependencies, already used throughout the codebase
- `tmux` (system binary, already in Docker): terminal multiplexer; the `shared` session is pre-created by `apps/shared-terminal/startup.sh`
- `opencode` (system binary, requires separate install): OpenCode AI coding agent; use `opencode run <prompt>` for non-interactive scripting; verify version before building wrapper
- `re` (stdlib): ANSI/OSC stripping and prompt pattern detection against `capture-pane` output
- `TTYSession` (existing `python/helpers/tty_session.py`): NOT used for the shared terminal — it creates isolated PTY processes that are invisible to the user and not connected to the tmux session

**Critical exclusions:**
- Do not use `libtmux`: synchronous-only, version drift risk, wrapper for 2-line subprocess calls
- Do not use `TTYSession` or `code_execution_tool` for shared terminal interaction: completely isolated execution contexts, user-invisible
- Do not use `playwright` or `browser_agent` for OpenCode: OpenCode is a terminal TUI, not a browser application
- Do not use `pexpect`: adds a dependency duplicating functionality that `TTYSession` and the tmux approach already provide

### Expected Features

Full details: `.planning/research/FEATURES.md`

**Must have (table stakes — all P1):**
- TERM-01: Send text + Enter to named tmux pane — the foundational action; everything depends on it
- TERM-02: Send text without Enter (literal partial input) — required for inline prompts (`y/N`, single-character responses)
- TERM-03: Send special keys (Ctrl+C, Ctrl+D, Tab, Escape, arrows) — required for interrupt and exit sequences
- TERM-04: Capture current pane screen content (`capture-pane -p`) — the agent's only way to observe terminal state
- TERM-05: Detect terminal readiness (prompt pattern matching + idle timeout dual strategy) — prevents blind injection while the CLI is still processing
- CLI-01: Start an interactive CLI in shared terminal and wait for its initial ready prompt
- CLI-02: Send prompts to a running interactive CLI and read its responses (multi-turn loop)
- CLI-03: Detect when the CLI has finished responding — the highest-complexity requirement
- CLI-04: Interrupt or exit an interactive CLI cleanly — prevents orphan processes in the user's terminal
- CLI-06: `usr/skills/cli-orchestration/SKILL.md` — documents all validated patterns for agent consumption
- ANSI stripping utility — strictly required before TERM-05 can function; treat as P1 in implementation order

**Should have (differentiators — P2):**
- CLI-05: Pre-built `OpenCodeSession` wrapper in `python/helpers/opencode_cli.py` — mirrors `ClaudeSession` interface from v1.1; hides tmux plumbing from skill code; provides clean `.start()` / `.send(prompt)` / `.exit()` interface
- Pane-specific targeting beyond `shared:0.0` — enables parallel CLI sessions in different panes

**Defer (v2+):**
- TUI-mode OpenCode interaction (send-keys to TUI) — only if `opencode run` session memory proves unreliable; complexity is in ANSI-aware input-field detection
- MCP-based tmux control (structured typed APIs over raw subprocess)
- OpenCode streaming JSON output (`opencode run -f json`) piped in real-time
- Other interactive CLI wrappers (aider, Codex CLI, custom REPLs)

### Architecture Approach

The architecture adds four new files with zero changes to existing files. `python/tools/tmux_tool.py` is a Tool class exposing four subcommand actions: `send`, `keys`, `read`, `wait_ready`. `prompts/agent.system.tool.tmux.md` auto-registers it in the agent's system prompt — the tools system auto-discovers all `agent.system.tool.*.md` files, so no other registration step is needed. `python/helpers/opencode_cli.py` is a Python helper (not a Tool class) providing `OpenCodeSession` with `.start()`, `.send(prompt)`, `.exit()` — callable from `code_execution_tool runtime=python` skill code. `usr/skills/cli-orchestration/SKILL.md` documents the Read-Detect-Write-Verify cycle for any interactive CLI.

The critical isolation boundary: `code_execution_tool` sessions and the shared tmux session are completely separate shell processes with no shared state. Environment variables, working directory, and activated virtualenvs set in one context are invisible to the other. This boundary must be documented explicitly in the tmux_tool docstring and the SKILL.md.

**Major components:**
1. `tmux_tool.py` (NEW Tool) — primitive `send` / `keys` / `read` / `wait_ready` interface targeting the `shared` tmux session; coexists with `terminal_agent.py` without conflict
2. `opencode_cli.py` (NEW helper) — `OpenCodeSession` class mirroring `ClaudeSession` from `claude_cli.py`; uses tmux subprocess calls internally; not a Tool class
3. `cli-orchestration/SKILL.md` (NEW skill) — Read-Detect-Write-Verify cycle, tmux_tool action reference, per-CLI prompt/exit patterns, environment isolation warning
4. `terminal_agent.py` (UNCHANGED) — single-shot sentinel commands remain for user-visible fire-and-forget operations; the two tools coexist by targeting the same pane with different detection strategies
5. `apps/shared-terminal/startup.sh` (UNCHANGED) — pre-creates the `shared` session; already correct

### Critical Pitfalls

Full details: `.planning/research/PITFALLS.md`

1. **capture-pane reads stale output** — `tmux capture-pane` reads the display buffer, not process state. Called immediately after `send-keys`, it returns the screen as it was before the new command began. Avoidance: minimum 200ms settle after `send-keys`, then poll at 300–500ms intervals until two consecutive captures are identical AND the last lines match a prompt pattern or idle timeout fires.

2. **Sentinel injection into the shared terminal is forbidden** — The existing sentinel pattern (`echo MARKER:$?`) must never be used in the `shared` session. The shared session is visible to the human user via ttyd in the browser; sentinel text appears in the UI and corrupts any running interactive program's input buffer. The tmux_tool uses stability polling and prompt matching exclusively.

3. **ANSI/OSC sequences corrupt capture-pane text** — Interactive CLIs emit heavy ANSI: cursor movement (`\x1b[A`, `\x1b[2K`), spinners, OSC title sequences. Even after tmux's basic stripping, residual sequences contaminate text. Apply comprehensive regex before any parsing: `re.sub(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07)', '', text)`.

4. **`opencode run` hangs on v0.15+ (confirmed regression)** — On OpenCode 0.15.0 through at least 0.15.2, the process completes output but never exits (confirmed: GitHub sst/opencode issue #3213). Any wrapper expecting process exit as the done signal hangs indefinitely. Mitigation: check `opencode --version`, apply a hard `subprocess.run(timeout=...)` with `process.terminate()` on expiry, or use `opencode serve` HTTP API mode which does not have this bug.

5. **Interactive CLI input buffer contamination** — If the agent interrupts a CLI mid-operation, the line-editing buffer may contain partial text. The next injection appends to the partial text, corrupting the command. Protocol: before every new injection, send `Ctrl+C` (cancel current operation), wait for screen stability, send `Ctrl+U` (clear line buffer), then verify the captured screen shows an empty prompt line before injecting new text.

## Implications for Roadmap

The architecture's build-order dependency chain (specified consistently in both ARCHITECTURE.md and FEATURES.md) and the pitfall-to-phase mapping from PITFALLS.md together fully determine the phase structure. There is one correct ordering; it cannot be safely rearranged.

### Phase 1: tmux Primitive Infrastructure
**Rationale:** Every subsequent phase depends on `send`, `keys`, and `read` working correctly. This phase has no dependency on any CLI-specific behavior and can be verified entirely using a plain bash shell in the shared terminal. It is pure tmux subprocess wiring with well-understood patterns.
**Delivers:** `python/tools/tmux_tool.py` with `send`, `keys`, `read` actions; `prompts/agent.system.tool.tmux.md` for auto-registration; agent can type text, send special keys (Ctrl+C, Escape, Tab, arrows), and capture pane content
**Addresses:** TERM-01, TERM-02, TERM-03, TERM-04
**Avoids:** Sentinel injection pitfall (establish the no-sentinel rule in code before any interactive CLI work); session name collision pitfall (add `tmux has-session` guard at construction time)

### Phase 2: Readiness Detection (`wait_ready`)
**Rationale:** ANSI stripping and dual-strategy readiness detection (prompt pattern + idle timeout) are the highest-complexity features of the milestone. They must be correct before any CLI interaction begins. Isolating this phase allows the detection logic to be validated against real pane output — including the false-positive problem where CLI program output matches shell prompt patterns — before that logic is embedded in multi-turn session code.
**Delivers:** `tmux_tool:wait_ready` action; ANSI stripping utility function; prompt pattern library; confirmed zero false-positive rate from CLI sub-prompts; idle timeout calibrated for AI CLI response times (10s default minimum)
**Addresses:** TERM-05; ANSI stripping (prerequisite for TERM-05 and CLI-02)
**Avoids:** Prompt detection false positives pitfall; capture-pane stale output pitfall; high-frequency polling overhead pitfall

### Phase 3: Interactive CLI Session Lifecycle (Empirical)
**Rationale:** With primitives proven in Phase 1 and readiness detection validated in Phase 2, the CLI session lifecycle (start, send, read, interrupt, exit) can be implemented empirically. This is the empirical validation step: OpenCode must be run manually in the shared terminal so its exact prompt pattern bytes, startup time, response duration, and exit behavior can be observed before any detection regex is written. Writing detection logic from documentation alone would embed unverified assumptions.
**Delivers:** CLI-01 through CLI-04 working via tmux_tool; empirically verified OpenCode prompt patterns and startup time; confirmed exit sequences (`/quit`, Ctrl+C, Ctrl+D); version check for `opencode run` hang regression
**Uses:** All stack elements from Phases 1+2; OpenCode binary in Docker
**Avoids:** Input buffer contamination pitfall (Ctrl+U pre-injection protocol); shell initialization race condition (poll-until-stable-prompt after CLI exit); `opencode run` hang pitfall (version check + hard timeout + terminate on expiry)

### Phase 4: OpenCode Session Wrapper
**Rationale:** Only after Phase 3 validates the empirical prompt patterns can the `OpenCodeSession` wrapper be written with confidence. The wrapper encodes those patterns — writing it before Phase 3 would embed untested assumptions. This is the same build discipline used in v1.1 where `claude_cli.py`'s `ClaudeSession` was written after single-turn patterns were confirmed working.
**Delivers:** `python/helpers/opencode_cli.py` with `OpenCodeSession` class; clean `.start()` / `.send(prompt)` / `.exit()` interface callable from `code_execution_tool runtime=python`; integration with skill-code patterns
**Implements:** CLI-05; ClaudeSession-mirroring architecture pattern

### Phase 5: CLI Orchestration Skill Documentation
**Rationale:** Skill documents must reflect only confirmed, validated behavior. Writing the SKILL.md before Phases 1–4 complete would risk embedding aspirational patterns that fail at runtime — creating persistent knowledge-base contamination that agents carry across sessions. This is an absolute policy, not a suggestion.
**Delivers:** `usr/skills/cli-orchestration/SKILL.md` documenting: tmux_tool action reference, Read-Detect-Write-Verify cycle, OpenCode-specific prompt/exit patterns, environment isolation warning, per-CLI reference table, session continuity guidance
**Addresses:** CLI-06
**Avoids:** Skill embedding unverified assumptions; knowledge contamination across sessions

### Phase Ordering Rationale

- Phases 1-2 are pure infrastructure and can be tested against a plain bash shell — no OpenCode dependency
- Phase 3 is the empirical step that cannot be shortcut: OpenCode prompt format, startup time, and response boundaries must be observed on the actual binary running in Docker before any detection code is written
- Phase 4 must follow Phase 3 because the wrapper encodes empirically verified patterns, not documentation-derived ones
- Phase 5 is always last by policy: skill documents describe confirmed behavior only
- Zero changes to existing files eliminates regression risk entirely; all phases create new files only

### Research Flags

Phases requiring empirical validation or deeper research before implementation:
- **Phase 3 (Interactive CLI Lifecycle):** HIGH research need — requires running OpenCode binary in Docker to observe exact prompt pattern bytes, startup time, and response boundary behavior before writing any detection regex. Additionally, must verify installed OpenCode version against the hang regression (v0.15+) and decide: pin to <0.15.0, apply hard timeout workaround, or use `opencode serve` HTTP mode. Recommend running `/gsd:research-phase` before planning Phase 3.
- **Phase 4 (OpenCode Wrapper):** MEDIUM research need — contingent on Phase 3 findings. If the hang regression is present and cannot be version-pinned, the wrapper architecture shifts from subprocess to HTTP client (`opencode serve`). This is a contingency path that needs a brief research spike if triggered.

Phases with standard patterns (skip research-phase):
- **Phase 1 (tmux Primitives):** Standard pattern — tmux subprocess calls are well-documented and the send-keys / capture-pane pattern is already used in `terminal_agent.py`. No unknowns.
- **Phase 2 (Readiness Detection):** Standard pattern — `code_execution_tool.py` already implements prompt-pattern + idle-timeout detection for PTY sessions. Port and adapt the approach; no new research needed.
- **Phase 5 (SKILL.md):** Documentation-only phase — follows established format from `usr/skills/claude-cli/SKILL.md`; no technical uncertainty once patterns are validated.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings verified against live codebase files, installed packages, and official docs. Only uncertainty: OpenCode `-p` flag exact syntax — verify with `opencode --help` on the installed binary. |
| Features | HIGH | Derived from live code inspection of `terminal_agent.py`, `code_execution_tool.py`, `tty_session.py`, `claude_cli.py`. Feature gaps confirmed by reading actual code capabilities, not assumed. |
| Architecture | HIGH | All findings from direct codebase inspection: tool dispatch chain, auto-discovery mechanism, session management, file paths confirmed against live files in the running project. |
| Pitfalls | HIGH | Critical pitfalls confirmed via live codebase analysis and upstream issue trackers (tmux #1412, #2254; OpenCode sst/opencode #3213, #11891, anomalyco/opencode #11891). The `opencode run` hang regression is confirmed as a documented, version-specific bug. |

**Overall confidence:** HIGH

### Gaps to Address

- **OpenCode installed version:** The single largest implementation risk. Research identifies a confirmed hang regression on OpenCode 0.15.0+. The installed version in Docker is unknown. Must run `opencode --version` at the start of Phase 3 planning and decide the mitigation strategy: pin version, apply hard timeout + terminate, or switch to `opencode serve` HTTP mode.
- **OpenCode exact prompt pattern bytes:** The OpenCode TUI ready-state indicator varies by version and theme. It must be observed on the actual installed binary in Docker — it cannot be reliably determined from documentation. Phase 3 empirical validation is mandatory before Phase 4 can begin.
- **OpenCode session memory reliability:** GitHub Issue #917 documents that `--continue` / `--session` flags for multi-turn non-interactive state are unreliable. If multi-turn sessions with OpenCode are required, test on the installed version before CLI-05 depends on session continuity. Fallback: embed prior context in each prompt.
- **`opencode serve` HTTP mode as contingency:** If the hang regression is present and version cannot be pinned, the Phase 4 architecture shifts to HTTP client calls against `opencode serve`. This requires a brief research spike on the HTTP API surface before implementation.

## Sources

### Primary (HIGH confidence)
- `python/tools/terminal_agent.py` — live codebase; `_TMUX_SESSION = "shared"` confirmed; sentinel pattern documented
- `python/tools/code_execution_tool.py` — live codebase; prompt patterns, idle timeout, session ID management confirmed
- `python/helpers/tty_session.py` — live codebase; PTY subprocess control; NOT connected to tmux sessions
- `python/helpers/claude_cli.py` — live codebase; `ClaudeSession` pattern that `opencode_cli.py` will mirror
- `python/helpers/subagents.py`, `agent.py`, `prompts/agent.system.tools.py` — live codebase; tool dispatch chain and auto-discovery mechanism confirmed
- `apps/shared-terminal/startup.sh` — live codebase; `shared` tmux session pre-creation confirmed
- `requirements.txt` — live codebase; `websocket-client` absent (needs adding); `psutil>=7.0.0` present
- `.planning/PROJECT.md` — TERM-01..05 and CLI-01..06 requirements confirmed

### Secondary (MEDIUM confidence)
- [OpenCode CLI docs](https://opencode.ai/docs/cli/) — `opencode run`, `-q`, `--continue`, `--session` flag behavior
- [OpenCode GitHub Issue #917 (sst/opencode)](https://github.com/sst/opencode/issues/917) — session memory unreliability in non-interactive mode
- [OpenCode GitHub Issue #11891 (anomalyco/opencode)](https://github.com/anomalyco/opencode/issues/11891) — subprocess.Popen hang with JSON output format
- [ForgeFlow project](https://github.com/Kingson4Wu/ForgeFlow) — validates ANSI-aware prompt detection approach for interactive CLI orchestration in tmux
- [Claude Code Agent Farm](https://github.com/Dicklesworthstone/claude_code_agent_farm) — `--idle-timeout` pattern for tmux-based agent orchestration
- [libtmux docs](https://libtmux.git-pull.com/) — blocking-only API confirmed; no async support; rejected for this project
- [tmux upstream issue #1412](https://github.com/tmux/tmux/issues/1412) — capture-pane timing behavior
- [tmux upstream issue #2254](https://github.com/tmux/tmux/issues/2254) — ANSI sequences in capture-pane output

### Tertiary (LOW confidence — validate against installed binary)
- [OpenCode GitHub Issue #3213 (sst/opencode)](https://github.com/sst/opencode/issues/3213) — `opencode run` hang on v0.15+ confirmed as regression; exact fixed version unknown; verify against installed binary with `opencode --version` before building any automation
- OpenCode `-p` flag status — referenced in community discussions (anomalyco/opencode issue #10411); verify flag name and behavior with `opencode --help` before writing `opencode_session()`

---
*Research completed: 2026-02-25*
*Ready for roadmap: yes*
