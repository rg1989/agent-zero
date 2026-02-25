"""
claude_cli.py - Claude CLI single-turn invocation helper.

Implements Agent Zero's validated pattern for calling the claude CLI
from within a Claude Code session (CLAUDECODE env fix) or any Python
subprocess context.

Empirically verified: 2026-02-25, claude 2.1.55
"""
import subprocess
import os
import json
import re

# ANSI escape sequence pattern - safety net for capture_output=True path.
# When subprocess runs with capture_output=True (not a TTY), claude outputs
# zero ANSI. This strip is defensive only.
# Pattern covers: ESC[@-Z\-_] (2-char) and ESC[...final (CSI sequences)
ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

CLAUDE_DEFAULT_TIMEOUT = 120  # seconds; claude API typically responds in 2-30s


def claude_single_turn(prompt: str, model: str = None, timeout: int = CLAUDE_DEFAULT_TIMEOUT) -> str:
    """
    Call claude CLI in single-turn (--print) mode. Returns clean response text.

    Uses --output-format json to get structured response; extracts .result field.
    CLAUDECODE is removed from subprocess env only -- os.environ is never modified.

    Args:
        prompt: The user prompt string.
        model: Optional model override (e.g., 'haiku', 'sonnet', 'opus').
                If None, uses claude's default (claude-sonnet-4-5).
        timeout: Max seconds to wait for response. Default 120s.

    Returns:
        str: Clean response text, no ANSI sequences, no JSON wrapper.

    Raises:
        RuntimeError: If claude exits non-zero, returns is_error=True,
                      binary not found, or subprocess.TimeoutExpired.
        json.JSONDecodeError: If --output-format json response is malformed.
    """
    # Remove CLAUDECODE from subprocess env only -- NEVER del os.environ['CLAUDECODE']
    # or os.unsetenv(). Those affect the whole process. Dict comprehension is scoped
    # to this call only.
    env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}

    cmd = ['claude', '--print', '--output-format', 'json']
    if model:
        cmd += ['--model', model]
    cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env_clean,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"claude single-turn timed out after {timeout}s. "
            "Increase timeout or check API connectivity."
        )
    except FileNotFoundError:
        raise RuntimeError(
            "claude binary not found in PATH. "
            "Verify: shutil.which('claude') or check ~/.local/bin is on PATH."
        )

    if result.returncode != 0:
        err = (result.stderr.strip() or result.stdout.strip())[:400]
        raise RuntimeError(f"claude exited {result.returncode}: {err}")

    # Safety strip (no-op when capture_output=True, but handles edge cases)
    stdout_clean = ANSI_RE.sub('', result.stdout).strip()

    data = json.loads(stdout_clean)

    if data.get('is_error'):
        raise RuntimeError(f"claude API error: {data.get('result', 'unknown error')}")

    return data['result']  # Clean response text


def claude_single_turn_text(prompt: str, model: str = None, timeout: int = CLAUDE_DEFAULT_TIMEOUT) -> str:
    """
    Call claude CLI in single-turn mode, returning plain text output.

    Uses --output-format text (no JSON wrapper). Simpler than claude_single_turn()
    when metadata (cost, session_id, usage) is not needed.

    Args:
        prompt: The user prompt string.
        model: Optional model override.
        timeout: Max seconds to wait. Default 120s.

    Returns:
        str: Clean response text.

    Raises:
        RuntimeError: If claude exits non-zero, binary not found, or timeout.
    """
    env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}

    cmd = ['claude', '--print', '--output-format', 'text']
    if model:
        cmd += ['--model', model]
    cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env_clean,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"claude single-turn-text timed out after {timeout}s")
    except FileNotFoundError:
        raise RuntimeError("claude binary not found in PATH")

    if result.returncode != 0:
        err = (result.stderr.strip() or result.stdout.strip())[:400]
        raise RuntimeError(f"claude exited {result.returncode}: {err}")

    return ANSI_RE.sub('', result.stdout).strip()
