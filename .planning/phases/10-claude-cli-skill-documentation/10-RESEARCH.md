# Phase 10: Claude CLI Skill Documentation - Research

**Researched:** 2026-02-25
**Domain:** Skill document authoring — `usr/skills/claude-cli/SKILL.md`
**Confidence:** HIGH (all patterns were empirically validated in Phases 8 and 9; this phase documents verified facts, not new code)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLAUDE-05 | A dedicated `claude-cli` skill (`usr/skills/claude-cli/SKILL.md`) documents the validated invocation patterns: single-turn (`--print`), multi-turn (`--resume UUID`), env fix, ANSI stripping, and completion detection | All patterns are empirically verified in `python/helpers/claude_cli.py` (Phases 8–9). Research below identifies every fact that must appear in the skill document, the exact code examples to use, and security notes the requirement calls out. |
</phase_requirements>

---

## Summary

Phase 10 is a pure documentation phase. No code is written. One file is created: `usr/skills/claude-cli/SKILL.md`. The skill document captures every validated claude CLI invocation pattern so any Agent Zero session can invoke claude correctly without re-discovering these patterns.

The content source is entirely the empirical validation record from Phases 8 and 9: the actual `python/helpers/claude_cli.py` implementation (323 lines, four public exports), and the verified test outputs documented in the SUMMARY and VERIFICATION files. The skill document must cover: the CLAUDECODE env fix, single-turn pattern, multi-turn `--resume UUID` pattern, ANSI stripping rationale, completion detection via `returncode`, dead-session detection and recovery, the `ClaudeSession` class, security notes, and scope (host-only, not Docker).

The reference skill format is `usr/skills/shared-browser/SKILL.md` — a structured markdown document with: metadata header, overview/rules section, stack table, runnable code blocks, decision guide, workflow section, anti-patterns, and troubleshooting table. The claude-cli SKILL.md should follow the same pattern. Length should be proportional to complexity — the shared-browser skill is 502 lines covering a large API surface; the claude-cli skill will be shorter (~150–200 lines) since the public API is four functions plus one class.

**Primary recommendation:** Create `usr/skills/claude-cli/SKILL.md` by distilling `python/helpers/claude_cli.py` and the Phase 8/9 research/summary/verification docs into a concise, runnable skill document following the `shared-browser/SKILL.md` structural template.

---

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `python/helpers/claude_cli.py` | Phase 9 (38f1489) | The implementation being documented | All four exports are empirically validated; skill is a usage guide for this module |
| `usr/skills/shared-browser/SKILL.md` | v4.3 | Structural template | Established skill format for this project; planners and agents already know this format |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `claude` CLI | 2.1.56 | The binary being invoked | Must document version and PATH location |
| `subprocess` (stdlib) | Python 3.x | Runtime context for all examples | All code examples run in Agent Zero Python runtime via `code_execution_tool` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| One SKILL.md covering all patterns | Separate SKILL.md per pattern (single-turn, multi-turn) | One file is simpler; all patterns share the same env fix and ANSI stripping setup |
| Referencing claude_cli.py in prose | Embedding full function code in SKILL | Skill consumers (agents) need runnable copy-paste blocks, not import chains — embed key examples directly |

---

## Architecture Patterns

### Skill File Location

```
usr/skills/claude-cli/
└── SKILL.md          # The only file needed for Phase 10
```

No `rules/` subdirectory is needed — the skill is self-contained. Phase 10 creates one file only.

### Skill Document Structure (based on shared-browser/SKILL.md template)

```
# Claude CLI Skill
## Metadata
## Overview + DEFAULT RULE (when to load this skill)
## Stack
## Prerequisites + CRITICAL: env fix
---
## Pattern 1: Single-Turn (stateless)
## Pattern 2: Multi-Turn (ClaudeSession)
## Pattern 3: Multi-Turn (claude_turn + manual session_id)
## Pattern 4: Dead Session Recovery
---
## Decision Guide: which function to call
## Completion Detection
## ANSI Stripping
## Session Coordination (--session-id / --resume UUID)
## Security Notes
## Anti-Patterns (NEVER DO)
## Common Pitfalls
## Troubleshooting table
```

### Content to Include Per Section

**Metadata:** name=claude-cli, version=1.0, description, tags=[claude, cli, subprocess, multi-turn, env-fix].

