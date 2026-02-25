---
phase: 14-opencode-session-wrapper
verified: 2026-02-25T20:45:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 14: OpenCode Session Wrapper — Verification Report

**Phase Goal:** Agent Zero can use a pre-built OpenCodeSession class with a clean .start() / .send(prompt) / .exit() interface — hiding tmux plumbing from skill code and mirroring the ClaudeSession pattern from v1.1
**Verified:** 2026-02-25T20:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from must_haves in 14-01-PLAN.md)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Skill code can call session.start(), session.send(prompt), session.exit() with no direct tmux subcommand calls | VERIFIED | `class OpenCodeSession` at line 56 with `start()` (line 94), `send()` (line 120), `exit()` (line 160) fully implemented. All tmux subprocess calls are internal to the class — no tmux calls would appear in skill code. |
| 2 | OpenCodeSession encodes the empirically verified Ctrl+P exit sequence — not /exit which triggers agent picker | VERIFIED | `exit()` sends `"C-p"` at line 182 (Step 1), then `"exit", "Enter"` at lines 188–190 (Step 2). Docstring explicitly warns against `/exit` (lines 171–173). No `/exit` string present in the file. |
| 3 | OpenCodeSession uses OPENCODE_PROMPT_PATTERN imported from tmux_tool, not a re-declared copy | VERIFIED (with note) | The plan itself anticipated import failure and provided a copy-with-source-comment fallback. The constant IS a copy of tmux_tool's value — verified byte-for-byte identical. Source attribution comment at lines 29–31 and 45, 49. Both files agree: `r'^(?:\s*/a0\s+\d+\.\d+\.\d+\s*$|(?!.*esc interrupt).*ctrl\+t variants\s+tab agents)'`. The copy approach satisfies the spirit of the requirement (single logical source). |
| 4 | send() raises RuntimeError (not hang) when response timeout is exceeded; sends C-c to interrupt | VERIFIED | `_wait_ready()` (line 197): on timeout sends `C-c` at lines 249–252, then raises `RuntimeError` at lines 254–258 with timeout value and Ollama hint. |
| 5 | send() raises RuntimeError if called before start() | VERIFIED | Guard at lines 142–143: `if not self._running: raise RuntimeError("OpenCodeSession not started — call start() first")`. Confirmed by SUMMARY: pre-start guard test passed. |
| 6 | OpenCodeSession.start() waits for OPENCODE_PROMPT_PATTERN before returning — startup not declared done until ready state confirmed | VERIFIED | `start()` calls `self._wait_ready(timeout=OPENCODE_START_TIMEOUT, prompt_pattern=OPENCODE_PROMPT_PATTERN)` at line 117 before setting `self._running = True` at line 118. `_running` is only set True after `_wait_ready` returns without raising. |

**Score:** 6/6 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `python/helpers/opencode_cli.py` | OpenCodeSession class with start/send/exit interface | VERIFIED | File exists at 264 lines (exceeds min_lines: 80). Exports `OpenCodeSession` class. Contains `OPENCODE_PROMPT_PATTERN` at line 46. All four methods present: `start()`, `send()`, `exit()`, `_wait_ready()`. `running` property at lines 261–263. |

**Artifact level checks:**

- Level 1 (Exists): File present at `python/helpers/opencode_cli.py`, 264 lines.
- Level 2 (Substantive): No TODO/FIXME/placeholder comments. No stub patterns (`return null`, empty handlers). All methods have full implementations with substantive logic. Module docstring documents phase basis and usage.
- Level 3 (Wired): `OpenCodeSession` methods call `subprocess.run(["tmux", ...])` directly — this IS the wiring. The class is the wiring layer between skill code (caller) and tmux (target). No `shell=True` anywhere in the file.

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `python/helpers/opencode_cli.py` | `python/tools/tmux_tool.py` | Constants copied with source comment | VERIFIED (copy variant) | Direct import fails at runtime due to `tmux_tool.py -> tool.py -> agent.py -> nest_asyncio` dependency chain in standalone Python contexts. Plan explicitly anticipated this (Task 1 fallback instruction). All three constants (ANSI_RE, OPENCODE_PROMPT_PATTERN, OPENCODE_START_TIMEOUT) are byte-for-byte identical between the two files — verified by direct comparison. Source attribution comment at lines 29–31 of opencode_cli.py. |
| `OpenCodeSession.exit()` | tmux send-keys C-p sequence | 3-step Ctrl+P palette exit | VERIFIED | `exit()` sends `"C-p"` (line 182) — Step 1. `time.sleep(0.2)` (line 187) — Step 2 pause. Sends `"exit", "Enter"` (lines 188–190) — Step 3. Calls `_wait_ready(timeout=15, prompt_pattern=r'[$#>%]\s*$')` (line 194) to confirm shell return. |
| `OpenCodeSession.send()` | `_wait_ready` | prompt pattern polling loop using OPENCODE_PROMPT_PATTERN | VERIFIED | `send()` calls `self._wait_ready(timeout=self._response_timeout, prompt_pattern=OPENCODE_PROMPT_PATTERN)` at line 150 (after sending prompt at lines 145–149). `start()` also calls `_wait_ready` with same pattern at line 117. |

