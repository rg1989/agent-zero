# Requirements: Agent Zero Fork — v1.1 Reliability

**Defined:** 2026-02-25
**Core Value:** Agent Zero can build, run, and persist web applications directly within its own UI

## v1.1 Requirements

Requirements for the Reliability milestone. Each maps to roadmap phases 6–10.

### Browser Control

- [ ] **BROWSER-01**: Agent Zero navigates to a URL using CDP `Page.navigate` followed by a `document.readyState` poll (never treats navigation as complete before page loads)
- [ ] **BROWSER-02**: Agent Zero takes a screenshot via CDP before every browser interaction to observe current state
- [ ] **BROWSER-03**: Agent Zero verifies navigation succeeded by checking current URL and page title after navigate-and-wait
- [ ] **BROWSER-04**: Shared browser Chromium startup replaces fragile `sleep 2` with a CDP WebSocket health-check poll, ensuring CDP is ready before any agent tries to connect
- [ ] **BROWSER-05**: Agent Zero uses a consistent Observe → Act → Verify workflow for all browser interactions (documented and enforced in skill)

### Claude CLI Control

- [ ] **CLAUDE-01**: Agent Zero can launch the `claude` CLI by unsetting `CLAUDECODE` in the subprocess environment (`env -u CLAUDECODE claude ...`), resolving the "cannot launch inside another Claude Code session" error
- [ ] **CLAUDE-02**: Agent Zero can send a prompt to `claude` using `--print` / `-p` mode and receive the complete response from stdout
- [ ] **CLAUDE-03**: Agent Zero can detect when a `claude --print` invocation has finished (process exit, clean stdout capture) and extract the response text free of ANSI escape sequences
- [ ] **CLAUDE-04**: Agent Zero can run a multi-turn interactive `claude` session using a persistent PTY (`code_execution_tool` or shared tmux), sending follow-up prompts and reading responses with combined idle-timeout + prompt-pattern completion detection
- [ ] **CLAUDE-05**: A dedicated `claude-cli` skill (`usr/skills/claude-cli/SKILL.md`) documents the validated invocation patterns: single-turn (`--print`), multi-turn (PTY/tmux), env fix, ANSI stripping, and completion detection

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Apps

- **APPS-01**: Background removal app (`apps/bg-remover/`) registered and accessible at `/bg-remover/` with auto-start
- **APPS-02**: App auto-discovery — Agent Zero registers new apps found in `apps/` directory without manual `register.py`

### UI

- **UI-01**: Preferences panel improvements (in-progress webui changes)
- **UI-02**: Sidebar and quick-actions UI polish

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Playwright for shared browser | Explicitly banned — spawns separate Chromium instance, creates persistent UI loader |
| New python/tools/ Tool class for claude CLI | No value — `code_execution_tool` already handles PTY subprocess; duplication with no gain |
| Flask/API endpoint for claude CLI | Unnecessary — agent invokes CLI directly via code execution tools |
| Upstream Agent Zero core changes | Fork-only — upstream changes pulled separately |
| OAuth / auth system | Single-user personal tool |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BROWSER-04 | Phase 6 | Pending |
| BROWSER-01 | Phase 7 | Pending |
| BROWSER-02 | Phase 7 | Pending |
| BROWSER-03 | Phase 7 | Pending |
| BROWSER-05 | Phase 7 | Pending |
| CLAUDE-01 | Phase 8 | Pending |
| CLAUDE-02 | Phase 8 | Pending |
| CLAUDE-03 | Phase 8 | Pending |
| CLAUDE-04 | Phase 9 | Pending |
| CLAUDE-05 | Phase 10 | Pending |

**Coverage:**
- v1.1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-25*
*Last updated: 2026-02-25 after roadmap creation (phases 6-10 confirmed)*
