# Project Research Summary

**Project:** Agent Zero v1.1 — Browser Reliability + Claude CLI Control
**Domain:** CDP WebSocket browser automation + interactive CLI subprocess management in a Docker-hosted LLM agent framework
**Researched:** 2026-02-25
**Confidence:** HIGH

## Executive Summary

This is a reliability milestone, not a greenfield build. Agent Zero's fork already contains all the infrastructure required: a working async CDP client (`apps/shared-browser/app.py`), a production-grade PTY session manager (`python/helpers/tty_session.py`), a persistent tmux terminal (`apps/shared-terminal/`), and a browser skill that documents the right interaction patterns. The gaps are behavioral: the browser skill does not enforce an observe-act-verify workflow, CDP navigation does not wait for page load, and all claude CLI invocations fail silently because `CLAUDECODE=1` is set in the Agent Zero Docker environment, which blocks nested claude process spawning.

The recommended approach is minimal-footprint: fix two existing files (`startup.sh` and `shared-browser/SKILL.md`) and create one new file (`usr/skills/claude-cli/SKILL.md`). No new Tool classes, no new Flask endpoints, no new Python dependencies except `websocket-client>=1.9.0` for synchronous CDP in skill snippets. Every feature requirement (BROWSER-01 through BROWSER-05, CLAUDE-01 through CLAUDE-05) can be satisfied through skill documentation updates and a 10-line bash change to the Chromium startup script.

The primary risks are ordering problems: CDP navigation must wait for `document.readyState === 'complete'` before the observe step, and claude CLI output must be stripped of ANSI escape sequences before the agent parses it. Both are medium-complexity fixes with well-understood solutions. The `CLAUDECODE` environment variable unset (`env -u CLAUDECODE`) is a one-line fix that unblocks all five CLAUDE requirements. BROWSER-04 (confirmed CDP readiness at Chromium startup) is a prerequisite for all browser features and should be addressed first.

---

## Key Findings

### Recommended Stack

The codebase already has the full async CDP stack (`websockets` v15.0.1, installed as a transitive dependency) and the PTY stack (stdlib `pty` + `asyncio` in `tty_session.py`). The only new Python dependency is `websocket-client>=1.9.0`, needed for synchronous CDP WebSocket connections in skill snippets where using an async context manager would require an unnecessary `asyncio.run()` wrapper.

**Core technologies:**
- `websockets` (async, already installed) — CDP WebSocket connections in async Flask handlers and Agent Zero tool code; reference pattern established in `app.py`
- `websocket-client>=1.9.0` (add to `requirements.txt`) — synchronous CDP in `code_execution_tool` Python snippets; simpler than async in snippet-style code
- `TTYSession` (existing, `python/helpers/tty_session.py`) — multi-turn interactive claude CLI sessions via PTY; already production-ready
- `asyncio.create_subprocess_exec` (stdlib) — single-turn `claude -p` subprocess; exits on completion, no interactive session management needed
- `urllib.request` (stdlib) — CDP tab discovery via `http://localhost:9222/json`; already used in `app.py`, zero-cost

**Critical exclusions:**
- Do not use `playwright` for the shared browser — it spawns an isolated Chromium instance and creates a persistent loader artifact in the Agent Zero UI (explicitly banned in SKILL.md)
- Do not use `pexpect` — `TTYSession` already provides equivalent PTY functionality; `pexpect` would duplicate it and add a dependency
- Unset `CLAUDECODE` per-invocation in subprocess env only (`env=` parameter), never globally

### Expected Features

