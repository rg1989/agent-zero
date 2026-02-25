# Architecture Research

**Domain:** Agent Zero fork — CDP browser control reliability + claude CLI skill integration
**Researched:** 2026-02-25
**Confidence:** HIGH (all findings from direct codebase inspection)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Agent Zero Core (FastAPI)                        │
│  agent.py message loop → tool dispatch → tool.execute() → Response      │
├────────────────┬───────────────────┬──────────────────┬─────────────────┤
│  browser_agent │  terminal_agent   │ code_execution   │  skills_tool    │
│  (Tool class)  │  (Tool class)     │  (Tool class)    │  (Tool class)   │
│                │                   │                  │                  │
│  browser-use   │  tmux send-keys   │  LocalInteractive│  loads SKILL.md │
│  Playwright    │  + capture-pane   │  Session / SSH   │  into context   │
│  BrowserSession│                   │                  │                  │
└───────┬────────┴──────────┬────────┴──────────────────┴────────┬────────┘
        │                   │                                      │
        ▼                   ▼                                      ▼
┌──────────────┐   ┌─────────────────┐                  ┌──────────────────┐
│ Shared Browser│   │ Shared Terminal │                  │ usr/skills/      │
│ App (Flask)  │   │ App (tmux)      │                  │ shared-browser/  │
│ port 9003    │   │                 │                  │   SKILL.md       │
│              │   │                 │                  │ claude-cli/      │
│  CDP ← → ──→│   │                 │                  │   SKILL.md (NEW) │
│  Chromium    │   │                 │                  └──────────────────┘
│  port 9222   │   │                 │
└──────────────┘   └─────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  startup.sh: Chromium --headless=new --remote-debugging-port=9222        │
│              --remote-allow-origins=*                                     │
│  app.py:     Flask routes /api/navigate, /api/screenshot, /api/click...  │
│  Agent code: python WebSocket client → CDP port 9222                     │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `browser_agent.py` (Tool) | Connects browser-use/Playwright to shared or headless Chromium; manages BrowserSession lifecycle | Python class extending Tool; State object stored in agent.data |
| `apps/shared-browser/startup.sh` | Launches Chromium with CDP flags; starts Flask app | bash script called by AppManager |
| `apps/shared-browser/app.py` | Flask server bridging Agent Zero UI and Chromium; routes /api/navigate, /api/screenshot, etc. | Python Flask with asyncio CDP via websockets library |
| `usr/skills/shared-browser/SKILL.md` | Documents CDP WebSocket patterns and xdotool commands for agent consumption | Markdown loaded dynamically via skills_tool |
| `terminal_agent.py` (Tool) | Injects commands into shared tmux session, captures output via sentinel pattern | Python class extending Tool; subprocess tmux calls |
| `code_execution_tool.py` (Tool) | Runs code in persistent LocalInteractiveSession shells; handles Python, node, bash | Full interactive PTY; prompt and dialog detection |
| `skills_tool.py` (Tool) | Lists and loads SKILL.md files into agent context extras | Reads from usr/skills/; populates agent.data["loaded_skills"] |
| `prompts/agent.system.tool.browser.md` | Instructs agent how/when to invoke browser_agent | Markdown injected into system prompt |

---

## Where CDP Control Lives Now vs. What Needs Fixing

The CDP integration exists at two distinct levels, with a gap between them:

**Level 1 — Flask bridge (apps/shared-browser/app.py)**
Flask exposes HTTP endpoints that wrap CDP calls. The UI (noVNC/screenshot polling) uses these. This layer is fully functional — navigate, click, screenshot, scroll all work.

**Level 2 — browser-use via Playwright (python/tools/browser_agent.py)**
When `use_shared=true`, browser_agent connects Playwright to Chromium via `cdp_url=http://localhost:9222`. This works IF Chromium started with `--remote-allow-origins=*`.

**The Bug (BROWSER-04)**
`startup.sh` already has `--remote-allow-origins=*`. However, the skill documentation (SKILL.md v3.0) says "If CDP returns 403: kill Chromium and restart." This suggests the flag may be missing from some startup path, or there is an ordering issue where browser_agent connects before Chromium is ready. The `_wait_for_cdp()` helper in browser_agent.py handles the readiness wait, but only checks TCP connectivity — not that the CDP WebSocket actually accepts cross-origin connections.

