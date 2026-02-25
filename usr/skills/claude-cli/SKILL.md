# Claude CLI Skill

## Metadata
- name: claude-cli
- version: 1.0
- description: Call the claude CLI from Agent Zero Python runtime — single-turn queries and multi-turn conversations
- tags: [claude, cli, subprocess, multi-turn, env-fix, session]
- author: agent-zero

## Overview

`python/helpers/claude_cli.py` is the implementation module for all claude CLI invocations. Agents can either import from it directly, or copy the standalone inline patterns from this skill.

## DEFAULT CLAUDE CLI RULE

**Load this skill when any task requires calling claude CLI as a subprocess from Agent Zero's Python runtime** — single-turn AI queries, multi-turn AI conversations, or delegating subtasks to claude.

**SCOPE: HOST-ONLY.** The `claude` binary is installed on the host at `~/.local/bin/claude` (on PATH as `claude`). This skill applies when Agent Zero runs on the host (development mode, port 50000). The Docker container (`code_execution_tool` in a Dockerized Agent Zero) does NOT have claude in PATH — if `shutil.which('claude')` returns None, this skill cannot be used.

---

## Stack

| Component | Detail |
|---|---|
| claude CLI | 2.1.56, `~/.local/bin/claude` (on PATH as `claude`) |
| Python runtime | `code_execution_tool` with `runtime="python"` |
| stdlib | `subprocess`, `os`, `json`, `re` — no external dependencies |
| Helper module | `python/helpers/claude_cli.py` (importable from Agent Zero Python runtime at `/a0`) |

---

## Prerequisites + CRITICAL: env fix

```
CRITICAL: Claude Code sets CLAUDECODE=1 in its environment. The claude binary
checks this variable and refuses to launch:
  "claude: error: Claude Code cannot be launched inside another Claude Code session."

Fix: Remove CLAUDECODE from the subprocess env — per-call ONLY, never globally:
  env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}
  subprocess.run(cmd, env=env_clean, ...)

WARNING: NEVER del os.environ['CLAUDECODE'] — that mutates the whole process.
```

This env_clean dict is built inside every function in `claude_cli.py`. All four patterns below include it.

---

## Pattern 1: Single-Turn via import

```python
import sys
sys.path.insert(0, '/a0')
from python.helpers.claude_cli import claude_single_turn

response = claude_single_turn("What is the capital of France?")
print(response)  # "Paris"

# Plain text variant (no JSON metadata):
from python.helpers.claude_cli import claude_single_turn_text
text = claude_single_turn_text("Summarize in one sentence: Agent Zero is ...")
```

---

## Pattern 1b: Single-Turn inline (no import — standalone copy-paste)

```python
import subprocess, os, json, re

ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}

result = subprocess.run(
    ['claude', '--print', '--output-format', 'json', 'What is the capital of France?'],
    capture_output=True, text=True, env=env_clean, timeout=120
)
data = json.loads(ANSI_RE.sub('', result.stdout).strip())
print(data['result'])      # "Paris"
print(data['session_id'])  # UUID (single-turn still creates a session file)
```

---

## Pattern 2: Multi-Turn via ClaudeSession (recommended — session_id managed automatically)

```python
import sys
sys.path.insert(0, '/a0')
from python.helpers.claude_cli import ClaudeSession

session = ClaudeSession()
r1 = session.turn("My name is Alice.")      # "Got it!"
r2 = session.turn("What is my name?")       # "Your name is Alice."
sid = session.session_id                     # UUID string (for coordination)

session.reset()                              # Start fresh — next turn = new session
r3 = session.turn("Hello!")                 # new session, no memory of Alice
```

---

## Pattern 3: Multi-Turn via claude_turn() — manual session_id (for multi-agent coordination)

```python
import sys
sys.path.insert(0, '/a0')
from python.helpers.claude_cli import claude_turn

# Turn 1 — new session (session_id=None starts fresh)
resp1, sid = claude_turn("My secret number is 42. Reply: GOT_IT")
# resp1 = 'GOT_IT', sid = 'c56c44fa-...'

# Turn 2 — resume same conversation
resp2, sid = claude_turn("What is my secret number?", session_id=sid)
# resp2 = 'Your secret number is 42.'

# Turn 3 — continue; pass sid to next turn again
resp3, sid = claude_turn("Double it.", session_id=sid)
# resp3 = '84'
```

---

## Pattern 4: Dead Session Recovery (robust multi-turn)

```python
import sys
sys.path.insert(0, '/a0')
from python.helpers.claude_cli import claude_turn_with_recovery

# sid may be stale from a previous run or expired session
resp, new_sid, was_recovered = claude_turn_with_recovery(
    "Continue our task.", session_id=sid
)
if was_recovered:
    print("WARNING: Session was lost. Claude has no memory of prior context.")
    # Re-establish context here before proceeding
```