**Overview:** State that `python/helpers/claude_cli.py` is the implementation module; agents import from it or copy the standalone patterns. Explain scope: host-only (claude binary not in Docker container).

**DEFAULT RULE:** When should an agent load this skill? "When any task requires calling claude CLI as a subprocess from Agent Zero's Python runtime — single-turn AI queries, multi-turn AI conversations, or delegating subtasks to claude."

**Stack table:**

| Component | Detail |
|---|---|
| claude CLI | 2.1.56, `/Users/rgv250cc/.local/bin/claude` (on PATH as `claude`) |
| Python runtime | `code_execution_tool` with `runtime="python"` |
| stdlib | `subprocess`, `os`, `json`, `re` — no external dependencies |
| Helper module | `python/helpers/claude_cli.py` (importable from Agent Zero Python runtime) |

**Prerequisites + CRITICAL env fix:** The most important fact in the document. Agents must know about CLAUDECODE=1 before anything else.

```
CRITICAL: Claude Code sets CLAUDECODE=1 in its environment. The claude binary
checks this variable and refuses to launch with:
  "claude: error: Claude Code cannot be launched inside another Claude Code session."

Fix: Remove CLAUDECODE from the subprocess env — per-call ONLY, never globally:
  env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}
  subprocess.run(cmd, env=env_clean, ...)

WARNING: NEVER del os.environ['CLAUDECODE'] — that mutates the whole process.
```

**Pattern 1: Single-Turn.** The `claude_single_turn()` function. Runnable copy-paste block. Returns str.

**Pattern 2: Multi-Turn via ClaudeSession.** The `ClaudeSession` class. Runnable copy-paste block. Emphasize: session_id tracked automatically, no UUID management needed.

**Pattern 3: Multi-Turn via claude_turn() (manual).** For when caller needs the session_id explicitly (e.g., to store it, pass it to another agent, or use `--session-id` coordination). Returns (str, str).

**Pattern 4: Dead Session Recovery.** `claude_turn_with_recovery()`. Returns (str, str, bool). Include the exact dead-session error: `returncode=1, stderr='No conversation found with session ID: UUID'`.

**Decision Guide table:**

| Need | Use |
|---|---|
| One-shot AI query, no memory needed | `claude_single_turn(prompt)` |
| Multi-turn conversation, session managed automatically | `ClaudeSession().turn(prompt)` |
| Multi-turn, need session_id to coordinate agents | `claude_turn(prompt, session_id=sid)` |
| Resume a known session from another context | `claude_turn(prompt, session_id='UUID-from-prior-run')` |
| Robust multi-turn with automatic recovery | `claude_turn_with_recovery(prompt, session_id=sid)` |
| Plain text output, no metadata | `claude_single_turn_text(prompt)` |

**Completion Detection:** Document that `subprocess.run()` blocks until process exits. `returncode == 0` is success. `returncode != 0` is failure. No idle-timeout, no prompt-pattern detection, no PTY needed.

**ANSI Stripping:** When `capture_output=True` (which all functions use), claude emits zero ANSI. The `ANSI_RE` strip in every function is a defensive safety net only. Document the OSC pitfall: if output were from a TTY, `clean_string()` would leave `9;4;0;\x07` payload — but this path is not exercised by the helper functions.

**Session Coordination (--session-id / --resume UUID):** Document the `--session-id UUID` flag for pre-allocating a session UUID before the first turn (for multi-agent coordination scenarios). Document `--resume UUID` as the standard mechanism for continuing a conversation. Document that session files are stored at `~/.claude/projects/<cwd-encoded>/<session_id>.jsonl` — cwd must be consistent across turns of the same session.

**Security Notes (required by CLAUDE-05):**

1. **API key handling:** The `claude` binary reads the API key from environment variables (typically `ANTHROPIC_API_KEY`) or from `~/.claude/` config. Never hardcode API keys. The env_clean dict comprehension passes all environment variables EXCEPT CLAUDECODE — this includes `ANTHROPIC_API_KEY` if set, which is correct behavior.
2. **Subprocess scope of env var fix:** `env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}` creates a NEW dict for the subprocess only. The parent process `os.environ` is NOT modified. All other subprocesses launched by Agent Zero continue to inherit the unmodified environment. This is the only safe approach.
3. **NEVER globally unset:** `del os.environ['CLAUDECODE']`, `os.unsetenv('CLAUDECODE')`, and shell `unset CLAUDECODE` all affect the parent process globally. This would break the CLAUDECODE=1 guard for any nested Claude Code session detection elsewhere in the system.

