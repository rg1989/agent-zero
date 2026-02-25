# Feature Research

**Domain:** Browser automation reliability + interactive CLI session control (Agent Zero fork, v1.1)
**Researched:** 2026-02-25
**Confidence:** HIGH (findings derived from live code inspection, direct CLI interrogation, CDP protocol knowledge — no web sources required)

---

## Context

This is a reliability milestone, not a greenfield feature build. The infrastructure already
exists. The gaps are behavioral: the browser skill documents the right patterns but does not
enforce them, and the claude CLI can be called but nested invocations crash because
`CLAUDECODE=1` is set in the Agent Zero environment.

What follows maps each PROJECT.md requirement (BROWSER-01..05, CLAUDE-01..05) to its feature
category, complexity, and the Agent Zero capabilities it depends on.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that must work for the v1.1 milestone to be considered done. Missing any of these
means the stated goal — "make browser control and Claude Code CLI work reliably" — is not met.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| CDP navigation that waits for page load | Navigating and immediately reading the page returns a blank/partial result without a load-complete wait. Users expect "navigate" to mean "the page is ready." | MEDIUM | `Page.navigate` returns `frameId` immediately. Must follow with `Page.loadEventFired` event or poll `document.readyState` via `Runtime.evaluate`. Already have the WebSocket helper in SKILL.md; need to extend it. |
| Screenshot before every browser action | "Observe before acting" is the only way an agent can know where it is. Without this, clicks land on the wrong element after dynamic page changes. | LOW | `Page.captureScreenshot` via CDP already exists in app.py. The skill documents it. The gap is enforcing it as mandatory, not optional. |
| URL/title verification after navigation | "Did we actually land where we intended?" Without this, failed navigations (redirects, errors, blocked pages) silently pass. | LOW | `Runtime.evaluate` → `{url: location.href, title: document.title}` already shown in SKILL.md. Needs to be the standard post-navigate step. |
| Chromium always starts with CDP remote origins flag | `--remote-allow-origins=*` missing → CDP WebSocket returns 403. The skill documents the fix but the startup script must enforce it. | LOW | `startup.sh` already has `--remote-allow-origins=*`. Verify it is present in every code path that can launch Chromium (startup + any restart logic). |
| claude CLI single-turn invocation from Agent Zero | CLAUDE-01/02/03: The most common use case — "run claude on this task and get an answer" — must work. | LOW | **Critical finding:** `CLAUDECODE=1` is set in Agent Zero's environment. Direct `claude --print "..."` fails with "Cannot be launched inside another Claude Code session." Fix: `env -u CLAUDECODE claude --print "..."`. This is the primary blocker. |
| Completion detection for single-turn claude calls | Agent Zero must know when claude has finished so it can read the output. Without this it reads partial output or hangs. | LOW | In `--print` mode, claude exits with code 0 when done. Standard subprocess completion detection applies. Agent Zero's `code_execution_tool` terminal runtime already handles this pattern. |
| Multi-turn claude sessions via tmux | CLAUDE-04: "Run a complete multi-turn session" — send multiple prompts to the same running instance. | MEDIUM | The shared terminal already has a persistent `tmux shared` session. Pattern: `tmux send-keys -t shared "claude --continue" Enter` followed by `tmux send-keys -t shared "prompt text" Enter`. Detect completion by watching for the claude prompt character (`>` or `?`) returning. |
| Dedicated claude CLI skill (SKILL.md) | CLAUDE-05: Without a skill file, Agent Zero will keep reinventing the patterns wrong. The skill is how knowledge persists. | LOW | Write `usr/skills/claude-cli/SKILL.md` documenting: env var fix, single-turn template, multi-turn tmux template, completion detection patterns, and the `--output-format stream-json` option for structured output. |

### Differentiators (Competitive Advantage)

