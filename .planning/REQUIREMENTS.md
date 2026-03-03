# Requirements: Agent Zero Fork

**Core Value:** Agent Zero can build, run, and persist web applications directly within its own UI

---

## v1.3 Requirements

Requirements for the App Builder milestone. Each maps to roadmap phases 16+.

### Skill Reliability

- [x] **SKILL-01**: Agent always recognizes app creation requests and routes to the web-app-builder skill — no ad-hoc Flask scripts outside the Apps System
- [x] **SKILL-02**: web-app-builder SKILL.md enforces a mandatory sequence: allocate port, copy template, customize code, register, start, verify — with no steps skippable
- [x] **SKILL-03**: App name is validated against reserved paths and naming rules before registration attempt
- [x] **SKILL-04**: After starting an app, the agent polls the app's port until it responds (HTTP 200) before declaring success to the user
- [ ] **SKILL-05**: Agent auto-selects the best template based on the user's request, tells the user which one was chosen, and allows override if asked

### Template Library

- [ ] **TMPL-01**: Real-time dashboard template exists with periodic data refresh and Chart.js or Plotly charts in a responsive grid layout
- [ ] **TMPL-02**: File/media tool template exists with drag-and-drop upload, file listing, download endpoints, and format conversion support
- [ ] **TMPL-03**: CRUD app template exists with SQLite database, model definition, and list/detail/create/edit/delete views
- [ ] **TMPL-04**: Utility/tool single-page app template exists as a minimal skeleton for calculators, viewers, text tools, and similar lightweight apps
- [ ] **TMPL-05**: Template catalog file lists all available templates with descriptions, use cases, and when to pick each one
- [ ] **TMPL-06**: _GUIDE.md decision tree updated to cover all new templates with clear selection criteria

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### App Management Enhancements

- **MGMT-01**: Health check daemon periodically verifies running apps are still responding
- **MGMT-02**: App logs are captured and viewable from the My Apps UI
- **MGMT-03**: App resource usage (CPU, memory) visible in the My Apps panel

### Advanced Templates

- **TMPL-07**: WebSocket chat/messaging template
- **TMPL-08**: Kanban/task board template
- **TMPL-09**: API testing/webhook receiver template

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

| Feature | Reason |
|---------|--------|
| App marketplace / sharing | Single-user system; no multi-user distribution needed |
| Custom domain routing | Docker/localhost deployment only |
| Database migration tooling | Templates use simple SQLite; no schema versioning needed for v1.3 |
| CI/CD for apps | Apps are quick prototypes, not production deployments |
| Modify `code_execution_tool` | Sentinel pattern is correct for shell commands; interactive CLIs need separate tool |
| Playwright for shared browser | Explicitly banned — spawns separate Chromium, creates persistent UI loader |
| Upstream Agent Zero core changes | Fork-only — upstream changes pulled separately |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SKILL-01 | Phase 16 | Complete |
| SKILL-02 | Phase 16 | Complete |
| SKILL-03 | Phase 16 | Complete |
| SKILL-04 | Phase 16 | Complete |
| SKILL-05 | Phase 18 | Pending |
| TMPL-01 | Phase 17 | Pending |
| TMPL-02 | Phase 17 | Pending |
| TMPL-03 | Phase 17 | Pending |
| TMPL-04 | Phase 17 | Pending |
| TMPL-05 | Phase 18 | Pending |
| TMPL-06 | Phase 18 | Pending |

**Coverage:**
- v1.3 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---

## Completed: v1.2 Requirements

### Terminal Tool

- [x] **TERM-01**: Agent Zero can send text + Enter to a named tmux pane in the shared terminal
- [x] **TERM-02**: Agent Zero can send text without Enter to a named tmux pane (partial input for inline prompts like `y/N`)
- [x] **TERM-03**: Agent Zero can send special keys to a named tmux pane (Ctrl+C, Ctrl+D, Tab, Escape, arrow keys)
- [x] **TERM-04**: Agent Zero can capture and read current terminal screen content from a tmux pane
- [x] **TERM-05**: Agent Zero can detect when a terminal pane is ready for input using prompt pattern matching with idle timeout fallback

### CLI Orchestration

- [x] **CLI-01**: Agent Zero can start an interactive CLI tool in the shared terminal and wait for its initial ready prompt
- [x] **CLI-02**: Agent Zero can send a prompt to a running interactive CLI and read its response
- [x] **CLI-03**: Agent Zero can detect when an interactive CLI has finished responding and is ready for next input
- [x] **CLI-04**: Agent Zero can interrupt or exit an interactive CLI session cleanly (Ctrl+C, Ctrl+D, or tool-specific exit command)
- [x] **CLI-05**: Agent Zero can use a pre-built `OpenCodeSession` wrapper with `.start()` / `.send(prompt)` / `.exit()` interface, mirroring `ClaudeSession`
- [x] **CLI-06**: Agent Zero can follow documented orchestration patterns for any interactive CLI via `usr/skills/cli-orchestration/SKILL.md`

## Completed: v1.1 Requirements

### Browser Control

- [x] **BROWSER-01**: Agent Zero navigates to a URL using CDP `Page.navigate` followed by a `document.readyState` poll
- [x] **BROWSER-02**: Agent Zero takes a screenshot via CDP before every browser interaction to observe current state
- [x] **BROWSER-03**: Agent Zero verifies navigation succeeded by checking current URL and page title after navigate-and-wait
- [x] **BROWSER-04**: Shared browser Chromium startup replaces fragile `sleep 2` with a CDP WebSocket health-check poll
- [x] **BROWSER-05**: Agent Zero uses a consistent Observe -> Act -> Verify workflow for all browser interactions

### Claude CLI Control

- [x] **CLAUDE-01**: Agent Zero can launch the `claude` CLI by unsetting `CLAUDECODE` in the subprocess environment
- [x] **CLAUDE-02**: Agent Zero can send a prompt to `claude` using `--print` / `-p` mode and receive the complete response
- [x] **CLAUDE-03**: Agent Zero can detect when a `claude --print` invocation has finished and extract the response text
- [x] **CLAUDE-04**: Agent Zero can run a multi-turn `claude` conversation using `--print --resume UUID` with process returncode as the completion signal
- [x] **CLAUDE-05**: A dedicated `claude-cli` skill (`usr/skills/claude-cli/SKILL.md`) documents all validated invocation patterns

---
*v1.3 requirements defined: 2026-03-03*
*v1.2 requirements completed: 2026-02-25*
*v1.1 requirements completed: 2026-02-25*
*Last updated: 2026-03-03 after roadmap creation*