**Anti-Patterns:**

- Using interactive claude (no `--print`) for programmatic use: full TUI rendering, no clean response boundary, idle-timeout unreliable during thinking pauses
- `--continue` instead of `--resume UUID` when multiple sessions may be active (cwd race condition)
- `--no-session-persistence` in multi-turn context (session files required for `--resume`)
- Parsing terminal runtime output as JSON without the extraction regex (OSC sequences survive `clean_string()`)
- Global env mutation: `del os.environ['CLAUDECODE']` or `os.unsetenv()`

**Pitfalls (concise, since full detail is in 08-RESEARCH.md):**
1. CLAUDECODE not removed → immediate error with specific message
2. PTY output + JSON parsing → `json.loads` fails on OSC payload residue
3. Timeout too short → `TimeoutExpired` on long responses
4. cwd change between turns → dead session (file at different path)
5. `--no-session-persistence` with `--resume` → dead session immediately

**Troubleshooting table:**

| Problem | Fix |
|---|---|
| `claude: error: Cannot be launched inside another Claude Code session` | Add `env_clean` dict, pass as `env=env_clean` to subprocess.run |
| `json.loads JSONDecodeError: Extra data` | Not using capture_output=True — switch to subprocess.run(capture_output=True) |
| `RuntimeError: No conversation found with session ID:` | Session is dead/expired — use claude_turn_with_recovery() or restart with session_id=None |
| `FileNotFoundError` for claude | claude binary not on PATH — verify `shutil.which('claude')` or check `~/.local/bin` on PATH |
| `TimeoutExpired` | Increase timeout (default 120s) or check API connectivity |
| Session memory lost between turns | session_id not passed to next turn — use ClaudeSession to manage automatically |
| `--resume` finds wrong session | cwd changed between turns — ensure consistent cwd= in all subprocess.run calls |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-turn conversation memory | Custom history dict injected as context string | `--resume UUID` via `claude_turn()` | Native session maintains full message history including tool calls; injecting text loses structured message format, inflates tokens |
| Completion detection | Idle-timeout polling loop on PTY output | `subprocess.run()` process exit + `returncode` | Process exit is unambiguous; idle-timeout has false positives during AI thinking pauses |
| Session tracking | Dict mapping prompt→response | `ClaudeSession` class | Already implemented and live-tested — zero extra code needed |
| Dead session recovery | Retry loop, exponential backoff | `claude_turn_with_recovery()` | Dead sessions fail immediately (returncode 1, ~1s) — one retry with session_id=None is sufficient |

**Key insight:** Every pattern needed for CLAUDE-05 is already implemented in `python/helpers/claude_cli.py`. The SKILL.md documents these patterns for agent consumption — copy-paste code blocks, decision guide, anti-patterns. No new code is needed.

---

## Common Pitfalls

### Pitfall 1: Creating a New Skill Directory Structure
**What goes wrong:** Creating `usr/skills/claude-cli/rules/*.md` files when the content fits in one SKILL.md.
**Why it happens:** Over-engineering based on skills with complex rule sets (e.g., gsd-planner with 4 rule files).
**How to avoid:** Phase 10 success criteria calls for exactly one file: `usr/skills/claude-cli/SKILL.md`. The claude-cli patterns are self-contained — no rules/ subdirectory is warranted.
**Warning signs:** Temptation to split single-turn, multi-turn, and security into separate rule files.

### Pitfall 2: Using Verbose Prose Instead of Copy-Paste Code Blocks
**What goes wrong:** Agent reads the skill, understands the concept, but still gets CLAUDECODE error because the code they write from memory omits `env_clean`.
**Why it happens:** Skill documents written as explainers rather than runnable recipes.
**How to avoid:** Every pattern must have a complete, copy-paste-ready code block with no missing imports, no ellipsis, no "fill in the blank." Agents should be able to paste the block directly into a `code_execution_tool` call.
**Reference:** The `shared-browser/SKILL.md` is exemplary — every code block runs verbatim.

### Pitfall 3: Omitting the Scope Warning (Host-Only)
**What goes wrong:** Agent tries to call `claude_single_turn()` from inside a Docker container where `claude` is not installed.
**Why it happens:** Forgetting that claude binary is only on the host, not in the agent-zero Docker container.
**How to avoid:** Include a prominent scope note in the overview: "The claude binary is installed on the host at `~/.local/bin/claude`. This skill applies when Agent Zero runs on the host (development mode, port 50000). Docker container (`code_execution_tool` in a Dockerized Agent Zero) does not have claude in PATH."