**The Workflow Gap (BROWSER-01 through BROWSER-05)**
browser_agent delegates all navigation decisions to the browser-use AI sub-agent, which decides to use `Page.navigate` or not. There is no explicit observe-act-verify enforced in code — it is entirely left to the LLM inside browser-use. The fix is not to rewrite browser_agent but to update the SKILL.md to enforce this workflow when the agent uses the skill directly via CDP (not browser-use).

---

## CDP Control: Modified vs. New Components

### MODIFY: `usr/skills/shared-browser/SKILL.md`

**What:** Add explicit Observe → Act → Verify section with CDP-based navigation that is separate from the xdotool fallback. Current SKILL.md already documents `Page.navigate` but lacks the verification step — it says to screenshot after but does not show how to verify URL/title.

**Change scope:** Add a "Navigation with Verification" pattern section showing:
1. `scrot` → `vision_load` (observe)
2. CDP `Page.navigate`
3. `time.sleep(2)` then CDP `Runtime.evaluate({expression: '({url: location.href, title: document.title})'})` (verify)
4. Screenshot (confirm visually)

This is a documentation-only change to an existing SKILL.md file. No Python code changes.

### MODIFY: `apps/shared-browser/startup.sh`

**What:** Add an explicit readiness check after Chromium starts — currently `sleep 2` is the only guard. Replace with a loop that polls `http://localhost:9222/json` until it returns HTTP 200, with a timeout and clear error message.

**Change scope:** 10-line bash modification. No Python changes.

### NO CHANGE: `python/tools/browser_agent.py`

The Playwright/browser-use integration is not the primary path for CDP control. SKILL.md directs agents to use CDP Python directly (via `code_execution_tool` running Python WebSocket code), not via browser_agent. browser_agent is for the browser-use AI sub-agent path. The `_wait_for_cdp()` helper and `--remote-allow-origins=*` flag path are already correct. The remaining issues are skill documentation and startup robustness.

---

## Claude CLI Control: Component Analysis

### New Component: `usr/skills/claude-cli/SKILL.md`

This is the primary deliverable for CLAUDE-01 through CLAUDE-05. No Python tool changes are needed because `terminal_agent` and `code_execution_tool` already provide all necessary primitives.

**Why a SKILL.md (not a new Tool class):**
- The claude CLI is an interactive process, not a single-shot command. Its interaction pattern is: launch → read prompt → send input → read response → repeat.
- `terminal_agent` handles single commands with a marker/sentinel. It is not designed for multi-turn interactive processes.
- `code_execution_tool` with a persistent LocalInteractiveSession IS the correct mechanism for interactive CLI programs — the session persists between calls, and output is read incrementally.
- The skill documents the exact `code_execution_tool` invocation sequences to launch claude, detect when it has finished responding, and send follow-up prompts.

**What the skill must document:**

```
Launch:
  code_execution_tool runtime=terminal
  code=`claude --no-pager --model claude-opus-4-6 -p "your prompt"`

For one-shot (non-interactive):
  Above is sufficient. Claude prints response to stdout and exits.

For multi-turn (interactive session):
  Use code_execution_tool runtime=terminal with persistent session.
  claude CLI enters interactive REPL mode when stdin is a TTY.
  In a LocalInteractiveSession, stdin IS a pseudo-TTY.
  Invoke: `claude` (no -p flag)
  Claude will print a prompt marker (e.g., "> " or "Human:").
  Detect: read output until between_output_timeout fires (idle = done).
  Send: session.send_command("your next message")
  Read: get_terminal_output() again.
```

**Detection mechanism for "claude has finished responding":**
The existing `code_execution_tool.get_terminal_output()` loop already handles this via `between_output_timeout` (default 15s) — when claude stops producing output for 15 seconds, the tool returns. The skill should document this behavior and recommend using `runtime=output` on the same session ID to poll for completion without re-sending a command.

