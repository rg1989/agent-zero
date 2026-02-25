# Phase 9: Claude CLI Multi-Turn Sessions - Research

**Researched:** 2026-02-25
**Domain:** Claude CLI multi-turn session management, `--resume` flag, session_id persistence
**Confidence:** HIGH (all key findings empirically verified on claude 2.1.56 on this host)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLAUDE-04 | Agent Zero can run a multi-turn interactive `claude` session using a persistent PTY (`code_execution_tool` or shared tmux), sending follow-up prompts and reading responses with combined idle-timeout + prompt-pattern completion detection | **Research finding: PTY interactive mode is the wrong approach.** The right approach is `--resume UUID` with `--print` (repeated subprocess.run calls), which avoids idle-timeout and prompt-pattern detection entirely. The requirement language says "persistent PTY or shared tmux" but the intent — multi-turn conversation with memory — is fully satisfied by `--resume --print`. The combined idle-timeout + prompt-pattern detection is ONLY needed if the interactive TUI mode is used; the `--resume` approach requires only `returncode` checking (same as single-turn). |
</phase_requirements>

---

## Summary

Phase 9's goal is to enable Agent Zero to conduct multi-turn conversations with claude CLI where each turn has access to conversation history. Phase 8 established the single-turn pattern (`subprocess.run` + `--print` + `capture_output=True`). Phase 9 extends this with the `--resume UUID` flag, which turns any sequence of `--print` calls into a continuous conversation with shared memory.

**Critical discovery:** The requirement text mentions "persistent PTY session" and "combined idle-timeout + prompt-pattern detection." Empirical testing reveals that claude's interactive (non-`--print`) mode uses a full TUI renderer with complex ANSI/CSI/control sequences that make reliable response-completion detection extremely difficult. The interactive mode renders a splash screen, sends user input to a rich UI, and does not produce clean parseable output. In contrast, `claude --print --resume UUID` uses the same subprocess.run approach from Phase 8, adds zero new infrastructure, gives clean JSON output, and delivers multi-turn context through the session file system that claude maintains at `~/.claude/projects/<path>/<session_id>.jsonl`.

**Dead session detection:** When `--resume` is called with an invalid or expired session UUID, claude exits immediately with returncode 1 and stderr `"No conversation found with session ID: <UUID>"`. This is clean, unambiguous, and detectable with standard `returncode` checking — no polling or pattern matching required.

**Primary recommendation:** Implement multi-turn via repeated `subprocess.run` calls with `--print --output-format json --resume session_id`. Extract `session_id` from the first turn's JSON response, pass it as `--resume` on all subsequent turns. Dead-session detection is `returncode != 0` plus stderr string check. No PTY, no idle-timeout, no prompt-pattern detection needed.

---

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `claude` CLI | 2.1.56 (Claude Code) | AI inference subprocess | Already installed at `~/.local/bin/claude`; `--resume` flag confirmed in this version |
| `subprocess` (stdlib) | Python 3.x stdlib | Launch claude as child process per turn | Same as Phase 8 pattern; `capture_output=True` eliminates TTY issues |
| `os.environ` (stdlib) | Python 3.x stdlib | Build CLAUDECODE-free env dict | Same as Phase 8; per-call dict comprehension |
| `json` (stdlib) | Python 3.x stdlib | Parse `--output-format json` response | Same as Phase 8; `.result` + `.session_id` fields |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `--resume UUID` flag | claude 2.1.56 | Continue an existing conversation by session UUID | Every turn after the first in a multi-turn session |
| `--continue` flag | claude 2.1.56 | Continue the most recent session in cwd | Simpler alternative when only one conversation is active in the cwd |
| `--session-id UUID` flag | claude 2.1.56 | Pre-allocate a UUID for a new session | Useful for coordination when session_id must be known before the first turn |
| `--fork-session` flag | claude 2.1.56 | When resuming, create a new session ID instead of reusing the original | Useful for branching a conversation (parallel explorations from one base) |
| `--no-session-persistence` flag | claude 2.1.56 | Disable session file writing | Stateless single-turn only — do NOT use this for multi-turn |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `--resume UUID` with `--print` (recommended) | Interactive PTY mode | PTY mode uses TUI rendering with complex ANSI sequences, no clean response boundary, idle-timeout is unreliable during claude thinking pauses; `--resume` is clean and deterministic |
| `--resume UUID` with `--print` | tmux + `send-keys` | tmux approach requires shell session management, pane output capture, and the same prompt-detection problems as PTY; `--resume` is simpler |
| `--resume UUID` with `--print` | stdin pipe to interactive claude | Interactive mode does not support stdin prompts cleanly; TUI mode renders differently than text I/O mode |
| Per-call `subprocess.run` | Long-running `subprocess.Popen` with stdin/stdout | Popen requires idle-timeout + prompt-pattern detection; subprocess.run blocks until complete, exit is clean signal |

