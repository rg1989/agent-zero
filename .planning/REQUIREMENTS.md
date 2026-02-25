# Requirements: Agent Zero Fork

**Core Value:** Agent Zero can build, run, and persist web applications directly within its own UI

---

## v1.2 Requirements

Requirements for the Terminal Orchestration milestone. Each maps to roadmap phases 11–15.

### Terminal Tool

- [x] **TERM-01**: Agent Zero can send text + Enter to a named tmux pane in the shared terminal
- [x] **TERM-02**: Agent Zero can send text without Enter to a named tmux pane (partial input for inline prompts like `y/N`)
- [x] **TERM-03**: Agent Zero can send special keys to a named tmux pane (Ctrl+C, Ctrl+D, Tab, Escape, arrow keys)
- [x] **TERM-04**: Agent Zero can capture and read current terminal screen content from a tmux pane
- [x] **TERM-05**: Agent Zero can detect when a terminal pane is ready for input using prompt pattern matching with idle timeout fallback

### CLI Orchestration

- [ ] **CLI-01**: Agent Zero can start an interactive CLI tool in the shared terminal and wait for its initial ready prompt
- [ ] **CLI-02**: Agent Zero can send a prompt to a running interactive CLI and read its response
- [ ] **CLI-03**: Agent Zero can detect when an interactive CLI has finished responding and is ready for next input
- [ ] **CLI-04**: Agent Zero can interrupt or exit an interactive CLI session cleanly (Ctrl+C, Ctrl+D, or tool-specific exit command)
- [ ] **CLI-05**: Agent Zero can use a pre-built `OpenCodeSession` wrapper with `.start()` / `.send(prompt)` / `.exit()` interface, mirroring `ClaudeSession`
- [ ] **CLI-06**: Agent Zero can follow documented orchestration patterns for any interactive CLI via `usr/skills/cli-orchestration/SKILL.md`

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Apps

- **APPS-01**: Background removal app (`apps/bg-remover/`) registered and accessible at `/bg-remover/` with auto-start
- **APPS-02**: App auto-discovery — Agent Zero registers new apps found in `apps/` directory without manual `register.py`

### UI

- **UI-01**: Preferences panel improvements (in-progress webui changes)
- **UI-02**: Sidebar and quick-actions UI polish

### CLI Orchestration (future)

- **CLI-EXT-01**: TUI-mode OpenCode interaction (tmux send-keys to TUI) — only if `opencode run` session memory proves unreliable
- **CLI-EXT-02**: Additional CLI wrappers (Aider, Codex CLI, custom REPLs)
- **CLI-EXT-03**: Pane-specific targeting beyond `shared:0.0` for parallel CLI sessions

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Modify `code_execution_tool` | Sentinel pattern is correct for shell commands; interactive CLIs need separate tool |
| `libtmux` dependency | Blocking-only API, version drift risk, just wraps 2-line subprocess calls |
| `pexpect` dependency | Duplicates TTYSession + tmux approach; unnecessary dependency |
| `TTYSession` for shared terminal | Creates isolated PTY subprocess — not connected to user-visible tmux session |
| Playwright for shared browser | Explicitly banned — spawns separate Chromium, creates persistent UI loader |
| Upstream Agent Zero core changes | Fork-only — upstream changes pulled separately |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TERM-01 | Phase 11 | Complete |
| TERM-02 | Phase 11 | Complete |
| TERM-03 | Phase 11 | Complete |
| TERM-04 | Phase 11 | Complete |
| TERM-05 | Phase 12 | Complete |
| CLI-01 | Phase 13 | Pending |
| CLI-02 | Phase 13 | Pending |
| CLI-03 | Phase 13 | Pending |
| CLI-04 | Phase 13 | Pending |
| CLI-05 | Phase 14 | Pending |
| CLI-06 | Phase 15 | Pending |

**Coverage:**
- v1.2 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---

## Completed: v1.1 Requirements

### Browser Control

- [x] **BROWSER-01**: Agent Zero navigates to a URL using CDP `Page.navigate` followed by a `document.readyState` poll
- [x] **BROWSER-02**: Agent Zero takes a screenshot via CDP before every browser interaction to observe current state
- [x] **BROWSER-03**: Agent Zero verifies navigation succeeded by checking current URL and page title after navigate-and-wait
- [x] **BROWSER-04**: Shared browser Chromium startup replaces fragile `sleep 2` with a CDP WebSocket health-check poll
- [x] **BROWSER-05**: Agent Zero uses a consistent Observe → Act → Verify workflow for all browser interactions

### Claude CLI Control

- [x] **CLAUDE-01**: Agent Zero can launch the `claude` CLI by unsetting `CLAUDECODE` in the subprocess environment
- [x] **CLAUDE-02**: Agent Zero can send a prompt to `claude` using `--print` / `-p` mode and receive the complete response
- [x] **CLAUDE-03**: Agent Zero can detect when a `claude --print` invocation has finished and extract the response text
- [x] **CLAUDE-04**: Agent Zero can run a multi-turn `claude` conversation using `--print --resume UUID` with process returncode as the completion signal
- [x] **CLAUDE-05**: A dedicated `claude-cli` skill (`usr/skills/claude-cli/SKILL.md`) documents all validated invocation patterns

---
*v1.2 requirements defined: 2026-02-25*
*v1.1 requirements completed: 2026-02-25*
*Last updated: 2026-02-25 after milestone v1.2 start*