**Subprocess alternative for one-shot (CLAUDE-01/CLAUDE-02):**
For simple one-shot use cases, the skill can document running `claude -p "prompt"` via `code_execution_tool runtime=terminal`. This is the simplest path and does not require interactive session management.

---

## Recommended Project Structure (Changes Only)

```
agent-zero/
├── apps/
│   └── shared-browser/
│       └── startup.sh           MODIFY: add CDP readiness poll loop
├── usr/
│   └── skills/
│       ├── shared-browser/
│       │   └── SKILL.md         MODIFY: add navigate-with-verify pattern
│       └── claude-cli/          NEW directory
│           └── SKILL.md         NEW: documents claude CLI interaction
```

No changes to `python/tools/`. No new Tool classes. No new Flask endpoints.

---

## Data Flow

### CDP Browser Control Flow (Fixed)

```
Agent needs to navigate browser
    ↓
skills_tool:load → shared-browser SKILL.md into context
    ↓
Agent generates CDP Python code using SKILL.md patterns
    ↓
code_execution_tool runtime=python
    ↓ (Python inside LocalInteractiveSession)
import websocket, urllib.request
tabs = json.loads(urlopen('http://localhost:9222/json').read())
ws = websocket.create_connection(tabs[0]['webSocketDebuggerUrl'])
send('Page.navigate', {'url': url})
    ↓ (verify step — NEW in SKILL.md)
result = send('Runtime.evaluate', {'expression': '({url:location.href,title:document.title})', 'returnByValue':True})
    ↓
scrot → vision_load (screenshot verify)
    ↓
Response to agent with URL + title confirmation
```

### Claude CLI One-Shot Flow

```
Agent wants to run claude with a prompt
    ↓
skills_tool:load → claude-cli SKILL.md into context
    ↓
code_execution_tool runtime=terminal
    code=`claude --no-pager -p "the prompt"`
    ↓ (LocalInteractiveSession runs command, reads stdout)
get_terminal_output() loops until shell prompt detected
    ↓
Full claude response returned as tool result to agent
```

### Claude CLI Multi-Turn Flow

```
Agent starts interactive session
    ↓
code_execution_tool runtime=terminal session=1
    code=`claude`  (no -p; enters REPL)
    ↓
get_terminal_output() returns after between_output_timeout (claude idle)
    → agent reads first response / greeting
    ↓
code_execution_tool runtime=terminal session=1 allow_running=True
    code=`next message to claude`
    ↓
get_terminal_output() returns when claude finishes second response
    ↓
Repeat for additional turns (same session ID)
```

---

## Integration Points

### How SKILL.md Content Reaches the Agent

The skills system injects content at two points:

1. **Available skills list:** `agent.system.skills.md` shows all skill names/descriptions in the system prompt so the agent knows what skills exist.
2. **Loaded skill content:** When `skills_tool:load` is called, the SKILL.md content is added to `agent.data["loaded_skills"]` (max 5 skills). `agent.system.skills.loaded.md` renders this into the system extras section each turn.

This means the claude-cli SKILL.md content is NOT in context until the agent explicitly loads it. The agent discovers it exists from the skills list (name + description + tags).

### Tool ↔ Tool Interactions

