# Architecture Research

**Domain:** Agent Zero fork — tmux terminal orchestration + interactive CLI integration (v1.2)
**Researched:** 2026-02-25
**Confidence:** HIGH (all findings from direct codebase inspection)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Agent Zero Core (FastAPI)                              │
│   agent.py message loop → get_tool(name) → tool.execute() → Response           │
│   Tool dispatch: subagents.get_paths() searches usr/tools/, python/tools/       │
├──────────────┬──────────────────┬──────────────────┬───────────────────────────┤
│ terminal_    │  tmux_tool       │  code_execution  │  skills_tool              │
│ agent.py     │  (NEW Tool class)│  _tool.py        │                           │
│ (EXISTING)   │                  │  (EXISTING)      │  loads SKILL.md           │
│              │                  │                  │  into context             │
│ single-shot  │  send-keys       │  LocalInteractive│                           │
│ sentinel     │  capture-pane    │  Session / SSH   │                           │
│ pattern      │  special keys    │  full PTY        │                           │
│              │  prompt detect   │                  │                           │
└──────┬───────┴────────┬─────────┴──────────────────┴──────────────┬────────────┘
       │                │                                             │
       ▼                ▼                                             ▼
┌──────────────────────────────────────┐                  ┌──────────────────────┐
│         Shared Terminal App          │                  │  usr/skills/         │
│  startup.sh: tmux new-session -d -s shared              │  cli-orchestration/  │
│  ttyd --port 9004 tmux new-session -A -s shared         │    SKILL.md (NEW)    │
│                                      │                  │  claude-cli/         │
│  tmux session "shared"               │                  │    SKILL.md          │
│  pane target: shared:0.0             │                  └──────────────────────┘
│  visible to user in UI drawer        │
└──────────────────────────────────────┘
         │  tmux CLI (subprocess)
         │  send-keys / capture-pane / send-keys Ctrl+C
         ▼
┌──────────────────────────────────────┐
│  opencode_session() helper           │
│  python/helpers/opencode_cli.py      │
│  (NEW — mirrors claude_cli.py        │
│   pattern with tmux backend)         │
└──────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `terminal_agent.py` (existing Tool) | Single-shot commands with sentinel completion; visible to user | Subprocess tmux send-keys + capture-pane poll |
| `tmux_tool.py` (NEW Tool) | Multi-operation tmux control: send text, send special keys, read screen, detect prompt readiness | New Tool class in `python/tools/`; wraps subprocess tmux calls |
| `python/helpers/opencode_cli.py` (NEW helper) | Pre-built OpenCode CLI orchestration; mirrors ClaudeSession pattern from claude_cli.py | Pure Python helper; not a Tool class; called from skill code or tmux_tool |
| `code_execution_tool.py` (existing Tool) | Private PTY shells for Agent Zero's own code/command execution; NOT the shared terminal | LocalInteractiveSession; multiple sessions by ID |
| `skills_tool.py` (existing Tool) | Lists and loads SKILL.md files into agent context | Reads usr/skills/; populates agent.data["loaded_skills"] |
| `apps/shared-terminal/startup.sh` (existing) | Starts persistent tmux session "shared" + ttyd web terminal | bash script; pre-creates `tmux new-session -d -s shared` |
| `usr/skills/cli-orchestration/SKILL.md` (NEW) | Documents complete Read-Detect-Write-Verify cycle for any CLI; OpenCode-specific pattern | Markdown loaded via skills_tool |

---

## What Already Exists vs. What Is New

### EXISTING — No Changes Needed

**`python/tools/terminal_agent.py`** — already uses tmux send-keys + sentinel. Covers TERM-01 for simple commands. NOT suitable for interactive CLIs (sentinel appended to command would be fed as input to the CLI program).

**`apps/shared-terminal/startup.sh`** — already pre-creates `tmux new-session -d -s shared` before ttyd starts. The tmux session exists before any browser or agent connects. No changes needed.

**`python/helpers/claude_cli.py` + `ClaudeSession`** — the multi-turn session model. `opencode_session()` will follow this exact pattern but with a tmux backend instead of subprocess.run.