**Must have (table stakes for v1.1 milestone):**
- `env -u CLAUDECODE` fix on all claude CLI invocations — one-line fix that unblocks CLAUDE-01 through CLAUDE-05
- BROWSER-04 CDP health check — confirm Chromium starts with `--remote-allow-origins=*` and CDP WebSocket is reachable; prerequisite for all browser features
- CDP navigate with page-load wait (BROWSER-01) — poll `document.readyState === 'complete'` after `Page.navigate` with 10s cap
- URL/title verification after navigation (BROWSER-03) — `Runtime.evaluate` returning `{url: location.href, title: document.title}`
- Observe-Act-Verify as mandatory workflow in `shared-browser/SKILL.md` (BROWSER-02/05) — documentation change, no code change
- Single-turn claude CLI pattern with `--print --output-format json` (CLAUDE-01/02/03) — subprocess exits on completion, structured JSON response
- Multi-turn claude CLI via dedicated `code_execution_tool` session (CLAUDE-04) — idle-timeout detection with prompt regex guard
- `usr/skills/claude-cli/SKILL.md` with all patterns (CLAUDE-05) — created after CLAUDE-01..04 are validated

**Should have (differentiators):**
- `--output-format json` structured output instead of free-form text parsing — eliminates parsing heuristics, already supported by claude CLI
- Observe-Act-Verify pattern named and promoted to lead section of skill — makes it a reusable pattern agents invoke by name
- `--session-id` / `--resume UUID` documented in claude CLI skill — enables deterministic multi-agent session management

**Defer to v2+:**
- Streaming output from claude via `--output-format stream-json` piped in real-time — complex integration; defer until single-turn/multi-turn are stable
- Browser action library (click-by-text, fill-form) — defer until the Observe-Act-Verify loop is proven reliable

### Architecture Approach

The architecture is a three-path system where Agent Zero can reach Chromium via: (1) the Flask HTTP bridge (`app.py /api/*`) used by the UI; (2) CDP WebSocket directly from skill-generated Python code running in `code_execution_tool`; and (3) Playwright via `browser_agent.py` for AI-driven browsing sub-agent tasks. These paths do not conflict. The skill-based approach (path 2) is the primary target for this milestone — skill documentation guides the agent to assemble CDP interactions from existing primitives without requiring new Tool classes or Flask endpoints.

**Major components and their roles:**
1. `apps/shared-browser/startup.sh` — MODIFY: replace `sleep 2` startup guard with a polling loop that confirms `/json` HTTP + WebSocket both succeed before marking Chromium ready
2. `usr/skills/shared-browser/SKILL.md` — MODIFY: add explicit Navigate-with-Verification pattern (screenshot → navigate → poll readyState → Runtime.evaluate URL/title → screenshot) as the primary workflow
3. `usr/skills/claude-cli/SKILL.md` — NEW: documents single-turn `claude -p` pattern, multi-turn `code_execution_tool` session pattern, ANSI stripping, completion detection, and env var fix
4. `python/tools/browser_agent.py` — NO CHANGE: `_wait_for_cdp()` and `--remote-allow-origins=*` path already correct; Playwright connection logic is not the primary skill path
5. `python/tools/code_execution_tool.py` / `TTYSession` — NO CHANGE: existing PTY session management, `between_output_timeout` idle detection, and session ID persistence are the correct primitives for multi-turn claude

### Critical Pitfalls

1. **CDP navigate returns before page loads** — After `Page.navigate`, the agent must poll `document.readyState === 'complete'` via `Runtime.evaluate` with a 10s cap before taking a screenshot or acting. `Page.navigate` resolves on navigation start, not page load. Avoidance: document this as a mandatory step in SKILL.md and in `startup.sh`'s readiness check.

2. **CLAUDECODE=1 blocks nested claude invocations** — Every attempt to call the claude CLI from within Agent Zero silently fails with "Cannot be launched inside another Claude Code session." Fix: pass `env=` with `CLAUDECODE` removed only to the subprocess, not globally. This is a prerequisite for all five CLAUDE requirements.

3. **ANSI escape sequences corrupt claude CLI output parsing** — Claude CLI (Ink/React TUI) wraps all output in ANSI color and cursor codes. Raw PTY output passed to the agent LLM looks like garbage. Fix: apply `re.sub(r'\x1b\[[0-9;]*[mGKHFABCDEFJ]', '', text)` and strip `\r` in a claude-specific wrapper layer before returning output; do not touch `TTYSession` itself.