### Pitfall 4: Documenting Unverified Flags
**What goes wrong:** Including flags like `--max-turns`, `--fork-session`, `--no-session-persistence` without explaining when NOT to use them.
**Why it happens:** Copying the full `claude --help` flag list into the skill.
**How to avoid:** Only document flags that were empirically tested in Phases 8/9: `--print`, `--output-format json/text`, `--resume UUID`, `--continue`, `--session-id UUID`, `--model`. Mark `--fork-session` and `--no-session-persistence` with explicit "do NOT use for multi-turn" warnings.

### Pitfall 5: Insufficient Security Notes
**What goes wrong:** Skill fails to address all three security areas required by CLAUDE-05 (API key handling, subprocess scope, global env mutation).
**Why it happens:** Security notes feel secondary when the primary goal is "make claude work."
**How to avoid:** Include a dedicated "Security Notes" section with all three items as required by CLAUDE-05 success criteria.

---

## Code Examples

All patterns below are from `python/helpers/claude_cli.py` (empirically verified 2026-02-25).

### Pattern 1: Single-Turn (claude_single_turn)

```python
# Source: python/helpers/claude_cli.py, Phase 8 (ae68ab5) — empirically verified
import sys
sys.path.insert(0, '/a0')  # Agent Zero root
from python.helpers.claude_cli import claude_single_turn

response = claude_single_turn("What is the capital of France?")
print(response)  # "Paris"
```

Or inline (no import needed):
```python
import subprocess, os, json, re

ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}

result = subprocess.run(
    ['claude', '--print', '--output-format', 'json', 'What is the capital of France?'],
    capture_output=True, text=True, env=env_clean, timeout=120
)
data = json.loads(ANSI_RE.sub('', result.stdout).strip())
print(data['result'])  # "Paris"
```

### Pattern 2: Multi-Turn (ClaudeSession)

```python
# Source: python/helpers/claude_cli.py, Phase 9 (38f1489) — empirically verified
from python.helpers.claude_cli import ClaudeSession

session = ClaudeSession()
r1 = session.turn("My name is Alice.")          # "Got it!"
r2 = session.turn("What is my name?")           # "Your name is Alice."
sid = session.session_id                          # UUID string

session.reset()                                   # Start fresh — next turn = new session
```

### Pattern 3: Multi-Turn (claude_turn — manual session_id)

```python
# Source: python/helpers/claude_cli.py, Phase 9 (38f1489) — empirically verified
from python.helpers.claude_cli import claude_turn

# Turn 1 — new session
resp1, sid = claude_turn("My secret number is 42. Reply: GOT_IT")
# resp1 = 'GOT_IT', sid = 'c56c44fa-93ee-4be6-be63-c4c10f3886fe'

# Turn 2 — resume same conversation
resp2, sid = claude_turn("What is my secret number?", session_id=sid)
# resp2 = 'Your secret number is 42.'

# Turn 3 — continue
resp3, sid = claude_turn("Double it.", session_id=sid)
# resp3 = '84'
```

### Pattern 4: Dead Session Recovery

```python
# Source: python/helpers/claude_cli.py, Phase 9 (38f1489) — empirically verified
from python.helpers.claude_cli import claude_turn_with_recovery

# sid may be a stale UUID from a prior run
resp, new_sid, was_recovered = claude_turn_with_recovery(
    "Continue our task.", session_id=sid
)
if was_recovered:
    print("WARNING: Session was lost. Claude has no memory of prior context.")
    # Re-establish context here if needed
```

### Dead Session Error (What It Looks Like)

```
# Command: claude --print --output-format json --resume 00000000-0000-0000-0000-000000000000 "Hello"
returncode: 1
stdout: ''
stderr: 'No conversation found with session ID: 00000000-0000-0000-0000-000000000000\n'
# Exits immediately (~1s) — no API call made
```

### JSON Response Schema (for understanding what the helper parses)