**`python/helpers/tty_session.py`** — correct primitive for private PTY sessions (code_execution_tool). Not used for the shared terminal.

### EXISTING — Terminal Agent Gap Analysis

`terminal_agent.py` does TERM-01 (send text + Enter) but has these gaps for TERM-02 through CLI-06:

| Requirement | terminal_agent | Gap |
|-------------|---------------|-----|
| TERM-02: send without Enter | Uses "Enter" hardcoded | No `enter=False` mode |
| TERM-03: special keys (Ctrl+C, Tab) | Not implemented | tmux send-keys literal mode needed |
| TERM-04: capture screen | Embedded in sentinel loop only | No standalone capture |
| TERM-05: prompt detection | Sentinel-only; no pattern matching | No idle+pattern detection |
| CLI-01..06: interactive CLI | sentinel breaks interactive programs | Wrong tool entirely |

### NEW — `python/tools/tmux_tool.py`

New Tool class. Reason for a Tool class (not skill-only): the tmux operations require subcommand dispatch, state (pane target, last-read cursor), and timeout management that cannot be cleanly expressed as skill-directed code_execution_tool calls. A Tool class also appears in the system prompt as a first-class tool the agent can call directly.

**Methods the Tool exposes:**

```
tmux_tool:send        — send text to pane (enter=true/false)
tmux_tool:keys        — send special keys: Ctrl+C, Ctrl+D, Tab, arrows, Escape
tmux_tool:read        — capture current pane screen (capture-pane -p)
tmux_tool:wait_ready  — poll until prompt pattern matches or idle timeout fires
```

**Why not extend terminal_agent?** Extending terminal_agent would break its sentinel contract and make the code harder to reason about. A separate tmux_tool with explicit subcommands is cleaner. Both tools coexist — terminal_agent for visible single-shot commands, tmux_tool for interactive CLI orchestration.

### NEW — `prompts/agent.system.tool.tmux.md`

Tool prompt file for tmux_tool. The tools system automatically picks up all `agent.system.tool.*.md` files from the prompts directory (confirmed by reading `agent.system.tools.py`). No other registration step needed.

### NEW — `python/helpers/opencode_cli.py`

Mirrors the structure of `claude_cli.py`. Wraps OpenCode interactive CLI sessions via tmux. Called from skill code or from tmux_tool's higher-level session management. Provides `OpenCodeSession` class with `.start()`, `.send(prompt)`, `.read_response()`, `.interrupt()`, `.exit()`.

### NEW — `usr/skills/cli-orchestration/SKILL.md`

Documents the complete CLI orchestration pattern — generic (any CLI tool) and OpenCode-specific. References tmux_tool subcommands. Documents the Read-Detect-Write-Verify cycle.

---

## Recommended Project Structure (Changes Only)

```
agent-zero/
├── python/
│   ├── tools/
│   │   └── tmux_tool.py           NEW: Tool class for tmux interaction
│   └── helpers/
│       └── opencode_cli.py        NEW: OpenCode CLI session wrapper (mirrors claude_cli.py)
├── prompts/
│   └── agent.system.tool.tmux.md  NEW: Tool prompt (auto-discovered by tools.py)
└── usr/
    └── skills/
        └── cli-orchestration/
            └── SKILL.md           NEW: CLI orchestration skill doc
```

No changes to existing files. `terminal_agent.py`, `startup.sh`, and `code_execution_tool.py` are unchanged.

---

## Data Flow

### TERM-01 through TERM-05: tmux_tool Data Flow

```
Agent wants to interact with shared terminal
    ↓
tmux_tool:send  {"text": "opencode", "enter": true}
    ↓ (subprocess)
tmux send-keys -t shared "opencode" Enter
    ↓ (wait for CLI to start)
tmux_tool:wait_ready  {"pattern": "> ", "timeout": 10}
    ↓ (poll loop)
while time < deadline:
    tmux capture-pane -t shared -p
    check last lines for pattern match
    OR check if output stopped for idle_seconds
    ↓ (ready)
Response: "ready" + captured screen snapshot
```

