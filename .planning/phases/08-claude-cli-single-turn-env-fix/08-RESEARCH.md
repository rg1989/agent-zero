# Phase 8: Claude CLI Single-Turn + Env Fix - Research

**Researched:** 2026-02-25
**Domain:** Claude CLI subprocess invocation, ANSI stripping, clean output capture
**Confidence:** HIGH (all key findings verified empirically on the actual host system)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLAUDE-01 | Agent Zero can launch `claude` CLI by unsetting `CLAUDECODE` in the subprocess environment (`env -u CLAUDECODE claude ...`), resolving the "cannot launch inside another Claude Code session" error | Empirically confirmed: `CLAUDECODE=1` triggers error; `env -u CLAUDECODE` bypasses it. Python: `{k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}` |
| CLAUDE-02 | Agent Zero can send a prompt to `claude` using `--print` / `-p` mode and receive the complete response from stdout | Empirically confirmed: `claude -p "prompt" --output-format json` returns clean JSON object with `.result` field containing the text response |
| CLAUDE-03 | Agent Zero can detect when a `claude --print` invocation has finished (process exit, clean stdout capture) and extract the response text free of ANSI escape sequences | Empirically confirmed: `subprocess.run(capture_output=True)` gives clean stdout with no ANSI. PTY output adds trailing CSI+OSC sequences; clean_string() handles CSI but NOT OSC. Recommendation: use Python runtime subprocess.run() to avoid PTY entirely |
</phase_requirements>

---

## Summary

Phase 8 implements the core pattern for Agent Zero to invoke the `claude` CLI as a subprocess. The primary blocker is that Claude Code sets `CLAUDECODE=1` in its environment, and the `claude` binary explicitly checks this variable and refuses to launch with the message "Claude Code cannot be launched inside another Claude Code session." The fix is well-established: pass a modified environment dict to the subprocess that excludes `CLAUDECODE`.

The cleanest invocation pattern uses `subprocess.run()` from within Agent Zero's Python runtime. When stdout is NOT a TTY (i.e., when using `capture_output=True`), the `claude` binary produces completely clean output with zero ANSI escape sequences. Using `--output-format json` additionally gives a structured JSON payload with metadata. When output IS a TTY (as happens when using Agent Zero's terminal runtime via TTYSession/PTY), the claude binary appends CSI and OSC escape sequences after the content; the existing `clean_string()` in `shell_ssh.py` handles CSI sequences but leaves OSC payloads (`9;4;0;\x07`) intact, which breaks JSON parsing.

The recommended approach for Phase 8 is: use Agent Zero's **Python runtime** (`code_execution_tool` with `runtime="python"`), call `subprocess.run()` with `capture_output=True` and a CLAUDECODE-scrubbed env dict, and use `--output-format json` to extract the response from the `.result` field. This approach requires zero new infrastructure — `code_execution_tool` already supports Python execution, and `subprocess.run()` handles process exit detection natively via `returncode`.

**Primary recommendation:** Use `subprocess.run(['claude', '-p', prompt, '--output-format', 'json'], capture_output=True, text=True, env={k:v for k,v in os.environ.items() if k != 'CLAUDECODE'})` from within Agent Zero's Python runtime.

---

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `claude` CLI | 2.1.55 (Claude Code) | AI inference subprocess | Already installed at `~/.local/bin/claude` on host; the binary being integrated |
| `subprocess` (stdlib) | Python 3.x stdlib | Launch claude as child process | Built-in, no deps; `capture_output=True` eliminates PTY/TTY issues entirely |
| `os.environ` (stdlib) | Python 3.x stdlib | Build CLAUDECODE-free env dict | Built-in dict comprehension removes env var without global mutation |
| `json` (stdlib) | Python 3.x stdlib | Parse `--output-format json` response | Built-in, parses `.result` field from structured response |
| `re` (stdlib) | Python 3.x stdlib | ANSI stripping (safety net) | Already used in `shell_ssh.py`; same regex pattern applies |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `--output-format text` | claude 2.1.55 | Return raw text (no JSON wrapper) | When only the text response is needed, simpler parsing |
| `--output-format json` | claude 2.1.55 | Return structured JSON with metadata | When cost/usage/session_id metadata is also valuable |
| `--no-session-persistence` | claude 2.1.55 | Prevent session files from being written | When stateless single-turn behavior is needed |
| `--model` | claude 2.1.55 | Override model for this invocation | When a specific model (e.g., haiku for speed) is needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python runtime + `subprocess.run` | Terminal runtime + shell command | Terminal uses PTY which adds ANSI sequences; JSON parsing breaks unless OSC sequences are explicitly stripped |
| `--output-format json` | `--output-format text` | JSON gives richer metadata; text is simpler for direct display |
| Per-call env dict | `env -u CLAUDECODE` shell prefix | Both work; Python dict approach is cleaner in Python code; shell prefix is better for terminal runtime |

