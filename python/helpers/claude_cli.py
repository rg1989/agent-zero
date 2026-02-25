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


# ---------------------------------------------------------------------------
# Multi-turn session support (Phase 9)
# ---------------------------------------------------------------------------
# Extends single-turn helpers above with --resume UUID support.
# Implementation: same subprocess.run + capture_output=True pattern as Phase 8.
# New flag: --resume session_id (appended to cmd when session_id is not None).
# Completion signal: process returncode (unambiguous; no idle-timeout needed).
# ---------------------------------------------------------------------------


def claude_turn(
    prompt: str,
    session_id: str = None,
    model: str = None,
    timeout: int = CLAUDE_DEFAULT_TIMEOUT,
) -> tuple:
    """
    Execute one turn of a multi-turn claude conversation.

    Returns (response_text, session_id) where session_id must be passed to
    the next call as --resume to continue the same conversation.

    Args:
        prompt: The user prompt string.
        session_id: UUID string from a prior turn, or None to start a new session.
                    None starts a new session; the UUID from a prior turn continues
                    the conversation.
        model: Optional model override (e.g. 'haiku', 'sonnet', 'opus').
        timeout: Max seconds to wait for response. Default 120s.

    Returns:
        tuple[str, str]: (response_text, session_id)
            - response_text: Clean response text, no ANSI, no JSON wrapper.
            - session_id: UUID to pass as session_id on the next turn.

    Raises:
        RuntimeError: If claude exits non-zero (includes dead/expired session),
                      binary not found, or subprocess.TimeoutExpired.
                      Dead session indicator: returncode 1 +
                      'No conversation found with session ID:' in stderr;
                      the RuntimeError message will contain 'No conversation found'.
        json.JSONDecodeError: If --output-format json response is malformed.

    Dead session detection:
        When --resume is called with an invalid or expired session UUID, claude
        exits immediately with returncode 1 and stderr containing
        'No conversation found with session ID: <UUID>'. This raises RuntimeError
        with that message. Use claude_turn_with_recovery() to handle this
        automatically.
    """
    env_clean = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}

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
            env=env_clean,
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


class ClaudeSession:
    """
    Stateful wrapper around claude_turn() for multi-turn conversations.

    Tracks session_id automatically so callers never manage UUIDs directly.
    Each call to turn() sends one prompt and returns the response text, while
    internally storing the session_id for the next turn.

    Usage:
        session = ClaudeSession()
        r1 = session.turn("My name is Alice.")
        r2 = session.turn("What is my name?")  # claude remembers: 'Alice'
        session.reset()                          # start fresh conversation
        r3 = session.turn("Hello!")             # new session, no memory of Alice
    """

    def __init__(self, model: str = None, timeout: int = CLAUDE_DEFAULT_TIMEOUT):
        """
        Args:
            model: Optional model override (e.g. 'haiku', 'sonnet', 'opus').
            timeout: Max seconds per turn. Default 120s.
        """
        self._session_id = None
        self._model = model
        self._timeout = timeout

    def turn(self, prompt: str) -> str:
        """
        Send one prompt, return response text. Tracks session_id internally.

        Args:
            prompt: The user prompt string.

        Returns:
            str: Clean response text from claude.

        Raises:
            RuntimeError: Propagated from claude_turn() on error.
        """
        response, self._session_id = claude_turn(
            prompt,
            session_id=self._session_id,
            model=self._model,
            timeout=self._timeout,
        )
        return response

    def reset(self):
        """
        Clear the current session. The next turn() call will start a fresh
        conversation with no memory of prior turns.
        """
        self._session_id = None

    @property
    def session_id(self) -> str:
        """Read-only access to the current session UUID (None before first turn)."""
        return self._session_id


def claude_turn_with_recovery(
    prompt: str,
    session_id: str = None,
    timeout: int = CLAUDE_DEFAULT_TIMEOUT,
) -> tuple:
    """
    Wrap claude_turn() with automatic dead-session recovery.

    Attempts to resume session_id. If the session is dead or expired
    (returncode 1 + 'No conversation found' in error), restarts with a
    fresh session automatically.

    Args:
        prompt: The user prompt string.
        session_id: UUID from a prior turn, or None for a new session.
        timeout: Max seconds to wait. Default 120s.

    Returns:
        tuple[str, str, bool]: (response_text, new_session_id, was_recovered)
            - response_text: Clean response text from claude.
            - new_session_id: UUID to use for the next turn.
            - was_recovered: True if session was dead and a fresh session was
              started (conversation context is lost). False if existing session
              was continued normally.

    Notes:
        - was_recovered=True means the session was dead and a new one was started.
          Conversation context is lost; the caller may need to re-establish context.
        - was_recovered=False means the existing session continued normally.
        - Always uses --resume UUID (not --continue) to avoid cwd race conditions
          when multiple sessions are active in the same working directory.

    Raises:
        RuntimeError: For non-recoverable errors (timeout, binary not found,
                      API errors, etc.).
    """
    try:
        response, new_sid = claude_turn(prompt, session_id=session_id, timeout=timeout)
        return response, new_sid, False
    except RuntimeError as e:
        if session_id and 'No conversation found' in str(e):
            # Dead/expired session — start fresh (context is lost)
            response, new_sid = claude_turn(prompt, session_id=None, timeout=timeout)
            return response, new_sid, True
        raise