4. **Idle-timeout alone is unreliable for claude completion detection** — Claude's streaming output has natural pauses (tool calls, thinking) of 1-2s that trigger false "done" signals, while the actual completion state (input prompt rendered) produces no text at all, leaving the timeout to fire later than expected. Fix: combine `between_output_timeout` (raise to 3-4s) with a regex check on the last 200 chars for claude's input prompt marker.

5. **CDP tab selection picks wrong target** — `tabs[0]` from `/json` is creation-order, not visible-tab order. Internal Chromium pages (`chrome://new-tab-page`, DevTools) silently become the controlled target. Fix: filter `/json` results by `type == 'page'` and skip `chrome://` and `about:blank` URLs — the SKILL.md already shows this correctly; `_get_ws_url()` in `app.py` must be updated to match.

---

## Implications for Roadmap

Based on dependency analysis across all four research files, the work splits into two independent streams (CDP browser fixes and Claude CLI skill) with a clear ordering within each stream. Total scope is narrow: two file modifications, one new file creation, and one new Python package in `requirements.txt`.

### Phase 1: CDP Readiness Foundation (BROWSER-04)

**Rationale:** `--remote-allow-origins=*` missing from any Chromium startup path returns a 403 on every CDP WebSocket call. All browser features depend on this. Fixing the `startup.sh` readiness check first ensures Phase 2 work is testable from day one.

**Delivers:** Chromium reliably starts with CDP enabled; polling loop replaces the fragile `sleep 2` guard; startup failure produces a clear diagnostic instead of a silent 403.

**Addresses:** BROWSER-04 requirement; pitfalls 2 (WebSocket 403), 5 (wrong tab selection in `_get_ws_url()`), 7 (headless=new viewport behavior documentation).

**Avoids:** All browser features being blocked by an infrastructure issue discovered mid-implementation.

### Phase 2: Browser Skill — Navigate-with-Verification (BROWSER-01/02/03/05)

**Rationale:** These four requirements are documentation-only changes to `shared-browser/SKILL.md`. They are interdependent (BROWSER-02 screenshot is the "observe" step; BROWSER-01 load wait makes the screenshot meaningful; BROWSER-03 URL verify closes the loop; BROWSER-05 is the workflow that ties them together). One skill rewrite delivers all four.

**Delivers:** Updated `shared-browser/SKILL.md` with Observe-Act-Verify as the lead section, a Navigate-with-Verification code pattern (Page.navigate + readyState poll + Runtime.evaluate URL/title + screenshot), and xdotool demoted to a fallback section.

**Uses:** `websocket-client` sync CDP in skill snippets; `urllib.request` for tab discovery; `base64` for screenshot decode — all already available.

**Avoids:** Pitfall 1 (navigate before load), pitfall 4 (wrong tab), pitfall 7 (false "navigation succeeded").

### Phase 3: Claude CLI — Single-Turn + Environment Fix (CLAUDE-01/02/03)

**Rationale:** The `CLAUDECODE=1` fix is a prerequisite for all CLAUDE features. Single-turn `claude -p` is the simplest interaction pattern and must be validated before multi-turn work begins. CLAUDE-01/02/03 form a natural unit: launch, send prompt, receive structured response.

**Delivers:** Confirmed working pattern for `env -u CLAUDECODE claude --print --output-format json "prompt"` via `code_execution_tool`; ANSI stripping documented; completion detection via process exit confirmed.

**Uses:** `asyncio.create_subprocess_exec` (stdlib) for async single-turn; `code_execution_tool runtime=terminal` for skill-based single-turn — both patterns documented.

**Avoids:** Pitfall 3 (CLAUDECODE block), pitfall 5 (ANSI corruption), pitfall 10 (subprocess env/auth).

