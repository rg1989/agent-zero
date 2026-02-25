---
phase: 08-claude-cli-single-turn-env-fix
plan: "01"
subsystem: api
tags: [claude-cli, subprocess, env-fix, CLAUDECODE, json-parsing, ANSI]

# Dependency graph
requires:
  - phase: 08-claude-cli-single-turn-env-fix
    provides: empirical research on claude CLI invocation patterns, confirmed env fix, confirmed JSON output format
provides:
  - "python/helpers/claude_cli.py with claude_single_turn() and claude_single_turn_text()"
  - "Reusable Python helper for calling claude CLI from Agent Zero Python runtime"
  - "CLAUDECODE env fix via per-call dict (never globally mutated)"
affects:
  - "10-claude-cli-skill" (SKILL.md documentation will reference these functions)
  - "09-claude-cli-multi-turn" (multi-turn PTY sessions build on this single-turn foundation)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CLAUDECODE env fix: {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'} per-call only"
    - "subprocess.run with capture_output=True for clean stdout (no ANSI, no PTY)"
    - "claude --print --output-format json; extract .result field"
    - "ANSI_RE safety strip matching shell_ssh.py pattern"

key-files:
  created:
    - python/helpers/claude_cli.py
  modified: []

key-decisions:
  - "Use subprocess.run capture_output=True (not TTY/PTY) to avoid ANSI sequences entirely"
  - "Per-call env dict (never del os.environ['CLAUDECODE'] globally)"
  - "claude_single_turn() uses --output-format json for metadata; claude_single_turn_text() uses --output-format text for simplicity"
  - "ANSI_RE defensive strip present but is no-op when capture_output=True; matches battle-tested shell_ssh.py regex"
  - "RuntimeError raised on non-zero exit, FileNotFoundError, and TimeoutExpired — no silent failures"

patterns-established:
  - "Pattern: All claude subprocess calls build env_clean via dict comprehension filtering CLAUDECODE"
  - "Pattern: All claude subprocess calls use capture_output=True for clean TTY-free output"
  - "Pattern: JSON format extraction via json.loads + data['result'] + is_error check"

requirements-completed: [CLAUDE-01, CLAUDE-02, CLAUDE-03]

# Metrics
duration: 14min
completed: 2026-02-25
---

# Phase 8 Plan 01: Claude CLI Single-Turn Helper Summary

**stdlib-only Python helper for invoking claude CLI from Agent Zero: CLAUDECODE env fix, capture_output JSON parsing, ANSI stripping, RuntimeError on all failure paths**

## Performance

- **Duration:** 14 min
- **Started:** 2026-02-25T18:00:22Z
- **Completed:** 2026-02-25T18:14:22Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Created `python/helpers/claude_cli.py` with `claude_single_turn()` and `claude_single_turn_text()` functions
- CLAUDE-01 confirmed: CLAUDECODE env fix prevents "Cannot be launched inside Claude Code session" error
- CLAUDE-02+03 confirmed: `claude_single_turn('Reply with only the word PONG.')` returns `'PONG'` — clean text, no ANSI, no JSON wrapper
- All three error paths confirmed: FileNotFoundError, TimeoutExpired, non-zero returncode all raise RuntimeError with diagnostic messages

## Task Commits

Each task was committed atomically:

1. **Task 1: Create python/helpers/claude_cli.py** - `ae68ab5` (feat)
2. **Task 2: Validate end-to-end against live claude binary** - no code changes (validation only; confirmed Task 1 implementation correct)

**Plan metadata:** (final commit — see below)

## Files Created/Modified

- `python/helpers/claude_cli.py` - Claude CLI single-turn invocation helper; `claude_single_turn()` and `claude_single_turn_text()` functions with CLAUDECODE env fix

## Decisions Made

- `subprocess.run` with `capture_output=True` used instead of PTY/shell: eliminates all ANSI sequences at source, avoids the OSC sequence problem documented in research (where `clean_string()` leaves `9;4;0;\x07` payload)
- Per-call `env_clean` dict builds a fresh copy with CLAUDECODE excluded — never mutates `os.environ` globally
- `claude_single_turn()` uses `--output-format json` to get structured response with `.result` field and metadata
- `claude_single_turn_text()` uses `--output-format text` as a simpler alternative when metadata is not needed
- ANSI_RE regex matches the exact pattern from `shell_ssh.py` — same regex, consistent codebase

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion used wrong case for error string check**
- **Found during:** Task 2 (live validation)
- **Issue:** Plan's test code used `'Cannot' in r.stderr` (capital C) but actual error message is "cannot be launched" (lowercase); assertion failed despite correct behavior
- **Fix:** Changed assertion to use `'cannot' in r.stderr.lower()` — matched the actual error message from claude 2.1.55
- **Files modified:** Test script only (not `claude_cli.py`); no change to deliverable
- **Verification:** Test 1a passed with corrected assertion
- **Committed in:** Not separately committed — test script was temporary, `claude_cli.py` unchanged

---

**Total deviations:** 1 auto-fixed (Rule 1 - test assertion case mismatch)
**Impact on plan:** Trivial — only affected temporary validation script, not the deliverable `claude_cli.py`. Zero scope creep.

## Issues Encountered

- Live API calls via `subprocess.run` take 30-45 seconds from within the Claude Code Bash tool context (network latency to Anthropic API). Tests were written to file and run via `nohup` background process to avoid the Bash tool's implicit shell hang behavior with long-running commands.
- The `timeout=15` in the initial inline test was too short for the API call to complete; extended to 120s (matching the `CLAUDE_DEFAULT_TIMEOUT` constant).

## User Setup Required

None - no external service configuration required. `claude` binary already installed at `/Users/rgv250cc/.local/bin/claude` (version 2.1.55). No new Python dependencies.

## Next Phase Readiness

- `python/helpers/claude_cli.py` is ready for import in Agent Zero's Python runtime (`code_execution_tool` with `runtime="python"`)
- Phase 9 (multi-turn PTY sessions) can reference `claude_single_turn()` as the single-turn primitive
- Phase 10 (`usr/skills/claude-cli/SKILL.md`) can document both functions with verified usage examples
- Note: `claude` binary is only available on the host, not in the Docker container — scope of this helper is host-side Python runtime only

---
*Phase: 08-claude-cli-single-turn-env-fix*
*Completed: 2026-02-25*
