---
phase: 08-claude-cli-single-turn-env-fix
verified: 2026-02-25T19:30:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 8: Claude CLI Single-Turn + Env Fix Verification Report

**Phase Goal:** Agent Zero can invoke the `claude` CLI from within its own environment and receive a clean, parseable response to a single-turn prompt
**Verified:** 2026-02-25T19:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                                              | Status     | Evidence                                                                                                                   |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------- |
| 1   | Running claude subprocess from Agent Zero Python context with CLAUDECODE set does NOT produce "Cannot be launched inside another Claude Code session" error | ✓ VERIFIED | `env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}` present on lines 48 and 107; passed to subprocess as `env=env_clean` on lines 60 and 119 |
| 2   | `claude_single_turn('test prompt')` returns a non-empty string containing only the response text — no ANSI escape sequences, no JSON wrapper       | ✓ VERIFIED | `--output-format json` used; `data['result']` extracted (line 86); `ANSI_RE.sub('', result.stdout)` safety strip on line 79 |
| 3   | Process exit is detected cleanly: returncode == 0 on success, RuntimeError raised with stderr on non-zero exit                                     | ✓ VERIFIED | `result.returncode != 0` check on lines 74 and 127; raises `RuntimeError(f"claude exited {result.returncode}: {err}")` on both paths |
| 4   | Calling `claude_single_turn()` with a bad prompt or timeout raises RuntimeError with a diagnostic message, not a silent hang or unhandled exception | ✓ VERIFIED | `subprocess.TimeoutExpired` caught → `RuntimeError` with message on lines 63-67 and 122-123; `FileNotFoundError` caught → `RuntimeError` on lines 68-72 and 124-125; `is_error` API-level error caught on lines 83-84 |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact                            | Expected                                              | Status     | Details                                                                                       |
| ----------------------------------- | ----------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------- |
| `python/helpers/claude_cli.py`      | `claude_single_turn()` and `claude_single_turn_text()` functions | ✓ VERIFIED | Exists, 131 lines (min: 40), contains `CLAUDECODE`; both functions present with correct signatures; imports cleanly |

**Level 1 (Exists):** File exists at `python/helpers/claude_cli.py` — confirmed.

**Level 2 (Substantive):** 131 lines. All required patterns verified by import + inspection:
- `CLAUDECODE` present — PASS
- `capture_output=True` present — PASS
- `json.loads` present — PASS
- `is_error` check present — PASS
- `env_clean` dict comprehension present — PASS
- `TimeoutExpired` handler present — PASS
- `FileNotFoundError` handler present — PASS
- `RuntimeError` raises present — PASS
- `ANSI_RE` safety strip present — PASS
- `data['result']` extraction present — PASS

**Level 3 (Wired):** This is a utility library module. Its "wiring" is importability from Agent Zero's Python runtime. Confirmed: `from python.helpers.claude_cli import claude_single_turn, claude_single_turn_text` imports cleanly with no errors. No downstream callers in Phase 8 scope — downstream integration is Phase 9's responsibility. The module is ready at `python/helpers/` alongside 80+ peer helpers.

### Key Link Verification

| From                                         | To               | Via                               | Status     | Details                                                                              |
| -------------------------------------------- | ---------------- | --------------------------------- | ---------- | ------------------------------------------------------------------------------------ |
| `python/helpers/claude_cli.py`               | claude binary    | `subprocess.run` with `env_clean` | ✓ WIRED    | Lines 48+60 (`claude_single_turn`) and 107+119 (`claude_single_turn_text`) both build `env_clean` with `if k != 'CLAUDECODE'` and pass as `env=env_clean` |
| `subprocess.run capture_output=True`         | `json.loads(result.stdout)` | `ANSI_RE.sub` safety strip then `json.loads` | ✓ WIRED | Line 79: `stdout_clean = ANSI_RE.sub('', result.stdout).strip()`; line 81: `data = json.loads(stdout_clean)` |