**Research flag:** Manually run the single-turn pattern via `code_execution_tool` before writing the skill. Claude CLI's exact output format and prompt marker must be empirically confirmed — training knowledge on specific Ink escape sequences is MEDIUM confidence.

### Phase 4: Claude CLI — Multi-Turn Sessions (CLAUDE-04)

**Rationale:** Multi-turn depends on single-turn working (Phase 3). The persistent `code_execution_tool` session with `between_output_timeout` is the correct primitive but requires careful timeout calibration and liveness checking to avoid the session-reuse and idle-timeout pitfalls.

**Delivers:** Validated multi-turn interaction pattern using `code_execution_tool` with a dedicated session ID; idle-timeout + prompt regex completion detection; session liveness check before each send; fallback session restart if claude exits unexpectedly.

**Avoids:** Pitfall 4 (idle-timeout unreliability), pitfall 6 (session reuse after exit), pitfall 5 (ANSI sequences).

**Research flag:** The exact claude CLI prompt marker string (the characters Ink renders when waiting for input) must be confirmed empirically. Use `xxd` or `repr()` on the raw PTY output to extract the exact byte sequence before writing the detection regex.

### Phase 5: Claude CLI Skill Documentation (CLAUDE-05)

**Rationale:** The skill is written last, after all patterns are validated. Writing before validation embeds untested patterns. This is the explicit dependency in FEATURES.md.

**Delivers:** `usr/skills/claude-cli/SKILL.md` covering: env var fix, single-turn template, multi-turn session template, ANSI stripping, completion detection, session liveness, `--session-id` / `--resume` for multi-agent coordination, security notes (API key masking, command scope).

**Uses:** Patterns validated in Phases 3 and 4.

**Avoids:** Skill embedding assumptions that fail at runtime.

### Phase Ordering Rationale

- Phase 1 before Phase 2: CDP reliability is infrastructure; browser skill improvements are useless if CDP is not reliably reachable.
- Phases 1-2 and Phases 3-5 are independent streams that could run in parallel by two developers.
- Phase 3 before Phase 4: Multi-turn requires single-turn to be confirmed working; the env var fix and ANSI handling must be solved first.
- Phase 5 always last: Skill documents must reflect validated patterns, not aspirational ones.
- No Python tool class changes anywhere: `code_execution_tool` and `TTYSession` already provide all primitives; the complexity is in knowledge (what sequences to use), not plumbing.

### Research Flags

Phases requiring empirical validation before implementation completes:
- **Phase 3 (Claude CLI single-turn):** Confirm exact claude CLI output format, ANSI sequences, and prompt marker string by running manually in Docker before coding detection logic. MEDIUM confidence on specifics.
- **Phase 4 (Claude CLI multi-turn):** Profile claude CLI's raw PTY bytes during an idle-at-prompt state to extract the exact prompt marker regex. Must be done empirically — Ink renders are version-specific.

Phases with standard, well-documented patterns (skip additional research):
- **Phase 1 (CDP readiness):** Chromium CDP startup patterns are well-documented; `startup.sh` is a 10-line bash change.
- **Phase 2 (Browser skill):** CDP `Page.navigate`, `Page.loadEventFired`, `Runtime.evaluate` semantics are stable CDP spec.
- **Phase 5 (Skill documentation):** Skill writing once patterns are validated; no technical uncertainty.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against installed packages (`pip index versions`), running codebase, and CLI help output. Only new dependency is `websocket-client>=1.9.0`. |
| Features | HIGH | Derived from live code inspection, direct CLI interrogation of claude v2.1.55, and confirmed env var behavior. All capabilities verified as present or absent. |
| Architecture | HIGH | All findings from direct codebase inspection. Component boundaries and tool interaction paths confirmed by reading source files. No assumptions. |
| Pitfalls | HIGH (functional) / MEDIUM (specifics) | CDP timing issues and env var problems are HIGH confidence. Claude CLI ANSI escape sequences and exact prompt marker pattern are MEDIUM — Ink renders are version-dependent and must be confirmed empirically. |