---

## Architecture Patterns

### Recommended Multi-Turn Structure

```
ClaudeMultiTurnSession (python/helpers/claude_cli.py)
├── __init__(session_id=None)     # None = new session
├── turn(prompt) -> str           # calls subprocess.run, returns text
│   ├── if self._session_id:      # resume existing session
│   │   └── cmd += ['--resume', self._session_id]
│   ├── subprocess.run(capture_output=True, env=env_clean, timeout=N)
│   ├── on success: store session_id from JSON response
│   ├── on returncode != 0: raise with stderr (catches dead session)
│   └── return data['result']
├── session_id property           # read-only access to current session UUID
└── reset()                       # clear session_id, next turn starts fresh
```

### Pattern 1: Multi-Turn via --resume --print (RECOMMENDED)

**What:** Chain multiple `subprocess.run` calls, each passing `--resume session_id` from the previous response.
**When to use:** All multi-turn interactions in Phase 9. This is THE implementation approach.

```python
# Source: empirically verified 2026-02-25 on claude 2.1.56
import subprocess, os, json, re

ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def _env_clean():
    """Build env dict with CLAUDECODE removed."""
    return {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}

def claude_turn(prompt, session_id=None, model=None, timeout=120):
    """
    Execute one turn of a claude conversation.

    Args:
        prompt: User prompt text.
        session_id: UUID string from a previous turn, or None for a new session.
        model: Optional model override.
        timeout: Max seconds to wait. Default 120s.

    Returns:
        (response_text: str, session_id: str)
        The session_id returned should be passed to the next claude_turn() call.

    Raises:
        RuntimeError: Non-zero exit (incl. dead session), binary not found, timeout.
        RuntimeError with "No conversation found" in message: dead/expired session.
    """
    cmd = ['claude', '--print', '--output-format', 'json']
    if model:
        cmd += ['--model', model]
    if session_id:
        cmd += ['--resume', session_id]
    cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=_env_clean(),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"claude turn timed out after {timeout}s")
    except FileNotFoundError:
        raise RuntimeError("claude binary not found in PATH")

    if result.returncode != 0:
        err = (result.stderr.strip() or result.stdout.strip())[:400]
        raise RuntimeError(f"claude exited {result.returncode}: {err}")

    stdout_clean = ANSI_RE.sub('', result.stdout).strip()
    data = json.loads(stdout_clean)

    if data.get('is_error'):
        raise RuntimeError(f"claude API error: {data.get('result', 'unknown')}")

    return data['result'], data['session_id']


# Usage:
resp1, sid = claude_turn("My favorite color is blue. Reply: GOT_IT")
# resp1 = 'GOT_IT', sid = 'c56c44fa-93ee-4be6-be63-c4c10f3886fe'

resp2, sid = claude_turn("What is my favorite color?", session_id=sid)
# resp2 = 'Blue. You told me at the start of this conversation.'

resp3, sid = claude_turn("Give me a one-sentence poem about that color.", session_id=sid)
# resp3 = 'The ocean wears blue like a crown it never takes off.'
```

**Empirically verified:** All three turns complete successfully with conversation memory intact. Session_id is stable across turns (same UUID returned). Total duration ~20s for 3 turns (5-10s each).

### Pattern 2: Stateful Session Class

**What:** Wrap `claude_turn()` in a class that tracks session_id state.
**When to use:** When code_execution_tool Python runtime block needs to maintain a session across multiple Agent Zero actions.