| From | To | Mechanism | Notes |
|------|----|-----------|-------|
| browser_agent (use_shared) | shared-browser app | CDP WebSocket via Playwright cdp_url | Playwright connects to port 9222 |
| SKILL.md (CDP pattern) | shared-browser Chromium | Python websocket in code_execution_tool | Direct WebSocket, no Flask proxy |
| terminal_agent | tmux shared session | subprocess tmux send-keys | Single-shot sentinel pattern |
| code_execution_tool | LocalInteractiveSession | PTY-based shell | Persistent; multi-turn via session IDs |
| skills_tool | usr/skills/*/SKILL.md | File read at load time | Content injected into context extras |
| browser_agent (auto-start) | AppManager | mgr.start_app("shared-browser") | Triggers startup.sh |

### Critical Boundary: CDP Direct vs. Flask Bridge vs. Playwright

There are three separate paths to Chromium:

1. **Flask bridge (app.py /api/*)**: Used by the browser UI for human interaction. The agent does NOT use this path directly.
2. **CDP WebSocket direct (skill pattern)**: Used by agent-generated Python code via code_execution_tool. Connects to `ws://localhost:9222/devtools/page/...`. Fast, programmatic.
3. **Playwright via browser-use (browser_agent tool)**: Used for AI-driven browsing tasks. Playwright is a wrapper over CDP. Used when the task requires the browser-use AI sub-agent to make decisions.

The skill (shared-browser/SKILL.md) documents path 2. The browser_agent tool uses path 3. These do not conflict — they connect to separate WebSocket instances per the CDP spec (each debug client gets its own connection).

---

## Architectural Patterns

### Pattern 1: Skill-Documented Tool Composition

**What:** Complex multi-step interactions (CDP sequences, CLI sessions) are documented as SKILL.md content rather than implemented as new Tool classes. The agent assembles the interaction from existing primitives (code_execution_tool, vision_load) guided by the skill.

**When to use:** When the complexity is in the sequence and knowledge, not in the Python plumbing. Both CDP browser control and claude CLI fit this — the underlying I/O mechanisms already exist.

**Trade-offs:** Pro: no Python deployment changes, fully inspectable by agent, easy to iterate. Con: agent must load the skill explicitly; skill content is token-heavy.

### Pattern 2: Sentinel-Based Completion Detection

**What:** A unique string marker is appended to commands (`echo "MARKER:$?"`). Output is polled until the marker appears. This is how terminal_agent works.

**When to use:** Single-shot commands where exact completion time matters. Works well for deterministic programs.

**Trade-offs:** Breaks for interactive programs that do not return to a shell prompt.

### Pattern 3: Timeout-Based Idle Detection

**What:** code_execution_tool's `between_output_timeout` returns when output stops for N seconds. This is how the multi-turn claude session works — "idle for 15s = done responding."

**When to use:** Interactive programs (claude CLI, REPLs, long-running commands) where a shell prompt never appears.

**Trade-offs:** Risk of false early returns if claude is slow to respond. The skill should recommend raising timeout for long prompts.

---

## Build Order

The two workstreams (CDP browser fixes and claude CLI skill) are independent and can be built in parallel. However, within each stream there is a dependency order.

### Stream 1: CDP Browser Fixes

```
Step 1: MODIFY startup.sh — add CDP readiness poll
  (Unblocks everything; ensures Chromium is ready before any CDP client connects)

Step 2: MODIFY shared-browser/SKILL.md — add navigate-with-verify pattern
  (Documents the Observe → Act → Verify workflow for agent use)

No Step 3 needed — browser_agent.py already has correct CDP connection logic
```

### Stream 2: Claude CLI Skill

```
Step 1: CREATE usr/skills/claude-cli/SKILL.md — one-shot pattern
  (CLAUDE-01, CLAUDE-02: launch + send prompt + receive response)

Step 2: EXTEND SKILL.md — add completion detection section
  (CLAUDE-03: how to detect claude finished responding)

Step 3: EXTEND SKILL.md — add multi-turn session section
  (CLAUDE-04: complete multi-turn pattern using persistent code_execution_tool session)

Note: Steps 1-3 are all in the same file. The skill can be written in one pass
once the interaction pattern is verified manually via code_execution_tool.
```

### Recommended Overall Order

1. Verify `startup.sh` CDP readiness (manual test: does it error if Chromium takes 5s to start?)
2. Fix `startup.sh` poll loop
3. Manually test claude CLI invocation via code_execution_tool to confirm interaction pattern
4. Write `claude-cli/SKILL.md` from confirmed patterns
5. Update `shared-browser/SKILL.md` with navigate-verify pattern
6. Test both skills end-to-end from agent context

Step 3 (manual claude CLI verification) is the highest-risk item — the exact behavior of claude CLI in a PTY vs. non-TTY context, and the prompt/response detection pattern, must be confirmed empirically before writing the skill.

---

## Anti-Patterns

### Anti-Pattern 1: New Tool Class for Claude CLI

**What people do:** Create `python/tools/claude_agent.py` mirroring browser_agent.py for claude CLI interaction.

**Why it's wrong:** code_execution_tool already provides persistent interactive sessions with PTY. A new tool class would duplicate this infrastructure, add Python deployment risk, and be harder to modify without restarting Agent Zero. The interaction complexity is in the knowledge (what flags, how to detect completion), not in the I/O plumbing.

**Do this instead:** SKILL.md that guides the agent to use `code_execution_tool` with the right session ID and timeout settings.

### Anti-Pattern 2: Using terminal_agent for Multi-Turn Claude Sessions

**What people do:** Use `terminal_agent` (tmux send-keys) to launch and interact with claude CLI.

**Why it's wrong:** terminal_agent's sentinel pattern (`echo "MARKER:$?"`) appends to the command. For claude CLI, this would inject `echo MARKER` as input to claude, producing garbage. Also, tmux capture-pane reads from a scrollback buffer which does not cleanly separate claude's output from previous session content.

**Do this instead:** `code_execution_tool` with a dedicated session number. The PTY and prompt-detection loop in LocalInteractiveSession handle interactive programs correctly.

### Anti-Pattern 3: Hardcoding CDP Tab Index

**What people do:** Always connect to `tabs[0]` in CDP, assuming the first tab is the right one.

**Why it's wrong:** Chromium may have multiple tabs. If the agent has opened additional tabs (via `Target.createTarget`), tabs[0] may not be the active page.

**Do this instead:** Filter for `type == 'page'` tabs and either use the most recently activated one (via `Page.getFrameTree` or checking `webSocketDebuggerUrl` ordering) or document that the agent should track which tab it opened. The current SKILL.md already does this correctly: `page_tabs = [t for t in tabs if t.get('type') == 'page']`.

### Anti-Pattern 4: Skipping CDP Verification After Navigation

**What people do:** Call `Page.navigate` and immediately proceed with actions, assuming the page loaded.

**Why it's wrong:** `Page.navigate` returns when the navigation is initiated, not when the page is loaded. Fast DOM actions on a loading page will fail silently or interact with the old page.

**Do this instead:** After `Page.navigate`, either: (a) sleep 1-2s then verify via `Runtime.evaluate` on `document.readyState` and `location.href`, or (b) listen for `Page.loadEventFired` before acting. The skill should document option (a) as the simpler pattern.

---

## Scaling Considerations

This is a single-user local tool. Scaling is not relevant. The only resource concern is:

| Concern | Current | Risk |
|---------|---------|------|
| CDP WebSocket connections | One per code_execution_tool call (opened and closed) | Low — websocket.close() is documented in skill |
| claude CLI processes | One per session, terminated when terminal_agent/code_execution_tool session ends | Low — process lifecycle tied to session |
| Chromium memory | Single Chromium instance shared across all agent calls | Medium — if Chromium crashes, all browser ops fail. The `_wait_for_cdp()` readiness check and startup.sh fix address this |

---

## Sources

- Direct inspection of `python/tools/browser_agent.py` (codebase, 2026-02-25)
- Direct inspection of `python/tools/terminal_agent.py` (codebase, 2026-02-25)
- Direct inspection of `python/tools/code_execution_tool.py` (codebase, 2026-02-25)
- Direct inspection of `python/tools/skills_tool.py` (codebase, 2026-02-25)
- Direct inspection of `python/helpers/tool.py` (codebase, 2026-02-25)
- Direct inspection of `apps/shared-browser/startup.sh` (codebase, 2026-02-25)
- Direct inspection of `apps/shared-browser/app.py` (codebase, 2026-02-25)
- Direct inspection of `usr/skills/shared-browser/SKILL.md` v3.0 (codebase, 2026-02-25)
- Direct inspection of `prompts/agent.system.tool.browser.md` (codebase, 2026-02-25)
- Direct inspection of `prompts/agent.system.tool.terminal.md` (codebase, 2026-02-25)

---

*Architecture research for: Agent Zero fork — CDP browser control and claude CLI integration*
*Researched: 2026-02-25*
