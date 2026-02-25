# Roadmap: Agent Zero Enhanced Fork

## Milestones

- ✅ **v1.0 Foundation & Apps System** - Phases 1-5 (shipped 2026-02-25)
- 🚧 **v1.1 Reliability** - Phases 6-10 (in progress)

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

### 🚧 v1.1 Reliability (In Progress)

**Milestone Goal:** Make browser control and Claude Code CLI work reliably as intended — CDP-based navigation, observe-act-verify workflow, CLAUDECODE env fix, multi-turn sessions, and validated skill documentation.

- [x] **Phase 6: CDP Startup Health-Check** - Replace fragile `sleep 2` with a polling loop that confirms Chromium CDP is ready before any agent connects
- [x] **Phase 7: Browser Navigate-with-Verification** - Rewrite shared-browser skill with mandatory Observe-Act-Verify workflow and CDP navigate-wait-verify pattern (completed 2026-02-25)
- [ ] **Phase 8: Claude CLI Single-Turn + Env Fix** - Validate `env -u CLAUDECODE` fix and `claude --print` single-turn pattern with ANSI stripping and clean completion detection
- [ ] **Phase 9: Claude CLI Multi-Turn Sessions** - Validate persistent PTY/tmux multi-turn sessions with idle-timeout + prompt-pattern completion detection
- [ ] **Phase 10: Claude CLI Skill Documentation** - Write `usr/skills/claude-cli/SKILL.md` capturing all validated invocation patterns

## Phase Details

### Phase 6: CDP Startup Health-Check
**Goal**: Chromium reliably starts with CDP enabled and the agent can depend on CDP being reachable before any browser interaction begins
**Depends on**: Nothing (infrastructure fix, prerequisite for Phase 7)
**Requirements**: BROWSER-04
**Success Criteria** (what must be TRUE):
  1. Starting the shared browser app results in Chromium with `--remote-allow-origins=*` confirmed active, not assumed
  2. A CDP WebSocket connection attempt from Agent Zero succeeds immediately after the shared browser app reports ready — no 403, no connection refused
  3. If Chromium fails to start or CDP is unreachable within the timeout, the startup log contains a diagnostic message identifying the failure, not a silent hang
  4. The fragile `sleep 2` guard is gone from `startup.sh` and replaced by a polling loop
**Plans**: 1 plan

Plans:
- [x] 06-01-PLAN.md — Replace sleep 2 with CDP readiness poll in startup.sh

### Phase 7: Browser Navigate-with-Verification
**Goal**: Agent Zero can navigate the shared browser to any URL and confirm the page loaded correctly using a documented, repeatable Observe-Act-Verify workflow
**Depends on**: Phase 6
**Requirements**: BROWSER-01, BROWSER-02, BROWSER-03, BROWSER-05
**Success Criteria** (what must be TRUE):
  1. Agent Zero navigates to a URL via CDP `Page.navigate` and does not treat navigation as complete until `document.readyState === 'complete'` (or a 10s timeout) — the page is fully loaded before any further action
  2. Agent Zero takes a screenshot via CDP before every browser action, so the agent always sees current state before acting
  3. After navigation completes, Agent Zero reads the current URL and page title via CDP `Runtime.evaluate` and can confirm the expected page was reached
  4. The shared-browser skill documents and enforces a named Observe-Act-Verify workflow as the primary interaction pattern — all browser interactions follow this sequence
**Plans**: 1 plan

Plans:
- [ ] 07-01-PLAN.md — Add websocket-client to requirements.txt and rewrite SKILL.md with navigate_and_wait, verify_navigation, and full Observe-Act-Verify

### Phase 8: Claude CLI Single-Turn + Env Fix
**Goal**: Agent Zero can invoke the `claude` CLI from within its own environment and receive a clean, parseable response to a single-turn prompt
**Depends on**: Nothing (independent stream from browser phases)
**Requirements**: CLAUDE-01, CLAUDE-02, CLAUDE-03
**Success Criteria** (what must be TRUE):
  1. Agent Zero launches `claude` CLI without the "Cannot be launched inside another Claude Code session" error — the `CLAUDECODE` env var is unset in the subprocess environment only
  2. Agent Zero sends a prompt to `claude --print` and receives the complete response from stdout as structured output
  3. Agent Zero detects that the `claude --print` invocation has finished via process exit, and the captured response text is free of ANSI escape sequences
**Plans**: 1 plan

Plans:
- [ ] 08-01-PLAN.md — Create python/helpers/claude_cli.py with validated single-turn pattern and end-to-end verification

### Phase 9: Claude CLI Multi-Turn Sessions
**Goal**: Agent Zero can conduct a multi-turn conversation with claude CLI using a persistent PTY session, sending follow-up prompts and reliably detecting when each response is complete
**Depends on**: Phase 8
**Requirements**: CLAUDE-04
**Success Criteria** (what must be TRUE):
  1. Agent Zero opens a persistent `code_execution_tool` PTY session for claude and sends a sequence of at least two prompts, receiving a coherent response to each
  2. Agent Zero detects claude response completion using combined idle-timeout and prompt-pattern detection — not idle-timeout alone — avoiding false "done" signals during claude's internal pauses
  3. If the claude session exits unexpectedly (crash, timeout), Agent Zero detects the dead session and can restart it rather than hanging
**Plans**: TBD

### Phase 10: Claude CLI Skill Documentation
**Goal**: A dedicated skill document captures every validated claude CLI interaction pattern so any Agent Zero session can invoke claude correctly without re-discovering these patterns
**Depends on**: Phase 9
**Requirements**: CLAUDE-05
**Success Criteria** (what must be TRUE):
  1. `usr/skills/claude-cli/SKILL.md` exists and documents the single-turn pattern (`env -u CLAUDECODE claude --print --output-format json`), multi-turn PTY pattern, ANSI stripping, and completion detection — all patterns validated in Phases 8-9
  2. The skill documents the `--session-id` / `--resume UUID` options for multi-agent session coordination
  3. The skill includes security notes covering API key handling and subprocess scope of the env var fix
**Plans**: TBD

## Progress

**Execution Order:**
Phases 6 → 7 (browser stream). Phases 8 → 9 → 10 (claude stream, independent of 6-7). Phase 7 requires Phase 6. Phase 9 requires Phase 8. Phase 10 requires Phase 9.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Apps System Core | v1.0 | - | Complete | 2026-02-25 |
| 2. Core Built-in Apps | v1.0 | - | Complete | 2026-02-25 |
| 3. GSD Skill Pack | v1.0 | - | Complete | 2026-02-25 |
| 4. Neon UI + UX | v1.0 | - | Complete | 2026-02-25 |
| 5. Scaffolding + Skills | v1.0 | - | Complete | 2026-02-25 |
| 6. CDP Startup Health-Check | v1.1 | 1/1 | Complete | 2026-02-25 |
| 7. Browser Navigate-with-Verification | 1/1 | Complete   | 2026-02-25 | - |
| 8. Claude CLI Single-Turn + Env Fix | v1.1 | 0/1 | Not started | - |
| 9. Claude CLI Multi-Turn Sessions | v1.1 | 0/TBD | Not started | - |
| 10. Claude CLI Skill Documentation | v1.1 | 0/TBD | Not started | - |
