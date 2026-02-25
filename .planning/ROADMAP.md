# Roadmap: Agent Zero Enhanced Fork

## Milestones

- ✅ **v1.0 Foundation & Apps System** - Phases 1-5 (shipped 2026-02-25)
- ✅ **v1.1 Reliability** - Phases 6-10 (shipped 2026-02-25)
- 🚧 **v1.2 Terminal Orchestration** - Phases 11-15 (in progress)

## Phases

<details>
<summary>✅ v1.0 Foundation & Apps System (Phases 1-5) - SHIPPED 2026-02-25</summary>

| Phase | Name | Status |
|-------|------|--------|
| 1 | Apps System Core | Complete |
| 2 | Core Built-in Apps | Complete |
| 3 | GSD Skill Pack | Complete |
| 4 | Neon UI + UX | Complete |
| 5 | Scaffolding + Skills | Complete |

</details>

<details>
<summary>✅ v1.1 Reliability (Phases 6-10) - SHIPPED 2026-02-25</summary>

| Phase | Name | Status |
|-------|------|--------|
| 6 | CDP Startup Health-Check | Complete |
| 7 | Browser Navigate-with-Verification | Complete |
| 8 | Claude CLI Single-Turn + Env Fix | Complete |
| 9 | Claude CLI Multi-Turn Sessions | Complete |
| 10 | Claude CLI Skill Documentation | Complete |

</details>

### 🚧 v1.2 Terminal Orchestration (In Progress)

**Milestone Goal:** Agent Zero can interact with the shared terminal and interactive CLIs as a human would — type, read screen, send special keys, detect readiness — enabling orchestration of any CLI agent (starting with OpenCode).

- [x] **Phase 11: tmux Primitive Infrastructure** - New `tmux_tool` Python Tool with `send`, `keys`, `read`, and `wait_ready` actions targeting the shared tmux session; Docker bind mounts and copy_A0.sh fixed for live-reload deployment (completed 2026-02-25)
- [x] **Phase 12: Readiness Detection** - ANSI stripping utility and dual-strategy `wait_ready` (prompt pattern + idle timeout) validated against real pane output (completed 2026-02-25)
- [ ] **Phase 13: Interactive CLI Session Lifecycle** - Empirical observation of OpenCode in Docker; CLI-01..04 implemented with verified prompt patterns and exit sequences
- [ ] **Phase 14: OpenCode Session Wrapper** - `OpenCodeSession` class in `python/helpers/opencode_cli.py` with clean `.start()` / `.send(prompt)` / `.exit()` interface
- [ ] **Phase 15: CLI Orchestration Skill Documentation** - `usr/skills/cli-orchestration/SKILL.md` documenting the Read-Detect-Write-Verify cycle and all confirmed patterns

## Phase Details

### Phase 11: tmux Primitive Infrastructure
**Goal**: Agent Zero can type text, send special keys, and read the screen of the shared tmux terminal — providing the foundational primitives every subsequent phase depends on
**Depends on**: Nothing (new files only; coexists with terminal_agent.py without conflict)
**Requirements**: TERM-01, TERM-02, TERM-03, TERM-04
**Success Criteria** (what must be TRUE):
  1. Agent Zero sends a command + Enter to the shared tmux pane and the command executes visibly in the user's browser terminal
  2. Agent Zero sends text without Enter to a named tmux pane, and the text appears as partial input at the prompt (e.g., responding to a `y/N` inline prompt)
  3. Agent Zero sends special keys (Ctrl+C, Ctrl+D, Tab, Escape, arrow keys) to the shared tmux pane and the terminal responds correctly — interrupts, completions, and cursor movements work as a human keyboard would produce them
  4. Agent Zero captures the current pane screen content and the returned text contains the visible terminal output, free of tmux internal artifacts
  5. No sentinel text (`echo MARKER:$?` or similar) is ever written into the shared session — capture-pane and stability polling are the only observation mechanisms
**Plans:** 2/2 plans complete

Plans:
- [x] 11-01-PLAN.md — Create python/tools/tmux_tool.py with send/keys/read actions and prompts/agent.system.tool.tmux.md for auto-registration
- [x] 11-02-PLAN.md — Fix Docker deployment gap: add python/ and prompts/ bind mounts to docker-compose.yml; fix copy_A0.sh sync-newer logic

### Phase 12: Readiness Detection
**Goal**: Agent Zero can reliably determine when the terminal is ready for the next input — preventing blind injection while a command is still running — using prompt pattern matching with idle timeout fallback
**Depends on**: Phase 11
**Requirements**: TERM-05
**Success Criteria** (what must be TRUE):
  1. Agent Zero calls `wait_ready` after sending a command and does not inject new input until the pane is stable — no corruption of a running process's input buffer
  2. ANSI escape sequences (cursor movement, color codes, OSC title sequences) are stripped from captured pane text before any pattern matching — prompt detection does not misfire on ANSI artifacts
  3. When a prompt pattern is present (e.g., `$ ` at the end of stable output), `wait_ready` returns promptly without waiting for the full idle timeout
  4. When no prompt pattern is present after a configurable idle timeout (default 10 seconds minimum for AI CLI response times), `wait_ready` returns anyway rather than hanging indefinitely
  5. A false-positive stress test confirms that CLI sub-prompts (e.g., `Continue? [y/N]`) do not trigger a false "ready" signal when the agent has not yet responded
**Plans:** 1/1 plans complete

Plans:
- [ ] 12-01-PLAN.md — Add _wait_ready() to TmuxTool with dual-strategy detection (prompt pattern + stability) and update agent prompt doc