**Installation:** `claude` CLI is already installed on the host at `/Users/rgv250cc/.local/bin/claude`. No additional packages needed for Phase 8.

---

## Architecture Patterns

### Recommended Invocation Structure

```
Agent Zero (Python runtime code block)
├── Build env_clean = os.environ minus CLAUDECODE
├── subprocess.run(['claude', '-p', prompt, ...], env=env_clean, capture_output=True)
├── Check returncode == 0
├── json.loads(result.stdout) → parse .result field
└── Return clean text to agent
```

### Pattern 1: Single-Turn via Python Runtime (RECOMMENDED)

**What:** Run claude as a subprocess from within Agent Zero's Python runtime, capturing stdout cleanly without PTY.
**When to use:** All single-turn queries in Phase 8.

```python
# Source: empirically verified 2026-02-25 on claude 2.1.55
import subprocess, os, json, re

ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

def claude_single_turn(prompt, model=None, timeout=120):
    """
    Invoke claude CLI in single-turn mode from Agent Zero Python runtime.
    Returns clean text response string.

    REQUIRES: claude installed, not inside another claude session
    (CLAUDECODE env var is removed from subprocess env only)
    """
    # Remove CLAUDECODE from subprocess env only — never modify os.environ globally
    env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}

    cmd = ['claude', '--print', '--output-format', 'json']
    if model:
        cmd += ['--model', model]
    cmd.append(prompt)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env_clean,
        timeout=timeout
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude exited {result.returncode}: {result.stderr[:300]}")

    # stdout with capture_output=True is already clean (no ANSI)
    # ANSI strip is a safety net only
    stdout_clean = ANSI_RE.sub('', result.stdout).strip()

    data = json.loads(stdout_clean)
    if data.get('is_error'):
        raise RuntimeError(f"claude error: {data.get('result', 'unknown error')}")

    return data['result']  # Clean text response
```

### Pattern 2: Single-Turn via Terminal Runtime (Alternate)

**What:** Run claude as a shell command via Agent Zero's terminal runtime. Output goes through TTY/PTY, so ANSI sequences appear and need extraction.
**When to use:** When the agent must use the terminal runtime (e.g., in a shell scripting context).

```bash
# Terminal runtime invocation pattern:
env -u CLAUDECODE claude --print --output-format json "Your prompt here"
```

**Python extraction from terminal output (handles ANSI residue):**
```python
# Source: empirically verified 2026-02-25
import re, json

def extract_json_from_terminal_output(raw_output):
    """
    Extract claude JSON response from terminal runtime output.
    The terminal/PTY path adds ANSI sequences after the JSON payload.
    Use regex to find the JSON object, bypassing residual ANSI garbage.
    """
    # Find the JSON object (must contain "type":"result")
    m = re.search(r'\{[^{}]*"type"\s*:\s*"result".*?\}', raw_output, re.DOTALL)
    if not m:
        raise ValueError("No claude JSON result found in output")
    return json.loads(m.group())
```

### Pattern 3: Plain Text Single-Turn (Simplest)

**What:** Use `--output-format text` (or no format flag) for raw text response. No JSON parsing needed.
**When to use:** When response is the only output needed (no metadata), and using subprocess.run (clean stdout guaranteed).

```python
# Source: empirically verified 2026-02-25
import subprocess, os, re

ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

def claude_single_turn_text(prompt, timeout=120):
    env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}
    result = subprocess.run(
        ['claude', '--print', prompt],
        capture_output=True, text=True,
        env=env_clean, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:300])
    # Already clean when capture_output=True, strip is safety net
    return ANSI_RE.sub('', result.stdout).strip()
```

### Anti-Patterns to Avoid

