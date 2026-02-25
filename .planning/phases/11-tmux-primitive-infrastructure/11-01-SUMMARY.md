---
phase: 11-tmux-primitive-infrastructure
plan: 01
subsystem: infra
tags: [tmux, subprocess, ansi, terminal, tool]

# Dependency graph
requires: []
provides:
  - TmuxTool class in python/tools/tmux_tool.py with send/keys/read actions
  - Agent-facing prompt documentation in prompts/agent.system.tool.tmux.md
  - Sentinel-free tmux primitive layer auto-registered via glob pattern
affects:
  - 12-claude-cli-integration
  - 13-opencode-integration
  - 14-interactive-session-orchestration
  - 15-tmux-advanced-patterns

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "subprocess.run list-form (no shell=True) for all tmux calls"
    - "ANSI_RE with OSC branch first to prevent 2-char branch shadowing"
    - "Action dispatch via dict (send/keys/read) in Tool.execute()"
    - "capture-pane without -e flag to avoid raw escape sequences in output"

key-files:
  created:
    - python/tools/tmux_tool.py
    - prompts/agent.system.tool.tmux.md
  modified: []

key-decisions:
  - "ANSI_RE OSC branch must come first: [@-Z\\-_] range includes ] (0x5D), which would shadow \\][^\\x07]*\\x07 if placed after"
  - "send action passes text as single list element to prevent tmux interpreting words like 'Tab' as key names"
  - "keys action accepts both str (split on whitespace) and list for flexibility"
  - "No sentinel injection in tmux_tool: capture-pane is the sole observation mechanism"
  - "synchronous subprocess.run chosen over asyncio.create_subprocess_exec: tmux calls are <50ms"

patterns-established:
  - "ANSI_RE pattern: OSC branch (\\][^\\x07]*\\x07) must precede 2-char branch ([@-Z\\-_])"
  - "send vs keys distinction: send=text+Enter for commands; keys=key-names without Enter for interactive input"
  - "Agent tool dispatch: dict mapping action strings to bound async methods"

requirements-completed: [TERM-01, TERM-02, TERM-03, TERM-04]

# Metrics
duration: 4min
completed: 2026-02-25
---

# Phase 11 Plan 01: tmux Primitive Infrastructure Summary

**Sentinel-free TmuxTool class with send/keys/read actions against the shared tmux session, plus auto-registered agent prompt documentation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-25T14:14:27Z
- **Completed:** 2026-02-25T14:18:25Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- TmuxTool Python class implementing TERM-01 (send), TERM-02/03 (keys), TERM-04 (read) requirements
- ANSI escape sequence stripping with correct OSC-first regex ordering verified against CSI and OSC test cases
- Agent-facing prompt documentation with send/keys/read distinction and all four usage examples, auto-registered via `agent.system.tool.*.md` glob
- terminal_agent.py left completely untouched — both tools coexist

## Task Commits

Each task was committed atomically:

1. **Task 1: Create python/tools/tmux_tool.py** - `2fd0504` (feat)
2. **Task 2: Create prompts/agent.system.tool.tmux.md** - `412557e` (feat)
3. **Auto-fix: ANSI_RE branch ordering** - `5d4937f` (fix)

## Files Created/Modified

- `python/tools/tmux_tool.py` - TmuxTool class: send/keys/read action dispatch, subprocess list-form calls, ANSI stripping
- `prompts/agent.system.tool.tmux.md` - Agent tool documentation with usage examples, auto-registered via glob

## Decisions Made

- ANSI_RE regex: OSC branch `\][^\x07]*\x07` placed before `[@-Z\\-_]` because the 2-char branch's range covers `]` (0x5D is in `\\-_` range 0x5C-0x5F) and would shadow the OSC branch if ordered after
- `send` passes the text argument as a single list element (not split), then "Enter" as a separate argument — this prevents tmux from treating words like "Tab" in user text as key names
- Synchronous `subprocess.run` used (not async) since tmux IPC calls complete in <50ms — avoids unnecessary coroutine overhead

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ANSI_RE branch ordering to correctly strip OSC sequences**

- **Found during:** Phase verification (after Task 1 commit)
- **Issue:** The plan-specified regex `\x1b(?:[@-Z\\-_]|...)` matched `]` via the `\\-_` range (0x5C-0x5F includes `]` at 0x5D), causing the OSC branch `\][^\x07]*\x07` to never match. OSC title sequences like `\x1b]0;bash\x07` were only partially stripped — the `\x1b` was removed but `0;bash\x07` remained.
- **Fix:** Reordered alternatives: OSC branch first → `\x1b(?:\][^\x07]*\x07|[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])`
- **Files modified:** `python/tools/tmux_tool.py`
- **Verification:** Both OSC (`\x1b]0;bash\x07` → `''`) and CSI (`\x1b[32m` → `''`) test cases pass
- **Committed in:** `5d4937f`

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix essential for correctness — terminal output with shell prompts often includes OSC title sequences. Without the fix, these would appear as junk text in read() output. No scope creep.

## Issues Encountered

- Plan verification check `assert 'MARKER' not in src` failed on the word "MARKER" in the docstring comment — the comment was rephrased to remove the word while preserving intent. Same issue occurred with `shell=True` in the docstring.
- The plan's ANSI verification script had a Python f-string backslash syntax error (`{result!r}` in f-string) but the actual regex behavior was tested and confirmed correct using a heredoc approach.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 12 (Claude CLI integration) can use `tmux_tool` send/keys/read immediately
- Phases 13-15 have the same primitives available
- terminal_agent.py unchanged — no coordination needed between tools

## Self-Check: PASSED

- FOUND: python/tools/tmux_tool.py
- FOUND: prompts/agent.system.tool.tmux.md
- Commits verified: 2fd0504, 412557e, 5d4937f all in git log

---
*Phase: 11-tmux-primitive-infrastructure*
*Completed: 2026-02-25*