Features that improve reliability beyond the minimum. Not required to close the milestone, but
would make the patterns significantly more robust.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Structured output from claude via `--output-format json` | Instead of parsing free-form text, get a JSON envelope with `result`, `cost`, `session_id`. Makes multi-turn session management deterministic. | LOW | `claude --print --output-format json "prompt"` returns `{"type":"result","subtype":"success","result":"...","session_id":"..."}`. No parsing heuristics needed. |
| CDP load-event-fenced navigation helper (Python function) | Wraps `Page.navigate` + `Page.loadEventFired` + URL verify into a single reusable function that the skill can reference. Reduces the chance of the agent skipping the wait step. | MEDIUM | Can live as a standalone Python snippet in the skill or as a method in `app.py` (`/api/navigate` could optionally wait for load). |
| `--session-id` persistence for multi-turn claude | Allows resuming a specific claude session by UUID rather than relying on "most recent." Makes multi-agent coordination reliable if two agents run claude sessions. | LOW | CLI already supports `--resume UUID` and `--session-id UUID`. Just needs to be documented in the skill. |
| Observe-Act-Verify as a named pattern in SKILL.md | Giving the three-step loop a name and template makes it a reusable unit the agent can invoke by name rather than reconstruct from first principles each time. | LOW | Already described in SKILL.md v3.0. Needs to be the lead section, not buried after the method reference. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Wrapping CDP in Playwright | "Playwright is higher-level and handles waits automatically." | The shared browser runs a real persistent Chromium instance. Playwright spawns its own isolated instance, creates a persistent loader artifact in the Agent Zero UI (`pkill -f playwright` is already in the troubleshooting guide for this reason), and cannot attach to an already-running Chromium without the CDP-attach mode (which is an advanced Playwright configuration that adds complexity without benefit over raw CDP). | Use raw CDP WebSocket directly. The existing SKILL.md patterns are sufficient. |
| Using `xdotool` for URL navigation | "It's simpler — just type the URL into the address bar." | xdotool navigation is unreliable: it requires `windowfocus` to succeed, is sensitive to focus state, can mis-fire if the address bar already has text selected, and provides no programmatic feedback on success. It also cannot navigate a headless Chromium (which is the actual configuration after the startup.sh rewrite). | `CDP Page.navigate` — fast, reliable, returns a frameId, independent of UI focus. |
| Running claude interactively in Agent Zero's own terminal session | "Just start an interactive claude session and type into it." | Agent Zero's terminal sessions (`code_execution_tool`) are persistent PTY sessions that Agent Zero uses for its own work. Injecting an interactive claude process into them creates a conflict: Agent Zero's prompt detection patterns see the claude prompt as a shell idle signal, causing premature output capture. | Use `--print` mode for single-turn (subprocess exits cleanly) or a dedicated tmux window for interactive sessions, isolated from Agent Zero's own shells. |
| Polling for claude output with a fixed `time.sleep()` | "Just wait 5 seconds and read the output." | LLM response time is non-deterministic. Short waits fail on complex prompts; long waits waste time on simple ones. Makes streaming impossible. | Subprocess completion detection (`wait()` on the PID) for `--print` mode. tmux `capture-pane` polling for interactive mode with idle detection. |
| Setting a global `CLAUDECODE` env override in the Docker image | "Fix the env var problem permanently by unsetting it in the Dockerfile." | `CLAUDECODE=1` is set by Claude Code at runtime, not at image build time. It signals active nesting protection. Removing it from the environment permanently would require a workaround that might break future Claude Code behavior. | Unset it per-invocation: `env -u CLAUDECODE claude ...`. This is precise, reversible, and only affects the spawned subprocess. |

---

## Feature Dependencies

