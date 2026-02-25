---
phase: 12-readiness-detection
plan: 01
subsystem: terminal
tags: [tmux, asyncio, prompt-detection, ANSI, readiness-polling, interactive-cli]

# Dependency graph
requires:
  - phase: 11-tmux-primitive-infrastructure
    provides: TmuxTool class with send/keys/read actions; ANSI_RE module-level regex; dispatch pattern
provides:
  - _wait_ready() method on TmuxTool — polls capture-pane every 0.5s, strips ANSI, detects shell prompt on last non-blank line or content stability, returns after timeout
  - "wait_ready" action registered in TmuxTool dispatch dict
  - agent prompt documentation with timeout/prompt_pattern args and 4 behavioral warnings
affects: [phase 13 opencode-orchestration, phase 14 claude-cli-orchestration, phase 15 multi-turn-sessions]

# Tech tracking
tech-stack:
  added: [asyncio (stdlib), time (stdlib)]
  patterns: [dual-strategy readiness detection — prompt-first, stability-fallback; initial 0.3s delay to avoid stale-prompt race]

key-files:
  created: []
  modified:
    - python/tools/tmux_tool.py
    - prompts/agent.system.tool.tmux.md

key-decisions:
  - "Initial 0.3s sleep before first capture-pane: prevents stale-prompt false positive where shell prompt from before the command still appears"
  - "Stability check skipped on first iteration (prev_content=None): avoids empty-pane false positive at startup"
  - "Lines captured capped at -S -50 (not -100) for wait_ready: only last prompt line needed; smaller capture is faster in tight poll loop"
  - "Live test deferred to Docker deployment: tmux not installed locally; Steps 1-3 (syntax, ANSI strip, prompt pattern) all passed locally"

patterns-established:
  - "wait_ready pattern: always call after send, before next send; use timeout=120 for AI CLI tools"
  - "Prompt matching: strip ANSI first, then match ONLY last non-blank line — never against full scrollback"
  - "Default prompt_pattern r'[$#>%]\\s*$': matches bash/zsh/sh/node prompts; does NOT match Continue? [y/N]"

requirements-completed: [TERM-05]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 12 Plan 01: Readiness Detection Summary

**`wait_ready` action added to TmuxTool: polls capture-pane every 0.5s, strips ANSI via ANSI_RE, detects shell prompt on last non-blank line (primary) or content stability (secondary), with configurable timeout and never-hang guarantee**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T16:21:01Z
- **Completed:** 2026-02-25T16:23:16Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Added `_wait_ready()` method to TmuxTool with dual-strategy detection: prompt pattern (primary) and content stability (secondary)
- Registered `wait_ready` in dispatch dict; updated valid-action error message
- Added `asyncio` and `time` imports; initial 0.3s delay guards against stale-prompt false positive at call boundary
- Updated agent prompt doc: action list, timeout/prompt_pattern args, 4 !!! behavioral warnings, 3 usage examples
- Validated: syntax clean, ANSI stripping works on colored prompts and OSC sequences, default pattern matches shell prompts and rejects `Continue? [y/N]`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _wait_ready() method and dispatch entry to TmuxTool** - `3bbeced` (feat)
2. **Task 2: Update agent prompt doc with wait_ready action and usage examples** - `c867417` (docs)
3. **Task 3: Validate implementation with a live test** - no commit (validation-only task)

**Plan metadata:** (see final commit below)

## Files Created/Modified

- `python/tools/tmux_tool.py` - Added `asyncio`/`time` imports; expanded dispatch dict; added `_wait_ready()` method (87 new lines); updated class docstring and error message
- `prompts/agent.system.tool.tmux.md` - Added `wait_ready` to action list; documented `timeout` and `prompt_pattern` args; added 4 `!!!` warnings; added 3 usage examples

## Decisions Made

- **Initial 0.3s sleep before first capture:** Prevents stale-prompt false positive (shell prompt from before the command still visible immediately after `send-keys`). Per RESEARCH.md Pitfall 6 and open question resolved in favour of 0.3s.
- **Stability skipped on first iteration:** `prev_content = None` initialization means comparison is skipped on iteration 1, preventing false "stable" signal on empty pane at startup (RESEARCH.md Pitfall 3).
- **-S -50 for wait_ready capture:** Only 50 lines needed for prompt detection vs 100 for full read; faster in tight poll loop. `_read()` remains at -S -100.
- **Live test deferred to Docker:** tmux not installed on macOS host. Steps 1-3 (syntax/AST, ANSI strip, prompt pattern matching) all verified locally. End-to-end live test available once agent runs in Docker.

## Deviations from Plan

None - plan executed exactly as written. Live test step 4 was gracefully skipped (as documented in the plan: "note this in the summary") — not a deviation.

## Issues Encountered

- Module full-import verification (`import python.tools.tmux_tool`) fails locally due to missing `nest_asyncio` (not installed outside Docker). Switched to AST-based verification for local validation — equivalent for syntax and structure checks. No fix needed; this is expected in the local dev environment.

## User Setup Required

None - no external service configuration required. Changes ship automatically via Docker bind mounts (`./python:/a0/python`, `./prompts:/a0/prompts`).

## Next Phase Readiness

- `wait_ready` is ready for use in Phase 13 (OpenCode orchestration)
- Phase 13 callers MUST pass `timeout=120` (or higher) when waiting on OpenCode responses — documented in agent prompt and RESEARCH.md Pitfall 4
- Phase 13 may need a custom `prompt_pattern` for OpenCode's prompt — `prompt_pattern` argument is exposed for this purpose
- Blockers from STATE.md remain: OpenCode installed version unknown; hang regression (v0.15+) still needs assessment

## Self-Check: PASSED

- python/tools/tmux_tool.py: FOUND
- prompts/agent.system.tool.tmux.md: FOUND
- 12-01-SUMMARY.md: FOUND
- Commit 3bbeced (Task 1): FOUND
- Commit c867417 (Task 2): FOUND

---
*Phase: 12-readiness-detection*
*Completed: 2026-02-25*