### CLI-01 through CLI-05: Interactive CLI Session Flow (Read-Detect-Write-Verify)

```
Agent wants to start OpenCode session
    ↓
tmux_tool:send  {"text": "opencode", "enter": true}
    ↓
tmux_tool:wait_ready  {"pattern": "> |◆", "timeout": 15}
    ← Response: screen content showing OpenCode prompt
                                    [READ]
    ↓ (agent DETECTS ready state)
                                    [DETECT]
tmux_tool:send  {"text": "refactor this function", "enter": true}
                                    [WRITE]
    ↓
tmux_tool:wait_ready  {"pattern": "> |◆", "timeout": 120, "idle_seconds": 5}
    ← Response: screen content with OpenCode response
                                    [VERIFY]
    ↓ (agent reads response, continues or exits)
tmux_tool:keys  {"keys": "Ctrl+C"}   ← interrupt if needed
tmux_tool:send  {"text": "exit", "enter": true}
```

### CLI-05: OpenCode via opencode_cli.py Helper

```
Agent code (in code_execution_tool runtime=python):
    sys.path.insert(0, '/a0')
    from python.helpers.opencode_cli import OpenCodeSession

    session = OpenCodeSession()
    session.start()                     # tmux send-keys "opencode" Enter + wait_ready
    r1 = session.send("write a test")  # send + wait_ready → returns response text
    r2 = session.send("add docstrings") # next turn, same session
    session.exit()                      # Ctrl+C or "exit" + Enter
```

### Skill-Directed Flow (CLI-06)

```
Agent loads skill:  skills_tool:load → "cli-orchestration"
    ↓ (SKILL.md injected into context extras)
Agent reads SKILL.md → learns Read-Detect-Write-Verify cycle
Agent generates tmux_tool calls directly
    ↓
tmux_tool:read → observe current state
tmux_tool:send / tmux_tool:keys → act
tmux_tool:wait_ready → verify ready
    ↓
Response returned to agent
```

---

## Integration Points

### How tmux_tool Fits Into Tool Dispatch

Tool names map to filenames: `tool_name: "tmux_tool"` → `python/tools/tmux_tool.py`. The agent's `get_tool()` method calls `subagents.get_paths(agent, "tools", "tmux_tool.py", default_root="python")`, which finds the file in `python/tools/`. No registration table, no factory, no imports in agent.py required. Drop the file in, write the prompt, done.

### How tmux_tool Appears in the System Prompt

`prompts/agent.system.tools.py` dynamically assembles the tools section by reading all `agent.system.tool.*.md` files from the prompts directory. Creating `agent.system.tool.tmux.md` is the only registration step needed. The tools section is rebuilt each inference turn.

### tmux_tool ↔ Shared Terminal Session

The shared terminal always uses session name `"shared"` (confirmed in `terminal_agent.py`: `_TMUX_SESSION = "shared"`). tmux_tool targets `shared:0.0` (window 0, pane 0) by default. The pane is pre-created by `startup.sh` before any agent or browser connects. No setup handshake needed.

### tmux_tool ↔ terminal_agent Coexistence

Both tools write to the same tmux pane. They do not conflict as long as they are not called simultaneously from different agents. The sentinel in terminal_agent (`echo "MARKER:$?"`) cannot appear in tmux_tool flows because tmux_tool never uses sentinel markers — it uses prompt pattern detection and idle timeout instead.

**When to use which:**

| Scenario | Tool |
|----------|------|
| Run a command the user should see, get exit code | terminal_agent |
| Start an interactive CLI, send prompts, read responses | tmux_tool |
| Send Ctrl+C or special keys | tmux_tool:keys |
| Capture current screen state | tmux_tool:read |
| Private shell (not shared terminal) | code_execution_tool |

### opencode_cli.py ↔ tmux_tool

`opencode_cli.py` is a Python helper that internally calls `subprocess.run(["tmux", ...])` directly — the same calls tmux_tool makes. It is NOT a Tool class. It is callable from `code_execution_tool runtime=python` skill code. It mirrors `claude_cli.py`'s `ClaudeSession` interface so the two patterns look identical to the agent:

```python
# claude_cli.py pattern (v1.1)
session = ClaudeSession()
r = session.turn("prompt")

# opencode_cli.py pattern (v1.2)
session = OpenCodeSession()
session.start()
r = session.send("prompt")
```

### Prompt Detection: Shared State Problem

Both tmux_tool and opencode_cli.py call `tmux capture-pane` independently. They read the same pane but do not share a cursor position. This means if the agent calls `tmux_tool:read` and separately calls opencode_cli.py, they both see the full scrollback. This is fine — both read from the same source and use the same prompt detection logic. There is no cursor advancement; reads are idempotent.

---

## Architectural Patterns

### Pattern 1: Prompt-Pattern + Idle-Timeout Dual Detection

**What:** After sending a command, poll capture-pane output in a loop. Declare "done" when either (a) the last line matches a prompt regex (fast path, ~instant), or (b) no new output has appeared for `idle_seconds` (fallback for programs without a predictable prompt).

**When to use:** Any interactive CLI where you need to detect readiness for next input. Use this in both tmux_tool:wait_ready and opencode_cli.py's read_response().

**Trade-offs:**
- Pro: handles CLIs with unpredictable prompts (idle fallback)
- Pro: fast for CLIs with known prompts (pattern match)
- Con: idle timeout is speculative — too short → false positive (returns before CLI finishes); too long → unnecessarily slow
- Mitigation: make idle_seconds configurable per-call; document that slow AI CLIs need 5-10s

**Example:**
```python
deadline = time.time() + timeout
last_output = ""
last_change = time.time()

while time.time() < deadline:
    cap = subprocess.run(["tmux", "capture-pane", "-t", "shared", "-p", "-S", "-200"],
                         capture_output=True, text=True)
    screen = cap.stdout
    if screen != last_output:
        last_output = screen
        last_change = time.time()
    # Fast path: known prompt pattern
    last_lines = screen.strip().splitlines()[-3:]
    for line in reversed(last_lines):
        if re.search(prompt_pattern, line):
            return screen
    # Fallback: idle timeout
    if time.time() - last_change > idle_seconds:
        return screen
    time.sleep(poll_interval)

return screen  # hard timeout — return whatever is on screen
```

### Pattern 2: tmux Pane Target Addressing

**What:** All tmux CLI calls target a specific pane using `-t session:window.pane` format. Use `"shared"` (shorthand for `shared:0.0`) consistently. Never use bare session name when window/pane matters.

**When to use:** Every `tmux send-keys` and `tmux capture-pane` call.

**Trade-offs:**
- Pro: explicit, survives window creation events
- Con: breaks if user creates extra windows (unlikely for shared-terminal which opens in window 0)

### Pattern 3: Skill-First, Tool-Second

**What:** Document the full interaction pattern in SKILL.md first. The tmux_tool exposes primitives (send, keys, read, wait_ready). The SKILL.md documents when and how to compose them into a CLI orchestration workflow. The agent calls the primitives guided by the skill.

**When to use:** For CLI-06 (generic pattern) and all OpenCode interactions.

**Trade-offs:**
- Pro: skill is inspectable, agent can adapt to edge cases not covered by opencode_cli.py
- Con: agent must load the skill first; adds token cost

### Pattern 4: ClaudeSession-Style Wrapper for CLI Tools

**What:** For well-known CLIs (OpenCode), provide a Python class (opencode_cli.py) that hides tmux plumbing. Interface matches ClaudeSession: `.start()`, `.send(prompt)` → response, `.exit()`. Called from code_execution_tool Python runtime.

**When to use:** CLI-05 (OpenCode wrapper). Any CLI with a stable prompt pattern.

**Trade-offs:**
- Pro: clean interface; no tmux knowledge required in skill code
- Con: hides errors; prompt pattern must be known in advance
- Con: does not work for CLIs with variable prompts → fall back to tmux_tool direct

---

## Build Order

Dependencies run in a strict sequence within the terminal orchestration stream. The stream is independent of any v1.1 work.