**Overall confidence:** HIGH

### Gaps to Address

- **Claude CLI prompt marker pattern:** The specific ANSI/character sequence that claude CLI renders when waiting for input must be confirmed by running `claude` in a PTY and inspecting raw bytes with `repr()` or `xxd`. Do this at the start of Phase 3 before writing detection logic. Estimated 30 minutes of empirical profiling.
- **`websocket-client` in Docker venv:** `websocket-client>=1.9.0` must be added to `requirements.txt` and confirmed installable in the Docker Python venv (`/opt/venv-a0`). Verify during Phase 2 setup.
- **`xdotool` / `scrot` in Docker:** `install_additional.sh` may not include these packages. Run `which xdotool scrot` in the container to confirm. If absent, add to `install_additional.sh`. These are fallbacks only; absence does not block any primary path.
- **`asyncio.run()` in Flask threads:** Current `app.py` uses `asyncio.run()` inside Flask route handlers. This works under the current threading model but breaks under ASGI hosts. Not a current milestone concern but should be documented with a comment warning in `app.py` during Phase 1.

---

## Sources

### Primary (HIGH confidence)
- `python/helpers/tty_session.py` — verified: stdlib `pty` + asyncio PTY; no external dependencies
- `python/helpers/shell_local.py` — verified: wraps TTYSession; confirms interactive session pattern
- `apps/shared-browser/app.py` — verified: `websockets` async CDP, `asyncio.wait_for` timeout, `async with websockets.connect(ws_url, max_size=None)` pattern
- `apps/shared-browser/startup.sh` — verified: `--remote-allow-origins=*` present; `sleep 2` guard identified as fragile
- `apps/shared-terminal/startup.sh` — verified: tmux `shared` session creation
- `usr/skills/shared-browser/SKILL.md` v3.0 — verified: `websocket-client` sync pattern, CDP helper, xdotool fallback documented
- `python/tools/browser_agent.py` — verified: `_wait_for_cdp()` TCP readiness check, Playwright `cdp_url` connection
- `python/tools/terminal_agent.py` — verified: tmux `send-keys` + sentinel pattern; not suitable for interactive claude sessions
- `python/tools/code_execution_tool.py` — verified: `LocalInteractiveSession`, `between_output_timeout`, session ID persistence
- `python/tools/skills_tool.py` — verified: `agent.data["loaded_skills"]` injection pattern; max 5 skills
- `requirements.txt` — verified: `websocket-client` absent; `websockets` absent as explicit dep (present as transitive)
- `docker/base/fs/ins/install_python.sh` — verified: Python 3.12.4 in `/opt/venv-a0`
- `claude --help` (v2.1.55) — verified: `-p/--print`, `--output-format text/json/stream-json`, `--continue`, `--resume`, `CLAUDECODE` env var protection
- `pip index versions websocket-client` — verified: 1.9.0 is current stable
- `.planning/PROJECT.md` — verified: BROWSER-01..05 and CLAUDE-01..05 requirements

### Secondary (MEDIUM confidence)
- CDP protocol training knowledge — `Page.navigate` return semantics, `loadEventFired`, `Runtime.evaluate document.readyState` behavior; well-established, multiple sources agree
- Chromium `--remote-allow-origins` flag behavior — introduced ~M108, broadly documented pattern
- Claude CLI Ink/React TUI architecture — ANSI output structure inferred from Ink framework knowledge; specific escape sequences are version-dependent

### Tertiary (LOW confidence — validate empirically)
- Claude CLI exact prompt marker for completion detection — must be confirmed by running `claude` in a PTY and inspecting raw bytes; not verifiable from source code or documentation alone

---
*Research completed: 2026-02-25*
*Ready for roadmap: yes*