### Phase 13: Interactive CLI Session Lifecycle
**Goal**: Agent Zero can start an interactive CLI in the shared terminal, send it prompts, read its responses, and exit cleanly — with all behavior derived from empirical observation of the actual OpenCode binary in Docker, not from documentation
**Depends on**: Phase 12
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. Agent Zero starts OpenCode (or any interactive CLI) in the shared terminal pane and waits for its initial ready prompt before sending any input — startup is not treated as complete until the ready state is confirmed on screen
  2. Agent Zero sends a multi-turn prompt sequence to a running interactive CLI session; each response is captured completely and reflects the CLI's processing of the prior input
  3. Agent Zero detects when an interactive CLI has finished responding and the terminal is ready for next input — the detection uses empirically observed prompt patterns from the actual installed binary, not assumed patterns
  4. Agent Zero exits an interactive CLI cleanly using the appropriate exit sequence (`/quit`, Ctrl+C, Ctrl+D, or tool-specific exit command), and the shared terminal returns to a normal shell prompt without orphaned processes
**Plans:** 1/2 plans executed

Plans:
- [ ] 13-01-PLAN.md — Install OpenCode in Docker, configure Ollama connectivity, run structured observation session to capture exact TUI prompt patterns, startup time, exit sequence; produce 13-01-OBSERVATION.md
- [ ] 13-02-PLAN.md — Encode empirical findings: OPENCODE_PROMPT_PATTERN constant in tmux_tool.py, permanent install in install_additional.sh, lifecycle doc in agent prompt, end-to-end CLI-01..04 validation

### Phase 14: OpenCode Session Wrapper
**Goal**: Agent Zero can use a pre-built `OpenCodeSession` class with a clean `.start()` / `.send(prompt)` / `.exit()` interface — hiding tmux plumbing from skill code and mirroring the `ClaudeSession` pattern from v1.1
**Depends on**: Phase 13
**Requirements**: CLI-05
**Success Criteria** (what must be TRUE):
  1. Agent Zero skill code can start an OpenCode session, send a prompt, receive the response, and exit using only `.start()`, `.send()`, and `.exit()` — without any direct tmux subcommand calls in the skill code
  2. `OpenCodeSession` correctly applies the empirically verified OpenCode prompt patterns and exit sequences from Phase 13 — it encodes observed reality, not documentation assumptions
  3. If the OpenCode version is affected by the `opencode run` hang regression (v0.15+), the wrapper applies a hard timeout with `process.terminate()` on expiry and surfaces a clear error rather than hanging indefinitely
**Plans**: TBD

Plans:
- [ ] 14-01-PLAN.md — Create python/helpers/opencode_cli.py with OpenCodeSession class; validate against installed OpenCode binary

### Phase 15: CLI Orchestration Skill Documentation
**Goal**: A skill document captures every validated CLI orchestration pattern — from tmux primitives through the Read-Detect-Write-Verify cycle to OpenCode-specific behavior — so any Agent Zero session can orchestrate CLI tools correctly without re-discovering these patterns
**Depends on**: Phase 14
**Requirements**: CLI-06
**Success Criteria** (what must be TRUE):
  1. `usr/skills/cli-orchestration/SKILL.md` exists and documents the tmux_tool action reference (`send`, `keys`, `read`, `wait_ready`) with the correct invocation syntax for each action
  2. The skill documents the Read-Detect-Write-Verify cycle as the required interaction pattern and includes the environment isolation warning (code_execution_tool and the shared tmux session are separate, non-sharing execution contexts)
  3. The skill includes OpenCode-specific patterns: confirmed prompt patterns, startup sequence, exit command, and the version hang regression workaround — all derived from Phase 13 empirical findings
  4. The skill follows the established format of `usr/skills/claude-cli/SKILL.md` and can be consumed by an agent session without ambiguity
**Plans**: TBD

Plans:
- [ ] 15-01-PLAN.md — Create usr/skills/cli-orchestration/SKILL.md documenting all confirmed patterns from Phases 11-14

## Progress

**Execution Order:**
Phases 11 → 12 → 13 → 14 → 15 (strictly sequential — each phase depends on the previous)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Apps System Core | v1.0 | - | Complete | 2026-02-25 |
| 2. Core Built-in Apps | v1.0 | - | Complete | 2026-02-25 |
| 3. GSD Skill Pack | v1.0 | - | Complete | 2026-02-25 |
| 4. Neon UI + UX | v1.0 | - | Complete | 2026-02-25 |
| 5. Scaffolding + Skills | v1.0 | - | Complete | 2026-02-25 |
| 6. CDP Startup Health-Check | v1.1 | 1/1 | Complete | 2026-02-25 |
| 7. Browser Navigate-with-Verification | v1.1 | 1/1 | Complete | 2026-02-25 |
| 8. Claude CLI Single-Turn + Env Fix | v1.1 | 1/1 | Complete | 2026-02-25 |
| 9. Claude CLI Multi-Turn Sessions | v1.1 | 1/1 | Complete | 2026-02-25 |
| 10. Claude CLI Skill Documentation | v1.1 | 1/1 | Complete | 2026-02-25 |
| 11. tmux Primitive Infrastructure | 2/2 | Complete    | 2026-02-25 | 2026-02-25 |
| 12. Readiness Detection | 1/1 | Complete    | 2026-02-25 | - |
| 13. Interactive CLI Session Lifecycle | 1/2 | In Progress|  | - |
| 14. OpenCode Session Wrapper | v1.2 | 0/1 | Not started | - |
| 15. CLI Orchestration Skill Documentation | v1.2 | 0/1 | Not started | - |