```python
# Source: empirically verified pattern based on 2026-02-25 testing
class ClaudeSession:
    """Persistent multi-turn claude session."""
    def __init__(self, model=None, timeout=120):
        self._session_id = None
        self._model = model
        self._timeout = timeout

    def turn(self, prompt):
        """Send one turn, return response text. Remembers session_id."""
        response, self._session_id = claude_turn(
            prompt,
            session_id=self._session_id,
            model=self._model,
            timeout=self._timeout,
        )
        return response

    def reset(self):
        """Start a new conversation (next turn creates new session)."""
        self._session_id = None

    @property
    def session_id(self):
        return self._session_id


# Usage:
session = ClaudeSession()
print(session.turn("My name is Alice."))    # GOT_IT (or similar)
print(session.turn("What is my name?"))    # "Your name is Alice."
print(session.session_id)                  # 'c56c44fa-...'
```

### Pattern 3: Dead Session Detection and Recovery

**What:** Detect when `--resume UUID` fails because the session no longer exists, then start a fresh session.
**When to use:** Long-running agent workflows where sessions may expire between turns.

```python
# Source: empirically verified 2026-02-25
def claude_turn_with_recovery(prompt, session_id=None, timeout=120):
    """
    claude_turn() with automatic dead session recovery.
    If session_id is stale/expired, starts a fresh conversation automatically.
    Returns (response, new_session_id, was_recovered).
    """
    try:
        response, new_sid = claude_turn(prompt, session_id=session_id, timeout=timeout)
        return response, new_sid, False
    except RuntimeError as e:
        err_msg = str(e)
        # Dead session: "claude exited 1: No conversation found with session ID: UUID"
        if session_id and 'No conversation found' in err_msg:
            # Start fresh session — context is lost
            response, new_sid = claude_turn(prompt, session_id=None, timeout=timeout)
            return response, new_sid, True  # was_recovered=True
        raise  # Re-raise non-recoverable errors

# Dead session error is deterministic:
# returncode=1, stderr="No conversation found with session ID: 00000000-..."
# - confirmed empirically 2026-02-25
# - exits IMMEDIATELY (no timeout wait), ~1s
```

### Anti-Patterns to Avoid

- **Interactive PTY mode for multi-turn:** `claude` without `--print` uses a full TUI rendering engine. The startup banner contains complex ANSI sequences. User input is echoed with cursor-movement sequences. AI response boundaries are not delimited — they blend into the UI chrome. Idle-timeout detection will trigger false "done" signals during claude's thinking pauses (1-3s). This path is extremely fragile for programmatic use.
- **Idle-timeout alone for response completion:** Even in `--print` mode with streaming, idle-timeout alone is unreliable because the Anthropic API can have multi-second pauses within a single response (streaming tokens). Use process `returncode` (clean exit) as the completion signal — it is unambiguous.
- **Global session_id storage in os.environ:** Session UUIDs are ephemeral per-conversation; storing them globally causes stale session problems across unrelated agent actions.
- **`--no-session-persistence` for multi-turn:** This flag prevents claude from writing session JSONL files. Using it with `--resume` would fail because the session history does not exist on disk. Only use `--no-session-persistence` for truly stateless single-turn calls.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-turn conversation memory | Custom conversation history dict passed as context string | `--resume UUID` flag | claude's native session system maintains message history including tool use; injecting history as text loses the structured message format and inflates token counts |
| Response completion detection | Idle-timeout polling loop on PTY output | `subprocess.run()` process exit | Process exit is unambiguous; idle-timeout has false positives during AI thinking pauses; PTY adds ANSI noise |
| Dead session recovery | Polling/retrying the same session UUID | Check `returncode != 0` + `'No conversation found' in stderr` | Claude exits immediately and deterministically for invalid sessions; no retry loop needed |
| Session UUID generation | `uuid.uuid4()` pre-allocation | Let claude generate session_id on first `--print` turn | The UUID in the JSON response `.session_id` field is the canonical ID; pre-allocating via `--session-id` is possible but unnecessary for normal multi-turn use |
| Per-turn ANSI stripping | Custom regex matching all terminal sequences | Same `ANSI_RE` from Phase 8, already a no-op with `capture_output=True` | `subprocess.run(capture_output=True)` with `--print` produces clean stdout with no ANSI; stripping is defensive only |

**Key insight:** The `--resume UUID` approach extends the Phase 8 pattern by adding exactly one flag and one return value. No new infrastructure, no timeout calibration, no prompt-pattern research. The implementation is essentially identical to Phase 8 with session_id tracking added.