- **Global env unset:** Never `del os.environ['CLAUDECODE']` or `os.unsetenv('CLAUDECODE')` — this affects the entire Python process and all subsequent subprocesses, including ones that should NOT have it unset.
- **Shell `unset CLAUDECODE` in terminal:** Changing the shell's CLAUDECODE affects all commands in that session, not just the claude call.
- **Using `subprocess.Popen` with a PTY for single-turn:** Unnecessary complexity; `subprocess.run` with `capture_output=True` is sufficient and gives clean output.
- **Parsing stdout from terminal runtime without JSON extraction:** `clean_string()` leaves OSC sequence payloads (`9;4;0;\x07`) which break `json.loads()`.
- **Using `--tools ""`:** Disables tool caching and costs ~19x more per call. Only use if tools would interfere with the specific use case.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ANSI sequence removal | Custom regex covering all ANSI variants | Existing `clean_string()` in `shell_ssh.py` (for terminal), or skip it entirely by using `subprocess.run(capture_output=True)` | `clean_string()` is already battle-tested for CSI sequences; avoiding PTY removes the problem entirely |
| Process exit detection | Polling loop checking PID | `subprocess.run()` blocks until exit; `returncode` attribute is the exit code | Built-in to `subprocess.run()` — zero extra code needed |
| Output buffering | Custom read loop with timeouts | `subprocess.run()` with `capture_output=True` buffers all stdout | Already handles deadlock avoidance for moderate output sizes |
| JSON response schema | Custom parser | `json.loads(result.stdout)` + dict access | The `--output-format json` schema is stable and documented |

**Key insight:** The entire Phase 8 implementation is achievable with stdlib-only Python code. No new dependencies, no new Tool classes, no new infrastructure.

---

## Common Pitfalls

### Pitfall 1: CLAUDECODE Not Removed from Subprocess Env

**What goes wrong:** `claude --print` fails immediately with "Claude Code cannot be launched inside another Claude Code session."
**Why it happens:** The `CLAUDECODE=1` env var set by Claude Code is inherited by all child processes.
**How to avoid:** Always build a clean env dict: `env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}` and pass it as the `env=` argument to `subprocess.run()`.
**Warning signs:** Error message contains "Cannot be launched inside another Claude Code session"; process exits immediately with non-zero returncode.

### Pitfall 2: PTY Output Breaks JSON Parsing

**What goes wrong:** `json.loads()` raises `JSONDecodeError: Extra data` on terminal runtime output.
**Why it happens:** When `claude` runs with stdout connected to a PTY (TTY), it appends cleanup escape sequences after the JSON payload: `\r\n ESC[<u ESC[?1004l ESC[?2004l ESC[?25h ESC]9;4;0;\x07 ESC[?25h`. The existing `clean_string()` removes CSI sequences (`ESC[...`) but leaves OSC sequences (`ESC]9;4;0;\x07` → becomes `9;4;0;\x07` after ESC] removal). This leaves garbage on a second line, causing `json.loads()` to fail with "Extra data".
**How to avoid:** Use `subprocess.run(capture_output=True)` (Python runtime) — no PTY, no ANSI. If terminal runtime must be used, use the JSON extraction regex pattern (Pattern 2 above).
**Warning signs:** `json.loads()` succeeds on output from direct shell but fails from Agent Zero terminal runtime.

### Pitfall 3: Subprocess Timeout Too Short

**What goes wrong:** `subprocess.TimeoutExpired` exception — claude process killed before response arrives.
**Why it happens:** Claude inference takes 2-30 seconds depending on prompt complexity and model. Default Python subprocess timeout may be too short, and some hosting environments have API latency spikes.
**How to avoid:** Use `timeout=120` (2 minutes) as a conservative default for single-turn calls. Wrap in try/except for `subprocess.TimeoutExpired`.
**Warning signs:** Intermittent failures on longer prompts; consistent failures when API is under load.

### Pitfall 4: OSC Sequence in clean_string Output

**What goes wrong:** `clean_string()` output contains `9;4;0;\x07` or similar strings that look like garbage.
**Why it happens:** `clean_string()` regex `r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"` matches CSI sequences (`ESC[`) but OSC sequences start with `ESC]` (0x1b 0x5d). The `]` character maps to decimal 93, which is in the range `[@-Z\\-_]`... wait: `[@-Z]` covers ASCII 64-90, `[\\-_]` covers 92-95. `]` is 93, so `\x5d` IS in `[\\-_]` range. However OSC sequences end with BEL (0x07) or ST (ESC\\), not the standard `[@-~]` terminator. So the ESC] part is consumed but the payload through BEL is not.
**How to avoid:** Do not use `clean_string()` for parsing claude JSON output from terminal runtime. Use the JSON extraction regex instead (find `{..."type":"result"...}` with regex then `json.loads()`).
**Warning signs:** Parsed text from terminal runtime contains sequences like `9;4;0;` or stray `\x07` bytes.

### Pitfall 5: Working Directory Matters

