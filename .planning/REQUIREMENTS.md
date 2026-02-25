# Requirements: Agent Zero Fork — v1.1 Reliability

**Defined:** 2026-02-25
**Core Value:** Agent Zero can build, run, and persist web applications directly within its own UI

## v1.1 Requirements

Requirements for the Reliability milestone. Each maps to roadmap phases 6–10.

### Browser Control

- [x] **BROWSER-01**: Agent Zero navigates to a URL using CDP `Page.navigate` followed by a `document.readyState` poll (never treats navigation as complete before page loads)
- [x] **BROWSER-02**: Agent Zero takes a screenshot via CDP before every browser interaction to observe current state
- [x] **BROWSER-03**: Agent Zero verifies navigation succeeded by checking current URL and page title after navigate-and-wait
- [x] **BROWSER-04**: Shared browser Chromium startup replaces fragile `sleep 2` with a CDP WebSocket health-check poll, ensuring CDP is ready before any agent tries to connect
- [x] **BROWSER-05**: Agent Zero uses a consistent Observe → Act → Verify workflow for all browser interactions (documented and enforced in skill)

### Claude CLI Control

- [x] **CLAUDE-01**: Agent Zero can launch the `claude` CLI by unsetting `CLAUDECODE` in the subprocess environment (`env -u CLAUDECODE claude ...`), resolving the "cannot launch inside another Claude Code session" error
- [x] **CLAUDE-02**: Agent Zero can send a prompt to `claude` using `--print` / `-p` mode and receive the complete response from stdout
- [x] **CLAUDE-03**: Agent Zero can detect when a `claude --print` invocation has finished (process exit, clean stdout capture) and extract the response text free of ANSI escape sequences
- [ ] **CLAUDE-04**: Agent Zero can run a multi-turn `claude` conversation using repeated `subprocess.run` calls with `--print --resume UUID`, where each turn returns a complete, parseable response and the session UUID is propagated automatically across turns — no PTY, no idle-timeout, no prompt-pattern detection required (process `returncode` is the unambiguous completion signal). Dead/expired sessions are detected via `returncode 1` + `"No conversation found"` in stderr and recovered by restarting with `session_id=None`.
- [ ] **CLAUDE-05**: A dedicated `claude-cli` skill (`usr/skills/claude-cli/SKILL.md`) documents the validated invocation patterns: single-turn (`--print`), multi-turn (`--resume UUID`), env fix, ANSI stripping, and completion detection

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
| BROWSER-04 | Phase 6 | Complete |
| BROWSER-01 | Phase 7 | Complete |
| BROWSER-02 | Phase 7 | Complete |
| BROWSER-03 | Phase 7 | Complete |
| BROWSER-05 | Phase 7 | Complete |
| CLAUDE-01 | Phase 8 | Complete |
| CLAUDE-02 | Phase 8 | Complete |
| CLAUDE-03 | Phase 8 | Complete |
| CLAUDE-04 | Phase 9 | Pending |
| CLAUDE-05 | Phase 10 | Pending |

**Coverage:**
- v1.1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-25*
*Last updated: 2026-02-25 — BROWSER-04 complete (Phase 6 CDP startup health-check); CLAUDE-04 definition revised to reflect subprocess.run/--resume UUID/returncode approach (Phase 9 plan revision)*