Dead session error reference (what it looks like):
```
# Command: claude --print --output-format json --resume 00000000-... "Hello"
returncode: 1
stdout: ''
stderr: 'No conversation found with session ID: 00000000-...\n'
# Exits immediately (~1s) — no API call made
```

JSON response schema (what the helper functions parse):
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

## Decision Guide

| Need | Use |
|---|---|
| One-shot AI query, no memory needed | `claude_single_turn(prompt)` |
| One-shot, plain text only | `claude_single_turn_text(prompt)` |
| Multi-turn conversation, session managed automatically | `ClaudeSession().turn(prompt)` |
| Multi-turn, need session_id to coordinate agents | `claude_turn(prompt, session_id=sid)` |
| Resume a known session from another context | `claude_turn(prompt, session_id='UUID-from-prior-run')` |
| Robust multi-turn with automatic dead-session recovery | `claude_turn_with_recovery(prompt, session_id=sid)` |

---

## Completion Detection

`subprocess.run()` blocks until the process exits. `returncode == 0` = success. `returncode != 0` = failure. **No idle-timeout, no prompt-pattern detection, no PTY needed.** Dead sessions fail immediately (~1s, returncode 1).

---

## ANSI Stripping

With `capture_output=True` (which all functions use), claude emits zero ANSI codes. The `ANSI_RE` strip in every function is a **defensive safety net only** — a no-op in the normal path. Do NOT switch to PTY/TTY mode for programmatic use: PTY output produces OSC sequences that survive naive ANSI strip patterns.

---

## Session Coordination

`--resume UUID` continues an existing session. `--session-id UUID` pre-allocates a UUID before the first turn (for multi-agent coordination — generate UUID with `import uuid; str(uuid.uuid4())`).

Session files are stored at `~/.claude/projects/<cwd-encoded>/<session_id>.jsonl`. The `cwd` must be **consistent across all turns of the same session** — a cwd change results in a dead session on the next `--resume`.

Prompt caching is automatic: subsequent turns cache-read prior context, significantly reducing cost per turn (verified: `cache_read_input_tokens: 16207` on turn 2 of multi-turn tests).

---

## Security Notes

1. **API key handling:** `claude` reads `ANTHROPIC_API_KEY` from env or `~/.claude/` config. The `env_clean` dict comprehension passes `ANTHROPIC_API_KEY` through to the subprocess — correct behavior. Never hardcode API keys in code.

2. **Subprocess scope of env fix:** `env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}` creates a NEW dict for that subprocess ONLY. The parent process `os.environ` is NOT modified. All other Agent Zero subprocesses continue to inherit the unmodified environment. This is the only safe approach.

3. **NEVER globally unset:** `del os.environ['CLAUDECODE']`, `os.unsetenv('CLAUDECODE')`, and shell `unset CLAUDECODE` affect the parent process globally — they break CLAUDECODE=1 detection for any nested Claude Code session logic in the system.

---

## Anti-Patterns (NEVER DO)

- Interactive claude (no `--print`) for programmatic use — TUI rendering, no response boundary, unreliable
- `--continue` instead of `--resume UUID` when multiple sessions may be active (cwd race condition)
- `del os.environ['CLAUDECODE']` or `os.unsetenv()` — global env mutation; use per-call dict only
- Parsing output without `capture_output=True` — PTY mode leaks OSC sequences that survive ANSI_RE strip
- Manually injecting conversation history as context strings — use `--resume UUID` instead (native session preserves structured message history, avoids token inflation)

---

## Common Pitfalls

| Pitfall | Fix |
|---|---|
| CLAUDECODE not removed | Build `env_clean` dict; pass as `env=env_clean` |
| `--continue` picks up wrong session | Use `--resume UUID` (explicit, no cwd race) |
| cwd changes between turns | Pass same `cwd=` to all subprocess.run calls for a session |
| `--no-session-persistence` + `--resume` | Session file not written → dead session immediately |
| Timeout too short | Increase timeout (default 120s); check API connectivity |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `claude: error: Cannot be launched inside another Claude Code session` | Add env_clean dict; pass `env=env_clean` |
| `json.loads JSONDecodeError: Extra data` | Not using `capture_output=True` — switch to subprocess.run(capture_output=True) |
| `RuntimeError: No conversation found with session ID:` | Session dead/expired — use `claude_turn_with_recovery()` or restart with `session_id=None` |
| `FileNotFoundError` for claude | claude binary not on PATH — check `shutil.which('claude')` or verify `~/.local/bin` is on PATH |
| `TimeoutExpired` | Increase timeout; check API connectivity |
| Session memory lost between turns | session_id not passed — use ClaudeSession to manage automatically |
| `--resume` finds wrong session | cwd changed between turns — ensure consistent cwd= in all subprocess.run calls |
| Skill doesn't apply | This skill is HOST-ONLY. Claude binary is not installed in Docker container |