---

## Common Pitfalls

### Pitfall 1: Using Interactive PTY Mode Instead of --resume --print

**What goes wrong:** The agent gets stuck waiting for response completion, or incorrectly detects "done" during a thinking pause, or cannot parse the response from TUI rendering output.
**Why it happens:** claude's interactive (TUI) mode uses an Ink/React-based renderer that writes complex terminal UI sequences (cursor movement, color codes, box-drawing characters) interspersed with response text. There is no clear delimiter between "thinking" and "response complete." Idle-timeout fires during 1-3s pauses within a single streaming response.
**How to avoid:** Always use `claude --print` for programmatic multi-turn. Use `--resume UUID` to maintain session continuity.
**Warning signs:** Prompt contains ANSI art/UI chrome; `read_full_until_idle` returns partial response; second prompt gets mixed into first response output.

### Pitfall 2: Losing session_id Between Turns

**What goes wrong:** Each call starts a new session instead of continuing the conversation. Claude has no memory of previous turns.
**Why it happens:** Forgetting to extract `session_id` from the JSON response and pass it to the next turn. Or using `--no-session-persistence` which prevents session files from being written.
**How to avoid:** Always extract `data['session_id']` from the JSON response and store it. Pass it as `--resume session_id` on every subsequent turn. Never use `--no-session-persistence` in multi-turn context.
**Warning signs:** Claude says "I don't have any context about what you told me earlier"; session_id in response keeps changing (new UUID each turn).

### Pitfall 3: Stale/Expired Session ID

**What goes wrong:** `claude_turn(prompt, session_id=old_uuid)` fails with `RuntimeError: claude exited 1: No conversation found with session ID: ...`
**Why it happens:** claude sessions are stored as JSONL files in `~/.claude/projects/<cwd-path>/<uuid>.jsonl`. If the file is deleted, the cwd changes (different project path), or the session is from a different machine, the resume fails.
**How to avoid:** Catch `RuntimeError` containing `'No conversation found'` and restart with `session_id=None`. Warn the agent that conversation context was lost and it may need to re-establish context.
**Warning signs:** `returncode == 1` on first post-restart resume; stderr contains exact string "No conversation found with session ID:".

### Pitfall 4: Idle-Timeout Calibration for Thinking Pauses

**What goes wrong:** If the PTY approach is used despite recommendation (e.g., for interactive display), `read_full_until_idle(idle_timeout=N)` triggers "done" during a 2-3s thinking pause mid-response.
**Why it happens:** The Anthropic API can pause streaming for 1-3s while the model reasons about a complex turn. An idle_timeout < 3s will fire a false "complete" signal.
**How to avoid:** Do not use PTY mode for multi-turn. If PTY is unavoidable, use idle_timeout >= 5s AND implement a prompt-pattern check — confirm the claude prompt marker is present before accepting "complete."
**Warning signs:** Partial responses that end mid-sentence; response picks up mid-sentence when the next prompt is sent.
**Empirical note from STATE.md:** "[Phase 9] Idle-timeout calibration for multi-turn requires profiling claude's natural pause durations (1-2s thinking pauses can trigger false 'done' signals)." This concern is ELIMINATED by using `--resume --print` instead of PTY mode.

### Pitfall 5: CWD Affects Which Session Files Are Found

**What goes wrong:** `--resume UUID` succeeds from project root but fails from a different working directory (or vice versa).
**Why it happens:** claude stores session files at `~/.claude/projects/<cwd-encoded-path>/<session_id>.jsonl`. The path is encoded from the cwd at session creation time. If the cwd changes between turns, claude looks in a different project directory for the session file.
**How to avoid:** Ensure all `subprocess.run` calls for a given session use the same `cwd=` argument. If no `cwd` is specified, all calls will use the process's cwd, which is stable across `subprocess.run` calls in Agent Zero's Python runtime.
**Warning signs:** Session resumes successfully sometimes but fails other times with "No conversation found" despite using the same UUID.

---

## Code Examples

Empirically verified patterns (2026-02-25, claude 2.1.56):

### Multi-Turn Chain — Three Turns With Memory