**Key link 1 — env_clean to subprocess:** Pattern `env_clean.*CLAUDECODE` confirmed present (lines 48, 107). `env=env_clean` passed to `subprocess.run()` on lines 60, 119. Both functions apply the fix independently — no shared mutable state.

**Key link 2 — JSON parsing chain:** `capture_output=True` set on lines 57-62 and 115-121. `result.stdout` is ANSI-stripped via `ANSI_RE.sub` on line 79. `json.loads(stdout_clean)` on line 81. `data['result']` returned on line 86. Chain is complete and correctly ordered.

**Global mutation check:** The `os.environ[` and `del os.environ` appearances on lines 45-46 are inside a comment (`# Remove CLAUDECODE from subprocess env only -- NEVER del os.environ['CLAUDECODE']`). No executable global mutation exists.

### Requirements Coverage

| Requirement | Source Plan | Description                                                                          | Status      | Evidence                                                                                 |
| ----------- | ----------- | ------------------------------------------------------------------------------------ | ----------- | ---------------------------------------------------------------------------------------- |
| CLAUDE-01   | 08-01-PLAN  | Agent Zero can launch `claude` CLI by unsetting `CLAUDECODE` in subprocess env       | ✓ SATISFIED | `env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}` on lines 48 + 107; passed as `env=env_clean` to all `subprocess.run()` calls |
| CLAUDE-02   | 08-01-PLAN  | Agent Zero can send a prompt to `claude` using `--print` / `-p` mode and receive complete response from stdout | ✓ SATISFIED | `cmd = ['claude', '--print', '--output-format', 'json']` + `cmd.append(prompt)` on lines 50-53; `result.stdout` captured and returned via `data['result']` |
| CLAUDE-03   | 08-01-PLAN  | Agent Zero can detect when `claude --print` invocation has finished and extract response text free of ANSI escape sequences | ✓ SATISFIED | `result.returncode` checked (lines 74, 127); `ANSI_RE.sub('', result.stdout)` applied (lines 79, 131); `subprocess.run()` blocks until process exits, `returncode` is the exit detection mechanism |

**Orphaned requirements check:** REQUIREMENTS.md maps CLAUDE-01, CLAUDE-02, CLAUDE-03 to Phase 8. All three are claimed in 08-01-PLAN.md frontmatter. No orphaned requirements.

**Out-of-scope requirements:** CLAUDE-04 (multi-turn PTY) maps to Phase 9; CLAUDE-05 (skill documentation) maps to Phase 10. Neither is expected here.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| None | — | — | — | — |

No anti-patterns found. No TODO/FIXME/PLACEHOLDER comments. No empty return values. No console.log-only stubs. No stub implementations.

### Commit Verification

Commit `ae68ab5` exists and matches:
- Message: `feat(08-01): add claude_cli.py with single-turn invocation helper`
- Change: `python/helpers/claude_cli.py | 131 ++++++++++` (single file, 131 insertions)
- Description in commit covers all key implementation decisions: env_clean CLAUDECODE fix, capture_output, JSON parsing, error handling, ANSI_RE pattern

### Human Verification Required

None. All success criteria for Phase 8 are mechanically verifiable:

- File existence and line count: verified programmatically
- Pattern presence (CLAUDECODE, json.loads, is_error, etc.): verified via import + inspection
- Import functionality: verified via Python import
- No global os.environ mutation: confirmed by line-level grep (only in comments)
- Key link chain (env_clean → subprocess → json.loads → data['result']): verified by line-number tracing

The one item that could benefit from human confirmation — live end-to-end response against the actual claude binary — was performed by the implementer during Task 2 and documented in 08-01-SUMMARY.md ("CLAUDE-02+03 PASS: response = 'PONG'"). The code structure fully supports this behavior being reproducible. No additional human verification is needed to confirm goal achievement.

### Gaps Summary

No gaps. All four observable truths are satisfied. Both required functions exist with complete, non-stub implementations. Both key links are verified. All three requirement IDs (CLAUDE-01, CLAUDE-02, CLAUDE-03) are covered. No anti-patterns found.

---

_Verified: 2026-02-25T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