```json
{
    "type": "result",
    "subtype": "success",
    "is_error": false,
    "duration_ms": 5100,
    "result": "Your secret number is 42.",
    "session_id": "c56c44fa-93ee-4be6-be63-c4c10f3886fe",
    "total_cost_usd": 0.0068,
    "usage": { "input_tokens": 25, "cache_read_input_tokens": 16207, "output_tokens": 12 }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PTY/tmux interactive mode for multi-turn | `--resume UUID` with `--print` (repeated subprocess.run) | Discovered Phase 9 | Eliminates idle-timeout, ANSI parsing, response-completion detection entirely |
| Injecting conversation history as context string | `--resume UUID` native session files | Phase 9 | Native session maintains full structured message history; no token inflation |
| `--continue` for multi-turn | `--resume UUID` | Phase 9 decision | `--resume` is explicit by UUID — safe when multiple sessions active in same cwd |
| `env -u CLAUDECODE claude ...` (shell prefix) | `{k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}` (Python dict) | Phase 8 | Python dict approach is scoped to one subprocess call; shell prefix requires terminal runtime |

---

## Open Questions

1. **Session file TTL / automatic cleanup**
   - What we know: Session JSONL files are persistent on disk (`~/.claude/projects/<path>/<uuid>.jsonl`). No TTL found in claude --help output.
   - What's unclear: Does claude have a background cleanup process that deletes old session files?
   - Recommendation: Document as LOW confidence in skill. Callers should use `claude_turn_with_recovery()` defensively to handle dead sessions regardless of cause.

2. **API key source and rotation**
   - What we know: `claude` CLI reads API key from environment (`ANTHROPIC_API_KEY`) or `~/.claude/` config. The env_clean dict passes `ANTHROPIC_API_KEY` through to the subprocess.
   - What's unclear: Whether `~/.claude/` config key takes precedence over env var, or vice versa.
   - Recommendation: Note in security section that the subprocess inherits the parent's API key configuration. No special handling needed in the helper functions.

3. **Prompt caching cost implications for long sessions**
   - What we know: Turn 2 of the multi-turn test showed `cache_read_input_tokens: 16207` — prior turn content was cache-read. Prompt caching reduces cost significantly for sessions with long prior context.
   - What's unclear: At what session length does caching stop helping and cost rises significantly?
   - Recommendation: Worth a brief note in the skill ("prompt caching is automatic; session context is cache-read on subsequent turns, significantly reducing cost per turn"). Not a blocker for Phase 10.

---

## Sources

### Primary (HIGH confidence — empirically verified)

- `python/helpers/claude_cli.py` (Phase 8: ae68ab5, Phase 9: 38f1489) — the complete implementation being documented; all patterns sourced from this file
- `08-01-SUMMARY.md` — live test output: CLAUDE-01a/01b/02+03 PASS, response='PONG', all assertions passed
- `09-01-SUMMARY.md` — live test output: 3-turn memory confirmed (42→84), dead session recovery confirmed, reset() confirmed, ALL TESTS PASSED
- `08-VERIFICATION.md` — 4/4 observable truths verified; all key links confirmed
- `09-VERIFICATION.md` — 4/4 observable truths verified; exact test output preserved (`r1='GOT_IT' r2='Your secret number is **42**.' r3='84'`)
- `usr/skills/shared-browser/SKILL.md` (v4.3) — structural template for the SKILL.md format

### Secondary (MEDIUM confidence)

- `08-RESEARCH.md` — ANSI sequence details, OSC payload behavior, PTY vs capture_output analysis
- `09-RESEARCH.md` — `--resume UUID` vs `--continue` rationale, dead session error format, session file location

---

## Metadata

**Confidence breakdown:**
- Content to document: HIGH — all patterns empirically verified in Phases 8/9
- SKILL.md structure: HIGH — follows established `shared-browser/SKILL.md` template
- Security notes: HIGH — env fix mechanism fully understood; API key handling is standard subprocess inheritance
- Session TTL: LOW — not verified against documentation; `was_recovered` pattern handles this defensively

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (claude CLI version may change; verify `claude --version` before updating)

**Implementation notes for the planner:**

- Phase 10 is ONE task: create `usr/skills/claude-cli/SKILL.md`
- No code changes to any existing file
- No new Python dependencies
- The file to create does NOT yet exist (confirmed: `usr/skills/claude-cli/` directory is absent)
- Verification is structural (file exists, required sections present) — no live API calls needed
- The SKILL.md must satisfy CLAUDE-05's three explicit requirements: (1) single-turn and multi-turn patterns, (2) `--session-id`/`--resume UUID` options, (3) security notes on API key handling and env fix scope