```python
# Source: empirically verified 2026-02-25
import subprocess, os, json, re

ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def claude_turn(prompt, session_id=None, model=None, timeout=120):
    env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}
    cmd = ['claude', '--print', '--output-format', 'json']
    if model:
        cmd += ['--model', model]
    if session_id:
        cmd += ['--resume', session_id]
    cmd.append(prompt)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env_clean, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"claude exited {result.returncode}: {result.stderr.strip()[:400]}")
    data = json.loads(ANSI_RE.sub('', result.stdout).strip())
    if data.get('is_error'):
        raise RuntimeError(f"API error: {data.get('result')}")
    return data['result'], data['session_id']

# Turn 1 — new session
resp1, sid = claude_turn("My favorite color is blue. Reply: GOT_IT")
# resp1 = 'GOT_IT', sid = 'c56c44fa-93ee-4be6-be63-c4c10f3886fe'  (real test output)

# Turn 2 — resume
resp2, sid = claude_turn("What is my favorite color?", session_id=sid)
# resp2 = 'Blue. You told me at the start of this conversation.'  (real test output)

# Turn 3 — continue
resp3, sid = claude_turn("Give me a one-sentence poem about that color.", session_id=sid)
# resp3 = 'The ocean wears blue like a crown it never takes off.'  (real test output)
```

### Dead Session Error Response

```
# Source: empirically verified 2026-02-25
# Command: claude --print --output-format json --resume 00000000-0000-0000-0000-000000000000 "Hello"
returncode: 1
stdout: ''  (empty)
stderr: 'No conversation found with session ID: 00000000-0000-0000-0000-000000000000\n'
# Exit is IMMEDIATE (~1s, no API call made)
```

### --continue Flag (Most Recent Session)

```python
# Source: empirically verified 2026-02-25
# --continue resumes the most recent session in the current directory
result = subprocess.run(
    ['claude', '--print', '--output-format', 'json', '--continue', 'Just say: CONTINUED'],
    capture_output=True, text=True, env=env_clean, timeout=120
)
# returncode: 0
# result JSON: {"type":"result","subtype":"success",...,"result":"CONTINUED","session_id":"09a92355-..."}
```

### JSON Response Schema (same as Phase 8, confirming session_id field)

```json
{
    "type": "result",
    "subtype": "success",
    "is_error": false,
    "duration_ms": 5100,
    "duration_api_ms": 4800,
    "num_turns": 1,
    "result": "Blue. You told me at the start of this conversation.",
    "stop_reason": null,
    "session_id": "c56c44fa-93ee-4be6-be63-c4c10f3886fe",
    "total_cost_usd": 0.0068,
    "usage": { "input_tokens": 25, "cache_read_input_tokens": 16207, "output_tokens": 12 }
}
```

The `session_id` field is present and stable across all turns of the same conversation (same UUID returned on turns 1, 2, and 3 of the same session — confirmed empirically).

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| PTY + idle-timeout for multi-turn | `--resume UUID` with `--print` | PTY approach fragile; `--resume` is the native multi-turn mechanism |
| Pass conversation history as context string | `--resume UUID` native session | Native session maintains full message history including tool calls; no token inflation |
| Custom prompt-pattern detection (e.g. `❯ `) | Process `returncode` only | `returncode` is unambiguous; prompt-pattern detection only needed for PTY TUI mode which is not the recommended path |

**Current claude CLI version:** 2.1.56 (as of 2026-02-25, updated from 2.1.55 during Phase 9 research)

**Key flags for Phase 9:**
- `--resume UUID`: Continue a conversation by session UUID (THE multi-turn mechanism)
- `--continue` / `-c`: Continue most recent session in cwd (no UUID needed)
- `--session-id UUID`: Pre-specify UUID for a new session (for coordination scenarios)
- `--fork-session`: When resuming, create new UUID branch (parallel exploration)
- `--no-session-persistence`: DISABLE for multi-turn; for single-turn stateless calls only

**Session file location:** `~/.claude/projects/<cwd-path-encoded>/<session_id>.jsonl`
- Files persist across process restarts
- JSONL format with per-message entries
- Dead session = file not found → `returncode 1`, stderr "No conversation found with session ID: ..."

---

## Open Questions