```
[BROWSER-01: CDP navigate with load wait]
    └──requires──> [BROWSER-04: Chromium starts with CDP enabled]
    └──requires──> [CDP WebSocket helper — already in SKILL.md]

[BROWSER-02: Screenshot before every action]
    └──requires──> [BROWSER-04: Chromium starts with CDP enabled]
    └──enhances──> [BROWSER-05: Observe→Act→Verify workflow]

[BROWSER-03: Verify navigation URL/title]
    └──requires──> [BROWSER-01: CDP navigate with load wait]
    └──is part of──> [BROWSER-05: Observe→Act→Verify workflow]

[BROWSER-05: Observe→Act→Verify workflow]
    └──requires──> [BROWSER-01 + BROWSER-02 + BROWSER-03 + BROWSER-04]

[CLAUDE-02: Send prompt, receive response]
    └──requires──> [CLAUDE-01: Launch claude CLI]
    └──requires──> [env -u CLAUDECODE fix — blocks all claude invocations]

[CLAUDE-03: Detect completion]
    └──requires──> [CLAUDE-02: Send prompt]

[CLAUDE-04: Multi-turn session]
    └──requires──> [CLAUDE-01 + CLAUDE-02 + CLAUDE-03]
    └──requires──> [shared-terminal tmux session running]

[CLAUDE-05: Dedicated skill]
    └──requires──> [CLAUDE-01..04 all validated]
    └──documents──> [all claude CLI patterns]
```

### Dependency Notes

- **BROWSER-04 is a prerequisite for all BROWSER features:** If Chromium does not expose CDP with `--remote-allow-origins=*`, every CDP call returns 403. The startup.sh already has this flag; the implementation task is verifying it survives restarts and adding a health-check that confirms CDP is reachable before attempting any browser operation.

- **The `env -u CLAUDECODE` fix is a prerequisite for all CLAUDE features:** Without unsetting this variable, every attempt to call the claude CLI from within an Agent Zero session fails immediately. This is a single-line fix but it blocks all five CLAUDE requirements.

- **CLAUDE-04 (multi-turn) depends on the shared-terminal tmux session:** The `shared` tmux session is started by `apps/shared-terminal/startup.sh`. If the shared-terminal app is not running, the tmux-based multi-turn pattern has no session to target. The skill must document the fallback: create a new tmux session (`tmux new-session -d -s claude-session`) if the shared session is unavailable.

- **CLAUDE-05 (skill) requires CLAUDE-01..04 to be validated:** Writing the skill before confirming the patterns work embeds untested patterns. The skill is the last step, not the first.

---

## MVP Definition

### Launch With (v1.1)

Minimum to close all BROWSER and CLAUDE requirements from PROJECT.md.

- [ ] BROWSER-04 verified: `startup.sh` has `--remote-allow-origins=*` and a CDP health-check confirms it — *prerequisite for everything else*
- [ ] BROWSER-01: CDP navigate with post-navigate `document.readyState` polling (wait until `complete` or 3s timeout) — *core reliability fix*
- [ ] BROWSER-02: Screenshot step codified as mandatory first step in skill workflow — *already in SKILL.md, needs skill update to make it the lead instruction*
- [ ] BROWSER-03: URL/title verify step after every navigation — *one `Runtime.evaluate` call, add to skill template*
- [ ] BROWSER-05: Observe→Act→Verify section promoted to top of SKILL.md as the primary workflow — *skill edit, no code change*
- [ ] env-u CLAUDECODE fix: all claude invocations in the skill use `env -u CLAUDECODE` prefix — *one-line fix, blocks everything else*
- [ ] CLAUDE-01/02/03: Single-turn pattern: `env -u CLAUDECODE claude --print --output-format json "prompt"` — *subprocess, reads output on exit*
- [ ] CLAUDE-04: Multi-turn pattern: tmux `send-keys` to shared session + capture-pane polling for completion — *tmux commands, no new infrastructure*
- [ ] CLAUDE-05: `usr/skills/claude-cli/SKILL.md` documenting all patterns with working code examples

### Add After Validation (v1.x)

- [ ] `/api/navigate` in `app.py` gains an optional `wait_for_load: bool` parameter — add only if Agent Zero frequently calls navigate via HTTP rather than direct Python CDP. Trigger: if skill-based CDP direct calls are cumbersome for certain workflows.
- [ ] `--session-id` based session tracking in the claude CLI skill — add when multi-agent coordination is needed. Trigger: second agent needs to join a claude session started by the first.

### Future Consideration (v2+)