```
Step 1: python/tools/tmux_tool.py + prompts/agent.system.tool.tmux.md
        (TERM-01, TERM-02, TERM-03, TERM-04)
        Prerequisite for everything else.
        Verify: agent can send text, send Ctrl+C, capture pane output.

Step 2: Prompt detection in tmux_tool:wait_ready
        (TERM-05)
        Depends on Step 1 (needs capture-pane working).
        Verify: wait_ready returns when shell prompt appears, and on idle timeout.

Step 3: CLI-01 through CLI-04 — interactive CLI session via tmux_tool
        (CLI-01: start OpenCode, CLI-02: send prompts + read responses,
         CLI-03: detect done, CLI-04: interrupt/exit)
        Depends on Step 2 (wait_ready is the completion detector).
        Empirical: run OpenCode manually in shared terminal; capture exact prompt
        pattern bytes before writing detection regex. This is the high-risk step.

Step 4: python/helpers/opencode_cli.py — OpenCode wrapper
        (CLI-05)
        Depends on Step 3 (patterns validated).
        Mirrors claude_cli.py's ClaudeSession interface.

Step 5: usr/skills/cli-orchestration/SKILL.md
        (CLI-06)
        Depends on Steps 3 and 4 (documents validated patterns only).
        Always written last.
```

**Rationale for this order:**

- Steps 1-2 are pure infrastructure; they have no dependency on any specific CLI behavior.
- Step 3 (interactive CLI) is the empirical step where the actual OpenCode prompt format, startup time, and response boundary must be confirmed manually before coding detection logic.
- Step 4 (OpenCode wrapper) must come after Step 3 because the wrapper encodes the prompt pattern — writing it before empirical validation would embed untested assumptions.
- Step 5 (skill doc) is always last. Skill documents must reflect confirmed behavior.

---

## New vs. Modified Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `python/tools/tmux_tool.py` | NEW | Tool class for tmux send/keys/read/wait_ready |
| `prompts/agent.system.tool.tmux.md` | NEW | Tool registration in system prompt |
| `python/helpers/opencode_cli.py` | NEW | OpenCode session wrapper (ClaudeSession pattern) |
| `usr/skills/cli-orchestration/SKILL.md` | NEW | CLI orchestration patterns for agent consumption |
| `python/tools/terminal_agent.py` | NO CHANGE | Existing single-shot tool unchanged |
| `apps/shared-terminal/startup.sh` | NO CHANGE | Session creation already correct |
| `python/helpers/tty_session.py` | NO CHANGE | Private PTY helper, not used for shared terminal |
| `python/helpers/claude_cli.py` | NO CHANGE | v1.1 pattern; opencode_cli.py mirrors it |

---

## Anti-Patterns

### Anti-Pattern 1: Using terminal_agent for Interactive CLI Sessions

**What people do:** Call `terminal_agent` with `command: "opencode"` expecting to have an interactive session.

**Why it's wrong:** terminal_agent appends `; echo "MARKER:$?"` to every command. For an interactive CLI, this sends "; echo ..." as input to the CLI, producing garbage. Also, terminal_agent has no mechanism for follow-up sends to the same running process — it sends one command and polls for the sentinel.

**Do this instead:** Use `tmux_tool:send` to start the CLI, `tmux_tool:wait_ready` to detect startup, then `tmux_tool:send` for each subsequent prompt.

### Anti-Pattern 2: Using code_execution_tool for Shared Terminal Interaction

**What people do:** Run `opencode` via `code_execution_tool runtime=terminal`, treating it like a local PTY process.

**Why it's wrong:** code_execution_tool creates a *private* LocalInteractiveSession — an isolated PTY process that the user cannot see in the shared terminal drawer. OpenCode running in code_execution_tool is invisible to the user. Also, code_execution_tool's `between_output_timeout` was tuned for code execution (15s), not for AI CLI response times which can be 30-120s.

**Do this instead:** Use `tmux_tool` to run OpenCode in the shared terminal (visible to user), or use `opencode_cli.py` which also uses the shared terminal via tmux.