1. **Session expiry policy**
   - What we know: Session files are persistent on disk (JSONL format confirmed); `--resume` with a fake UUID fails immediately with returncode 1.
   - What's unclear: Does claude have a TTL or cleanup policy that deletes old session files? (Could not verify from help output or docs.)
   - Recommendation: Treat any `returncode != 0` with "No conversation found" as a dead session and restart gracefully. Do not assume sessions are permanent. The session file for our resume test (`c56c44fa-...`) was confirmed on disk after the test.

2. **Session files are cwd-scoped — Docker vs host context**
   - What we know: Session files stored at `~/.claude/projects/<cwd-encoded>/<uuid>.jsonl`. All Agent Zero multi-turn use is currently host-side (claude not in Docker container).
   - What's unclear: If Agent Zero runs in Docker and claude is somehow available there, the home directory path for session storage may differ.
   - Recommendation: Document that Phase 9 is host-context only (same as Phase 8). No Docker scope change.

3. **`--continue` vs `--resume UUID` for the Phase 9 implementation**
   - What we know: `--continue` uses most-recent session per cwd; `--resume UUID` is explicit by session identifier. Both confirmed working.
   - What's unclear: Whether multiple concurrent agent sessions in the same cwd would cause `--continue` to race/conflict.
   - Recommendation: Use `--resume UUID` (explicit), not `--continue`. Explicit is safer when multiple sessions could be active.

4. **Cost of resuming a long session**
   - What we know: Turn 2 of the resume test showed `cache_read_input_tokens: 16207` — the prior turn's content was cache-read. This suggests claude's session system uses prompt caching automatically.
   - What's unclear: At what session length does prompt caching stop helping and costs rise significantly?
   - Recommendation: Not a Phase 9 concern — note as a usage consideration in Phase 10 SKILL.md.

---

## Sources

### Primary (HIGH confidence — empirically tested)

- `claude 2.1.56` binary at `/Users/rgv250cc/.local/bin/claude` — all multi-turn behaviors verified by direct execution
- **Resume chain test** (`/tmp/test_resume_chain.py`) — 3-turn conversation with memory confirmed; session_id stable; durations 5-10s per turn
- **Dead session test** (`/tmp/test_dead_session.py`) — `returncode=1`, `stderr='No conversation found with session ID: 00000000-0000-0000-0000-000000000000\n'` confirmed; exits immediately
- **`--continue` test** — confirmed `returncode=0`, continues most recent session; session_id returned in JSON
- **Interactive PTY test** (`/tmp/test_claude_interactive_v3.py`) — confirmed TUI rendering complexity; AI responses NOT readable from PTY output in the test (prompt input echoed with UI chrome; no clean response text extracted)
- `claude --help` output — `--resume`, `--continue`, `--session-id`, `--fork-session`, `--no-session-persistence` flags confirmed in version 2.1.56
- `~/.claude/projects/` directory structure — session JSONL files confirmed; cwd-encoded path structure confirmed

### Secondary (MEDIUM confidence)

- Phase 8 research (`08-RESEARCH.md`) — `ANSI_RE` pattern, `env_clean` pattern, `capture_output=True` approach — all reused unchanged
- Phase 8 summary (`08-01-SUMMARY.md`) — confirms `claude_cli.py` as the foundation; multi-turn builds on single-turn helper

### Tertiary (LOW confidence — not independently verified)

- Session expiry/TTL: assumed persistent until deleted; not verified against documentation

---

## Metadata

**Confidence breakdown:**
- `--resume UUID` multi-turn approach: HIGH — empirically confirmed 3-turn chain with memory
- Dead session detection: HIGH — empirically confirmed returncode=1 + exact stderr message
- `--continue` flag: HIGH — empirically confirmed works as described in help
- Interactive PTY: HIGH — empirically confirmed TUI complexity makes it unsuitable
- Session file location/format: HIGH — confirmed directory structure and JSONL format
- Session expiry policy: LOW — not verified; assumed persistent files

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (claude CLI version may change; verify `claude --version` before implementing)

**Key empirical test commands (reproducible):**
```bash
# Multi-turn resume chain (3 turns):
python3 /tmp/test_resume_chain.py

# Dead session detection:
python3 /tmp/test_dead_session.py

# Interactive PTY mode (confirms TUI complexity):
python3 /tmp/test_claude_interactive_v3.py
```