**Key link note on truth #3 (import vs copy):** The plan's `key_links[0]` specifies `pattern: "from python\\.tools\\.tmux_tool import"`. This pattern does NOT match in the file (confirmed: grep returns 0 matches). However, the plan itself provided an explicit fallback ("If import fails, copy the three constants directly into opencode_cli.py with a comment") which was correctly applied. The constants are in sync; the deviation is plan-anticipated and documented. This is assessed as VERIFIED because the functional requirement (single logical source, constants in sync) is met.

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CLI-05 | 14-01-PLAN.md | Agent Zero can use a pre-built `OpenCodeSession` wrapper with `.start()` / `.send(prompt)` / `.exit()` interface, mirroring `ClaudeSession` | SATISFIED | `OpenCodeSession` class in `python/helpers/opencode_cli.py` provides exactly this interface. SUMMARY documents multi-turn end-to-end validation: `start()` → `send("What is 2+2?")` returned "4" → `send("Add 1")` returned "5" → `exit()`. Skill code requires only `from python.helpers.opencode_cli import OpenCodeSession` — no tmux knowledge. |

**Orphaned requirement check:** REQUIREMENTS.md maps only CLI-05 to Phase 14 (Traceability table). 14-01-PLAN.md claims only CLI-05. No orphaned requirements.

**Requirements marked complete in REQUIREMENTS.md:** CLI-05 shows `[x]` (checked) in REQUIREMENTS.md line 25.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Scanned for: TODO/FIXME/XXX/HACK/PLACEHOLDER (case-insensitive), `return null`, `return {}`, `return []`, `=> {}`, `pass` (Python), `shell=True`. All checks returned no matches.

---

## Human Verification Required

### 1. End-to-end live session validation

**Test:** In Docker, run `docker exec agent-zero python3 -c "import sys; sys.path.insert(0, '/a0'); from python.helpers.opencode_cli import OpenCodeSession; s = OpenCodeSession(response_timeout=60); s.start(); r = s.send('What is 2+2? Reply with just the number.'); assert '4' in r; s.exit(); print('PASS')"` with the shared tmux session running and Ollama accessible.
**Expected:** `PASS` printed; no exceptions; `s.running` True after start(), False after exit().
**Why human:** Requires live Docker container with tmux session running and Ollama at host:11434. Cannot verify live subprocess behavior statically.

Note: SUMMARY.md documents this test was run successfully during Task 2 execution, including multi-turn ("4" and "5" responses). Static verification finds all implementation structures correct. Human verification is confirmatory, not a gap indicator.

---

## Decisions Made (Traceability)

**Import fallback (key deviation):** The plan required `from python.tools.tmux_tool import OPENCODE_PROMPT_PATTERN, OPENCODE_START_TIMEOUT, ANSI_RE` but also explicitly provided a fallback: "If import fails, copy the three constants directly into opencode_cli.py with a comment: `# Copied from python/tools/tmux_tool.py — single source of truth is there`." The import fails at runtime because `tmux_tool.py` imports `tool.py` → `agent.py` → `nest_asyncio` which is not installed outside the Agent Zero container venv. The fallback was correctly applied. All three constant values are byte-for-byte identical between the two files — no value drift. Source comment at lines 29–31 prevents future confusion.

**Synchronous class design:** `OpenCodeSession` uses `time.sleep()` not `asyncio.sleep()`. This matches the ClaudeSession pattern (synchronous) and is correct for skill code runtime. `asyncio` lives only in the Tool dispatch layer.

**Full pane return from send():** `send()` returns ANSI-stripped full pane content (300 lines) including TUI chrome. Response is visible in content. Differential extraction deferred to Phase 15 per plan scope. This is documented in the class docstring (lines 79–82).

---

## Commit Verification

| Commit | Hash | Status | Content |
|--------|------|--------|---------|
| Task 1: Implement OpenCodeSession | `12ac35e` | VERIFIED | `git show 12ac35e` confirms commit exists with correct subject and `python/helpers/opencode_cli.py` as the only changed file (+264 lines) |

---

## Overall Assessment

Phase 14 goal is **achieved**. The `OpenCodeSession` class in `python/helpers/opencode_cli.py` provides:

1. A clean `.start()` / `.send(prompt)` / `.exit()` interface — skill code has zero tmux knowledge
2. The empirically verified Ctrl+P exit sequence from Phase 13 — encoded in `exit()`, with explicit warning against `/exit`
3. Timeout-with-RuntimeError behavior in `_wait_ready()` — no hangs
4. Pre-start guard in `send()` — clear error if called before `start()`
5. Startup completion gated on OPENCODE_PROMPT_PATTERN match — `_running = True` set only after `_wait_ready` returns
6. Constants that are byte-for-byte copies of `tmux_tool.py` values with source attribution — functionally equivalent to import

The one structural deviation (constants copied rather than imported via `from python.tools.tmux_tool import`) was explicitly anticipated in the plan's fallback instructions and correctly applied. Values are in sync. CLI-05 is satisfied.

---

_Verified: 2026-02-25T20:45:00Z_
_Verifier: Claude (gsd-verifier)_