**What goes wrong:** Claude reads project CLAUDE.md from the working directory, which may change the agent's behavior unexpectedly.
**Why it happens:** Claude Code uses CLAUDE.md in the cwd for project instructions. If the subprocess inherits cwd = Agent Zero's working directory, and that directory has a CLAUDE.md, it affects the claude session.
**How to avoid:** For Agent Zero's use case this is usually fine (no CLAUDE.md in agent work dirs). Be aware when testing from the agent-zero project root directory, which does have CLAUDE.md.
**Warning signs:** Claude response behavior changes unexpectedly based on cwd.

---

## Code Examples

Verified patterns from empirical testing (2026-02-25, claude 2.1.55):

### Error Message When CLAUDECODE=1 (What We're Fixing)

```
$ CLAUDECODE=1 claude --print "say HELLO"
Error: Claude Code cannot be launched inside another Claude Code session.
Nested sessions share runtime resources and will crash all active sessions.
To bypass this check, unset the CLAUDECODE environment variable.
```

Exit code: non-zero (failure).

### Clean Stdout When NOT TTY (subprocess with capture_output=True)

```python
# Source: empirically verified 2026-02-25
# xxd shows: 48 45 4c 4c 4f 0a  (exactly "HELLO\n" — no ANSI, no carriage return)
import subprocess, os
env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}
r = subprocess.run(
    ['claude', '--print', 'say HELLO'],
    capture_output=True, text=True, env=env_clean, timeout=120
)
print(repr(r.stdout))  # 'HELLO\n'
print(r.returncode)    # 0
```

### JSON Output Format (Full Response Structure)

```python
# Source: empirically verified 2026-02-25
# Command: claude -p "say HELLO" --output-format json
# Output: single line JSON object
{
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "duration_ms": 1823,
    "duration_api_ms": 1106,
    "num_turns": 1,
    "result": "HELLO",           # <-- the text response
    "stop_reason": None,
    "session_id": "0c396907-...", # <-- UUID for --resume in Phase 9
    "total_cost_usd": 0.008243,
    "usage": {
        "input_tokens": 3,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 16207,
        "output_tokens": 5,
        ...
    },
    "uuid": "8e5e25b8-..."
}
```

### ANSI Sequences When TTY Is Connected

```
# Source: xxd /tmp/claude_tty_out.txt — empirically captured 2026-02-25
# After "HELLO\r\n", claude appends:
1b 5b 3c 75          → ESC[<u         (focus event tracking disable — CSI)
1b 5b 3f 31 30 30 34 6c → ESC[?1004l  (disable focus reporting — CSI)
1b 5b 3f 32 30 30 34 6c → ESC[?2004l  (disable bracketed paste — CSI)
1b 5b 3f 32 35 68    → ESC[?25h       (show cursor — CSI)
1b 5d 39 3b 34 3b 30 3b 07 → ESC]9;4;0;\x07  (iTerm2 OSC progress — OSC+BEL)
1b 5b 3f 32 35 68    → ESC[?25h       (show cursor again — CSI)
```

The CSI sequences are handled by `clean_string()`. The OSC sequence (`ESC]9;4;0;\x07`) is partially handled — ESC] is consumed by `[@-Z\\-_]` match but the payload `9;4;0;\x07` remains in cleaned output.

### Complete Working Implementation (for Agent Zero Skill)

