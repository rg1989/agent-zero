---
phase: 14-opencode-session-wrapper
plan: 01
subsystem: infra
tags: [opencode, tmux, cli, tui, python, docker]

# Dependency graph
requires:
  - phase: 13-02
    provides: OPENCODE_PROMPT_PATTERN and OPENCODE_START_TIMEOUT constants in tmux_tool.py; empirically verified Ctrl+P exit sequence and lifecycle timing for OpenCode v1.2.14

provides:
  - OpenCodeSession class in python/helpers/opencode_cli.py with .start()/.send()/.exit() interface
  - CLI-05 requirement satisfied: skill code orchestrates full OpenCode lifecycle without direct tmux knowledge
  - End-to-end validated multi-turn session: start() → send() → send() → exit() all succeed against live OpenCode v1.2.14

affects: [15-opencode-skill-doc, any skill using OpenCode sessions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - OpenCodeSession sync class pattern: mirrors ClaudeSession from claude_cli.py but wraps tmux subprocess calls (not opencode binary subprocess)
    - Constants copied from tmux_tool.py with source comment when direct import fails due to agent.py dependency chain
    - Sync _wait_ready() with time.sleep() as translation of async TmuxTool._wait_ready (asyncio.sleep removed)
    - Per-operation timeouts: 15s startup, 120s response, 15s exit (empirically derived Phase 13)

key-files:
  created:
    - python/helpers/opencode_cli.py
  modified: []

key-decisions:
  - "ANSI_RE, OPENCODE_PROMPT_PATTERN, OPENCODE_START_TIMEOUT copied directly into opencode_cli.py with source comment — import from python.tools.tmux_tool fails in standalone Python contexts because tmux_tool.py imports tool.py → agent.py → nest_asyncio (not installed outside container venv)"
  - "OpenCodeSession is a synchronous class — skill code runs sync in code_execution_tool Python runtime; asyncio is only in the Tool dispatch layer"
  - "send() returns full ANSI-stripped pane content (300 lines) including TUI chrome — response text is visible in content; differential extraction deferred to Phase 15 SKILL.md"

patterns-established:
  - "OpenCodeSession pattern: sync class wrapping subprocess tmux calls, import-path-safe constants, 3-step Ctrl+P exit"
  - "Import fallback pattern: copy module-level constants with source comment when dependency chain prevents import in standalone contexts"

requirements-completed: [CLI-05]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 14 Plan 01: OpenCode Session Wrapper Summary

**OpenCodeSession class in python/helpers/opencode_cli.py — sync tmux wrapper with .start()/.send()/.exit() validated end-to-end against OpenCode v1.2.14; multi-turn confirmed with "4" and "5" responses in 2 minutes total**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T18:18:01Z
- **Completed:** 2026-02-25T18:20:42Z
- **Tasks:** 2 (both auto)
- **Files modified:** 1

## Accomplishments

- Created python/helpers/opencode_cli.py (264 lines) with complete OpenCodeSession class
- Class loads cleanly inside Docker with `sys.path.insert(0, '/a0')` — no import errors
- End-to-end multi-turn validation passed: start() → send("What is 2+2?") returned "4" → send("Add 1") returned "5" → exit() left shell clean
- Pre-start guard correctly raises `RuntimeError("OpenCodeSession not started — call start() first")` when send() called before start()
- CLI-05 requirement satisfied: skill code orchestrates full lifecycle with zero direct tmux knowledge

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement OpenCodeSession in python/helpers/opencode_cli.py** - `12ac35e` (feat)
2. **Task 2: End-to-end validation against installed OpenCode v1.2.14 in Docker** - no code changes required; validated on first run

**Plan metadata:** *(final docs commit below)*

## Files Created/Modified

- `python/helpers/opencode_cli.py` — OpenCodeSession class: start(), send(), exit(), _wait_ready(), running property; module-level constants ANSI_RE, OPENCODE_PROMPT_PATTERN, OPENCODE_START_TIMEOUT copied from tmux_tool.py

## Decisions Made

- **Import path for tmux_tool constants**: Direct `from python.tools.tmux_tool import ...` fails in standalone Python contexts (e.g., skill code, validation scripts) because tmux_tool.py imports tool.py → agent.py → nest_asyncio which is not installed outside the full Agent Zero container venv. Resolution: copy the three constants directly into opencode_cli.py with a comment referencing the single source of truth (tmux_tool.py). The plan explicitly anticipated this and provided the fallback.

- **Synchronous class design**: OpenCodeSession is sync (time.sleep, not asyncio.sleep). TmuxTool's async is for the Agent Zero tool dispatch loop; helper modules run synchronously. This matches the pattern from claude_cli.py.

- **Full pane return from send()**: send() returns the ANSI-stripped full pane content (300 lines) including TUI chrome. The assistant response is visible in context. Differential extraction (before/after capture diff) deferred to Phase 15 SKILL.md as a known enhancement — not required for v1 scope.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Constants copied rather than imported from python.tools.tmux_tool**

- **Found during:** Task 1 (pre-implementation verification)
- **Issue:** `from python.tools.tmux_tool import OPENCODE_PROMPT_PATTERN, OPENCODE_START_TIMEOUT, ANSI_RE` raises `ModuleNotFoundError: No module named 'nest_asyncio'` in standalone Python context — the import chain is tmux_tool → tool.py → agent.py → nest_asyncio
- **Fix:** Copied the three constants directly into opencode_cli.py with a comment: "Copied from python/tools/tmux_tool.py — single source of truth is there." This matches the plan's explicit fallback instruction: "If import fails, copy the three constants directly into opencode_cli.py with a comment"
- **Files modified:** python/helpers/opencode_cli.py (constants section)
- **Verification:** Class loads in Docker with `python3 -c "from python.helpers.opencode_cli import OpenCodeSession"` — no import errors
- **Committed in:** 12ac35e (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - Blocking — import path issue, plan-anticipated fallback applied)
**Impact on plan:** Required change with explicit plan-provided resolution. Constants remain in sync; source comment prevents future confusion.

## Issues Encountered

None — validation passed on first run. The 0.5s sleep in start() (Phase 13 pitfall 3 mitigation) was sufficient to allow the TUI input widget to activate before the first send(). Both arithmetic prompts ("2+2" → "4", "Add 1" → "5") returned correct values and multi-turn context was preserved.

## User Setup Required

None — no external service configuration required. OpenCode v1.2.14 is already installed in Docker from Phase 13.

## Next Phase Readiness

- Phase 15 (OpenCode SKILL.md) can import OpenCodeSession directly: `from python.helpers.opencode_cli import OpenCodeSession`
- Multi-turn validated: two consecutive send() calls succeed with coherent responses
- Exit method leaves shell clean: shared terminal shows shell prompt after exit()
- **Phase 15 should document**: send() returns full pane content including TUI chrome; callers need to parse or accept the content as-is; response text is visible but not isolated
- **Phase 15 may add**: session_id capture from exit output for OpenCode session resumption (opencode -s ses_[ID]); differential send() extraction for cleaner response text

---
*Phase: 14-opencode-session-wrapper*
*Completed: 2026-02-25*