### Anti-Pattern 3: Hardcoded Idle Timeout for AI CLIs

**What people do:** Use a fixed 5-second idle timeout for wait_ready, assuming that's enough for OpenCode to respond.

**Why it's wrong:** AI CLI tools like OpenCode call the Anthropic API, which can take 5-60 seconds to return. A 5-second idle timeout causes false "done" signals mid-response.

**Do this instead:** Default `idle_seconds=10` minimum for AI CLIs; allow per-call override. Combine with prompt pattern detection — if the prompt appears before the idle timeout, return immediately without waiting the full duration.

### Anti-Pattern 4: Reading Stale Scrollback as Current State

**What people do:** Call `tmux capture-pane` and treat the full scrollback as the current response, not distinguishing between output from the current turn and previous turns.

**Why it's wrong:** tmux capture-pane with `-S -N` returns up to N lines of scrollback, including all prior session output. If the agent sent a command 3 turns ago, that output is still in the scrollback.

**Do this instead:** Track a "last read position" by recording a unique marker sent before each new command, then extracting only output after that marker. Or limit the scrollback window to the lines produced since the last send (use `-S -50` rather than `-S -500` when response is expected to be short).

### Anti-Pattern 5: New Tool Class for OpenCode with Embedded TTY Session

**What people do:** Create `python/tools/opencode_tool.py` that spawns opencode as a child process via TTYSession (similar to code_execution_tool).

**Why it's wrong:** This makes OpenCode invisible to the user (runs in a hidden PTY). The whole point of CLI-01 through CLI-06 is that the user can watch the shared terminal while the agent operates it. Shared terminal visibility requires running in the tmux session.

**Do this instead:** tmux_tool + opencode_cli.py, both using the shared tmux session.

---

## Scaling Considerations

This is a single-user local tool. Scaling is not a concern. The only resource issue is:

| Concern | Reality | Risk |
|---------|---------|------|
| Multiple agents writing to same tmux pane | Concurrent sends would interleave output | Low — Agent Zero is typically single-threaded per conversation |
| OpenCode long response blocking tmux_tool:wait_ready | Waits up to `timeout` seconds, blocking the agent | Medium — set generous timeout (120s); agent cannot do other terminal work during wait |
| tmux session not existing when tmux_tool sends | `tmux send-keys -t shared` fails if session missing | Low — startup.sh pre-creates "shared"; shared-terminal app restarts on failure |

---

## Sources

- Direct inspection of `python/tools/terminal_agent.py` — tmux_SESSION = "shared", sentinel pattern confirmed
- Direct inspection of `python/tools/code_execution_tool.py` — LocalInteractiveSession, between_output_timeout, session IDs
- Direct inspection of `python/helpers/tty_session.py` — PTY subprocess control (private sessions only)
- Direct inspection of `python/helpers/shell_local.py` — wraps TTYSession for code_execution_tool
- Direct inspection of `python/helpers/claude_cli.py` — ClaudeSession pattern; opencode_cli.py will mirror this
- Direct inspection of `python/helpers/tool.py` — Tool base class: execute(), before_execution(), after_execution()
- Direct inspection of `python/helpers/subagents.py` — get_paths(): tool resolution order (usr/tools/, python/tools/)
- Direct inspection of `python/helpers/extract_tools.py` — load_classes_from_file(): how tool classes are found
- Direct inspection of `agent.py` lines 974-1000 — get_tool(): full dispatch chain confirmed
- Direct inspection of `prompts/agent.system.tools.py` — auto-discovery of agent.system.tool.*.md files confirmed
- Direct inspection of `prompts/agent.system.tool.terminal.md` — terminal_agent system prompt format (model for tmux.md)
- Direct inspection of `apps/shared-terminal/startup.sh` — pre-creates "shared" session; ttyd -A flag confirmed
- Direct inspection of `.planning/PROJECT.md` — TERM-01..05 and CLI-01..06 requirements

---

*Architecture research for: Agent Zero fork — tmux terminal orchestration (v1.2)*
*Researched: 2026-02-25*