- [ ] Streaming output from claude via `--output-format stream-json` piped back to Agent Zero in real-time — complex integration, defer until single-turn and multi-turn are stable and the use case is validated.
- [ ] Browser action library (click by text, fill form field, wait for element) built on top of CDP — defer until the basic Observe→Act→Verify loop is proven reliable in practice.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| env -u CLAUDECODE fix | HIGH | LOW | P1 — unblocks all CLAUDE features |
| BROWSER-04 CDP health-check | HIGH | LOW | P1 — unblocks all BROWSER features |
| CDP navigate with load wait (BROWSER-01) | HIGH | LOW | P1 — core reliability |
| CLAUDE single-turn --print pattern (CLAUDE-01/02/03) | HIGH | LOW | P1 — core use case |
| URL/title verify after navigate (BROWSER-03) | HIGH | LOW | P1 — required for BROWSER-05 |
| Observe→Act→Verify skill update (BROWSER-02/05) | MEDIUM | LOW | P1 — no code, skill edit only |
| Multi-turn tmux pattern (CLAUDE-04) | MEDIUM | MEDIUM | P2 — depends on P1 CLAUDE |
| claude-cli SKILL.md (CLAUDE-05) | HIGH | LOW | P1 — but last, after others validated |
| `/api/navigate` load-wait option | LOW | LOW | P3 — only if direct CDP insufficient |
| `--session-id` tracking | LOW | LOW | P3 — future multi-agent |

**Priority key:**
- P1: Must have for v1.1 launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Existing Infrastructure (Dependencies Already Satisfied)

These are Agent Zero capabilities this milestone depends on — all confirmed present:

| Capability | Where | Status |
|------------|-------|--------|
| CDP WebSocket Python helper (websocket-client) | SKILL.md + app.py uses websockets lib | Present |
| `Page.captureScreenshot` via CDP | app.py `/api/screenshot`, SKILL.md | Present |
| `Page.navigate` via CDP | app.py `/api/navigate`, SKILL.md | Present |
| `Runtime.evaluate` for JS execution | SKILL.md | Present |
| Chromium headless with `--remote-allow-origins=*` | apps/shared-browser/startup.sh line 39 | Present |
| tmux `shared` session | apps/shared-terminal/startup.sh | Present |
| `code_execution_tool` terminal runtime | python/tools/code_execution_tool.py | Present |
| claude CLI binary | /Users/rgv250cc/.local/bin/claude v2.1.55 | Present |
| `--print` non-interactive mode | claude --help output | Present |
| `--output-format json` for structured output | claude --help output | Present |
| `--continue` / `--resume UUID` for multi-turn | claude --help output | Present |

---

## Sources

- `/Users/rgv250cc/Documents/Projects/agent-zero/usr/skills/shared-browser/SKILL.md` — existing skill v3.0 (live file)
- `/Users/rgv250cc/Documents/Projects/agent-zero/apps/shared-browser/startup.sh` — Chromium startup configuration (live file)
- `/Users/rgv250cc/Documents/Projects/agent-zero/apps/shared-browser/app.py` — Flask CDP proxy (live file)
- `/Users/rgv250cc/Documents/Projects/agent-zero/apps/shared-terminal/startup.sh` — tmux session setup (live file)
- `/Users/rgv250cc/Documents/Projects/agent-zero/python/tools/code_execution_tool.py` — Agent Zero terminal session patterns (live file)
- `/Users/rgv250cc/Documents/Projects/agent-zero/.planning/PROJECT.md` — milestone requirements (live file)
- `claude --help` output — v2.1.55, direct CLI interrogation, confirmed `--print`, `--output-format`, `--continue`, `--resume` flags
- Direct env inspection — confirmed `CLAUDECODE=1` is set, which blocks nested invocations; `env -u CLAUDECODE` is the fix
- CDP protocol knowledge (HIGH confidence from training) — `Page.navigate` return semantics, `loadEventFired`, `Runtime.evaluate` for `document.readyState`

---

*Feature research for: Agent Zero v1.1 — Browser reliability + Claude CLI control*
*Researched: 2026-02-25*