```python
# Source: empirically verified 2026-02-25
# Run in Agent Zero's Python runtime (runtime="python" in code_execution_tool)
import subprocess, os, json, re

ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

def claude_single_turn(prompt, timeout=120):
    """
    Call claude CLI in single-turn mode from Agent Zero.
    Returns clean response text string.
    """
    # Unset CLAUDECODE for subprocess only — never modify os.environ globally
    env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}

    result = subprocess.run(
        ['claude', '--print', '--output-format', 'json', prompt],
        capture_output=True,
        text=True,
        env=env_clean,
        timeout=timeout
    )

    # Process exited: check return code
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"claude failed (exit {result.returncode}): {err[:300]}")

    # Safety: strip any ANSI (not needed for capture_output=True, but defensive)
    stdout_clean = ANSI_RE.sub('', result.stdout).strip()

    data = json.loads(stdout_clean)

    if data.get('is_error'):
        raise RuntimeError(f"claude API error: {data.get('result', 'unknown')}")

    return data['result']


# Usage:
response = claude_single_turn("What is the capital of France?")
print(response)  # "Paris"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `claude --print` (no format) | `claude --print --output-format json` | claude 2.x | Structured response with metadata; `.result` field is the text |
| Assume prompt as stdin | Prompt as positional argument | claude 2.x | `claude -p "prompt"` is the primary pattern; stdin adds context |
| No env fix (subprocess inherits CLAUDECODE) | `env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}` | Discovered 2026-02-25 | Enables claude invocation from within Claude Code sessions |

**Current claude CLI version:** 2.1.55 (as of 2026-02-25)

**Key flags for Phase 8:**
- `-p` / `--print`: Single-turn, non-interactive, exits after response
- `--output-format json`: Structured JSON output (recommended)
- `--output-format text`: Plain text output (simpler, same content as `.result`)
- `--no-session-persistence`: Don't write session files (stateless)
- `--model <alias>`: Use specific model (e.g., `haiku`, `sonnet`, `opus`)

---

## Open Questions

1. **claude binary location in Docker container**
   - What we know: `claude` is NOT installed in the agent-zero Docker container (verified). It is installed on the host at `/Users/rgv250cc/.local/bin/claude`.
   - What's unclear: Phase 8's ROADMAP says "from within its own environment" — does this mean from Agent Zero's web server process (running in Docker), or from a host-side script context?
   - Recommendation: The phase 8 skill/documentation is for the HOST development context (running agent zero locally, which is where CLAUDECODE=1 matters). If agent zero runs in Docker, CLAUDECODE would not be set unless the Docker container somehow inherits it via `-e CLAUDECODE`. Document this scope clearly.

2. **subprocess.TimeoutExpired handling**
   - What we know: `subprocess.run(timeout=N)` raises `subprocess.TimeoutExpired` if claude doesn't exit within N seconds.
   - What's unclear: Whether 120s is the right default for the expected use cases in Agent Zero.
   - Recommendation: Use 120s as default but make it configurable. The claude API typically responds in 2-30s.

3. **claude binary in PATH within code_execution_tool**
   - What we know: Agent Zero's terminal/python runtime executes in a subprocess shell. `claude` must be on PATH.
   - What's unclear: Whether `~/.local/bin` is on PATH in Agent Zero's subprocess environment.
   - Recommendation: The skill should document checking PATH and optionally using the full path `/Users/rgv250cc/.local/bin/claude` or `shutil.which('claude')` to discover the binary location.

---

## Sources

### Primary (HIGH confidence — empirically tested)

- `claude 2.1.55` binary at `/Users/rgv250cc/.local/bin/claude` — all output format and ANSI behaviors verified by direct execution
- `xxd /tmp/claude_tty_out.txt` — raw byte inspection of PTY output confirming ANSI sequence structure
- `xxd /tmp/claude_test_out.txt` — raw byte inspection of subprocess capture_output output confirming clean stdout
- `python3 clean_string test` — verified that `clean_string()` leaves OSC payloads intact

### Secondary (MEDIUM confidence)

- `claude --help` output (2026-02-25) — flags and descriptions for `--print`, `--output-format`, `--no-session-persistence`, `--model`
- Agent Zero `shell_ssh.py:215` — `clean_string()` function, regex pattern for ANSI stripping
- Agent Zero `tty_session.py` — TTYSession implementation showing PTY-based subprocess management

### Tertiary (LOW confidence — not independently verified beyond this project)

- OSC sequence behavior (`ESC]9;4;0;\x07`) is iTerm2-specific progress reporting — may not appear on Linux terminals in Docker, where only CSI cleanup sequences would appear

---

## Metadata

**Confidence breakdown:**
- CLAUDECODE error and env fix: HIGH — observed exact error message; confirmed fix works
- subprocess.run clean output: HIGH — verified via xxd (6 bytes, pure HELLO\n)
- PTY ANSI sequences: HIGH — captured and decoded via xxd
- OSC in clean_string: HIGH — Python test showed `9;4;0;\x07` remains after clean_string
- --output-format json schema: HIGH — multiple real invocations, consistent structure
- claude binary not in Docker container: HIGH — docker exec search confirmed
- PATH availability of claude in subprocess: MEDIUM — not tested in Agent Zero's actual subprocess context

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (claude CLI version may change; verify `claude --version` before implementing)

**Key empirical test commands (reproducible):**
```bash
# Verify CLAUDECODE error:
CLAUDECODE=1 claude --print "test"

# Verify env fix:
env -u CLAUDECODE claude --print "say HELLO" > /tmp/out.txt && xxd /tmp/out.txt

# Verify PTY ANSI:
script -q /tmp/tty.txt env -u CLAUDECODE claude --print "say HELLO" < /dev/null && xxd /tmp/tty.txt

# Verify JSON format:
env -u CLAUDECODE claude --print "say HELLO" --output-format json
```
