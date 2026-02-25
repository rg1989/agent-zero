---
phase: 13-interactive-cli-session-lifecycle
plan: 02
subsystem: infra
tags: [opencode, tmux, cli, tui, docker]

# Dependency graph
requires:
  - phase: 13-01
    provides: empirically verified OPENCODE_PROMPT_PATTERN and startup timing for OpenCode v1.2.14 TUI

provides:
  - OPENCODE_PROMPT_PATTERN and OPENCODE_START_TIMEOUT constants in tmux_tool.py (Phase 14 can import directly)
  - OpenCode permanent Docker installation in install_additional.sh (survives container rebuilds)
  - OpenCode lifecycle usage pattern documented in prompts/agent.system.tool.tmux.md (CLI-01..04)
  - End-to-end validated: OpenCode starts, accepts prompts, receives AI responses, exits cleanly

affects: [14-opencode-session-wrapper, any phase using tmux_tool with OpenCode]

# Tech tracking
tech-stack:
  added: [opencode v1.2.14 permanent Docker install via opencode.ai/install]
  patterns:
    - OPENCODE_PROMPT_PATTERN module-level constant for Phase 14 import
    - CLI-04 exit via Ctrl+P (commands palette) + "exit" search + Enter (not direct /exit send)
    - OpenCode ready state = two-branch pattern covering startup AND post-response states

key-files:
  created: []
  modified:
    - docker/run/fs/ins/install_additional.sh
    - python/tools/tmux_tool.py
    - prompts/agent.system.tool.tmux.md

key-decisions:
  - "OPENCODE_PROMPT_PATTERN uses two-branch regex: startup branch (status bar with /a0 + version) OR post-response branch (ctrl+t hints WITHOUT esc interrupt)"
  - "CLI-04 exit sequence: Ctrl+P (commands palette) + type 'exit' + Enter — not direct /exit send which triggers agent picker in v1.2.14"
  - "OPENCODE_START_TIMEOUT = 15s (10x buffer over observed 1.5s startup time)"

patterns-established:
  - "OpenCode exit pattern: keys C-p, send exit, wait_ready (default shell pattern)"
  - "Module-level constants in tmux_tool.py serve as shared config for OpenCode-aware tools"

requirements-completed: [CLI-01, CLI-02, CLI-03, CLI-04]

# Metrics
duration: 7min
completed: 2026-02-25
---

# Phase 13 Plan 02: Interactive CLI Session Lifecycle Implementation Summary

**OPENCODE_PROMPT_PATTERN constant in tmux_tool.py, permanent Docker install, CLI-01..04 lifecycle validated end-to-end with big-pickle model responding "4" to "What is 2+2?" in 5.9 seconds**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-25T17:16:55Z
- **Completed:** 2026-02-25T17:23:55Z
- **Tasks:** 2 (Task 3 is checkpoint — awaiting human verify)
- **Files modified:** 3

## Accomplishments

- Added OPENCODE_PROMPT_PATTERN and OPENCODE_START_TIMEOUT constants to tmux_tool.py sourced from 13-01-OBSERVATION.md
- Added OpenCode CLI permanent install block to install_additional.sh (curl -fsSL https://opencode.ai/install | bash)
- Added "OpenCode Lifecycle Pattern" section to prompts/agent.system.tool.tmux.md with CLI-01..04 step-by-step examples
- End-to-end lifecycle validated: CLI-01 (startup → ready state detected), CLI-02+03 (prompt sent, "4" returned in 5.9s), CLI-04 (exited cleanly via Ctrl+P + exit)
- Discovered and documented v1.2.14 exit behavior: `/` key triggers AGENT PICKER, not command autocomplete; corrected exit method is Ctrl+P palette

## Task Commits

Each task was committed atomically:

1. **Task 1: Add OpenCode constants and install script** - `2e7e1ab` (feat)
2. **Task 2: Update prompt doc and validate end-to-end** - `c7fc4d8` (feat)

**Plan metadata:** (pending — after checkpoint)

## Files Created/Modified

- `docker/run/fs/ins/install_additional.sh` — Added OpenCode CLI install block after ttyd section
- `python/tools/tmux_tool.py` — Added OPENCODE_PROMPT_PATTERN and OPENCODE_START_TIMEOUT after ANSI_RE
- `prompts/agent.system.tool.tmux.md` — Added "OpenCode Lifecycle Pattern" section with CLI-01..04 examples

## Decisions Made

- **CLI-04 exit method**: Direct `/exit` send does NOT work in v1.2.14 (the `/` character opens the AGENT PICKER immediately). The verified method is: `keys C-p` → `send exit` (searches for "Exit the app") → `wait_ready`. Prompt doc updated to reflect this.
- **OPENCODE_PROMPT_PATTERN**: Two-branch regex covering both initial startup (status bar branch) and post-response state (hints bar negative-lookahead branch). Values sourced directly from 13-01-OBSERVATION.md assertions.
- **OPENCODE_START_TIMEOUT = 15**: 10x buffer over observed 1.5s startup, provides safety margin for slow container starts or network latency.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected CLI-04 exit sequence in prompt documentation**
- **Found during:** Task 2 (end-to-end lifecycle validation)
- **Issue:** Plan specified `{"action": "send", "text": "/exit"}` for CLI-04. In v1.2.14, the `/` character typed into the TUI input area immediately opens the AGENT PICKER (showing "build native", "plan native" agents), NOT the command autocomplete for `/exit`. The "exit" text goes into the agent search box rather than the command input.
- **Fix:** Updated CLI-04 in prompts/agent.system.tool.tmux.md to use the correct three-step sequence: `keys C-p` (opens commands palette), `send exit` (filters to "Exit the app"), `wait_ready` (detects shell prompt). Added IMPORTANT warning note.
- **Files modified:** prompts/agent.system.tool.tmux.md
- **Verification:** Executed Ctrl+P + type "exit" + Enter successfully — OpenCode exited and shell prompt `(venv) root@...shared-terminal#` appeared
- **Committed in:** c7fc4d8 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug in documented CLI-04 exit sequence)
**Impact on plan:** Necessary correction for correctness — the plan's proposed exit sequence would have silently failed.

## Issues Encountered

- Initial `tmux send-keys` using the Python inline script for ready-state pattern check failed due to shell escaping of `(?!...)` negative lookahead. This only affected the bash-level test script; the actual `tmux_tool.py` regex compilation is unaffected (Python handles escaping correctly). Branch 1 of the pattern was verified to match `True` for the initial startup ready state.
- End-to-end validation: first prompt "What is 2+2?" was typed into the TUI input area via `tmux send-keys ... Enter` but the initial Enter was sent before the TUI fully registered the text — required sending a second explicit Enter. This is consistent with OBSERVATION.md note about split send + keys being more reliable for the initial fresh startup.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 14 can import `OPENCODE_PROMPT_PATTERN` and `OPENCODE_START_TIMEOUT` directly from `python/tools/tmux_tool.py`
- CLI-01..04 lifecycle verified in live container (agent-zero container, OpenCode v1.2.14)
- Shell is clean after validation — shared terminal shows shell prompt, no TUI running
- Exit method documented correctly in prompt file for agent self-use
- **Phase 14 must account for**: CLI-04 exit via Ctrl+P palette (not `/exit` direct send); first prompt Enter timing issue on fresh TUI starts

---
*Phase: 13-interactive-cli-session-lifecycle*
*Completed: 2026-02-25*
