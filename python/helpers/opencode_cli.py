"""
opencode_cli.py - OpenCode TUI session wrapper via shared tmux session.

Implements OpenCodeSession: a stateful wrapper exposing .start() / .send(prompt) / .exit()
interface, mirroring ClaudeSession in python/helpers/claude_cli.py.

All empirical patterns sourced from Phase 13 research:
  - 13-01-OBSERVATION.md: startup timing, ready-state pattern, busy/idle states
  - 13-02-SUMMARY.md: CLI-04 exit via Ctrl+P palette (NOT /exit — triggers agent picker in v1.2.14)

Empirically verified: 2026-02-25, OpenCode v1.2.14, Docker aarch64.

Usage:
    import sys
    sys.path.insert(0, '/a0')
    from python.helpers.opencode_cli import OpenCodeSession

    session = OpenCodeSession()
    session.start()
    r1 = session.send("What does /a0/python/tools/tmux_tool.py do?")
    r2 = session.send("How many actions does TmuxTool implement?")
    session.exit()
"""
import subprocess
import re
import time

# ---------------------------------------------------------------------------
# Constants — single source of truth is python/tools/tmux_tool.py.
# Copied here because importing tmux_tool pulls in agent.py → nest_asyncio
# which is not available in standalone Python contexts (skill code, validation scripts).
# If tmux_tool.py changes these values, update here too.
# ---------------------------------------------------------------------------

# Pre-established project ANSI strip regex (STATE.md Phase 11 decision)
# OSC branch (\][^\x07]*\x07) MUST come before 2-char branch ([@-Z\\-_]) because
# ] (0x5D) falls in the \-_ range — branch ordering matters.
# Covers: OSC title sequences, 2-char ESC sequences, CSI color/cursor sequences.
ANSI_RE = re.compile(r'\x1b(?:\][^\x07]*\x07|[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# OpenCode TUI ready-state prompt pattern — empirically verified Phase 13 (13-01-OBSERVATION.md)
# Matches two ready states:
#   1. Initial startup: status bar shows "/a0  ...  1.2.14" at bottom-right
#   2. Post-response: hints bar shows "ctrl+t variants  tab agents" WITHOUT "esc interrupt" (busy indicator)
# Copied from python/tools/tmux_tool.py — single source of truth is there.
OPENCODE_PROMPT_PATTERN = r'^(?:\s*/a0\s+\d+\.\d+\.\d+\s*$|(?!.*esc interrupt).*ctrl\+t variants\s+tab agents)'

# Timeout for OpenCode TUI startup (seconds) — observed startup ~1.5s; 10x safety buffer
# Copied from python/tools/tmux_tool.py — single source of truth is there.
OPENCODE_START_TIMEOUT = 15  # seconds

_TMUX_SESSION = "shared"
_OPENCODE_RESPONSE_TIMEOUT = 120  # seconds — AI response budget


class OpenCodeSession:
    """
    Stateful wrapper around OpenCode TUI lifecycle via shared tmux session.

    Mirrors ClaudeSession from python/helpers/claude_cli.py. Hides tmux plumbing:
    OPENCODE_PROMPT_PATTERN, exit sequences, ANSI stripping, wait_ready polling loops.
    Skill code orchestrates OpenCode without any direct tmux knowledge.

    All empirical patterns from Phase 13 (13-01-OBSERVATION.md, 13-02-SUMMARY.md):
    - Ready-state detection: two-branch pattern (startup status bar OR post-response hints bar)
    - Exit sequence: Ctrl+P palette → 'exit' + Enter → wait for shell prompt
      DO NOT use /exit — the '/' character opens the AGENT PICKER in OpenCode v1.2.14,
      causing 'exit' text to go into the agent search box instead of executing the command.
    - First prompt timing: 0.5s sleep in start() before _wait_ready completes lets the
      TUI input widget fully activate (Phase 13 pitfall 3 mitigation).

    Lifecycle:
        session = OpenCodeSession()
        session.start()                      # starts TUI, waits for ready state
        r1 = session.send("prompt text")     # returns full ANSI-stripped pane content
        r2 = session.send("follow-up")       # multi-turn: TUI context persists
        session.exit()                        # Ctrl+P palette exit, waits for shell prompt

    send() returns the full ANSI-stripped pane content (TUI chrome included).
    The assistant response text is visible in the returned content.
    Future enhancement: differential extraction (before/after capture diff) can isolate
    only the new response text — not required for v1 (Phase 14 scope).
    """

    def __init__(self, response_timeout: int = _OPENCODE_RESPONSE_TIMEOUT):
        """
        Args:
            response_timeout: Max seconds to wait for OpenCode AI response. Default 120s.
                              Adjust upward for slow models or large file analysis tasks.
        """
        self._running = False
        self._response_timeout = response_timeout

    def start(self) -> None:
        """
        Start OpenCode TUI in the shared tmux session and wait for ready state.

        Sends 'export PATH=/root/.opencode/bin:$PATH && opencode /a0' + Enter.
        The PATH export is defensive — it's a no-op if already set in the shell environment.

        Waits for OPENCODE_PROMPT_PATTERN to match (initial startup state) before returning.
        Sets self._running = True on success.

        Raises:
            RuntimeError: If OpenCode does not reach ready state within OPENCODE_START_TIMEOUT (15s).
        """
        subprocess.run(
            ["tmux", "send-keys", "-t", _TMUX_SESSION,
             "export PATH=/root/.opencode/bin:$PATH && opencode /a0", "Enter"],
            capture_output=True,
            text=True,
        )
        # 0.5s sleep after sending start command before _wait_ready.
        # Phase 13 pitfall 3: first prompt timing issue — TUI input widget needs
        # a brief moment to fully activate after the process starts.
        time.sleep(0.5)
        self._wait_ready(timeout=OPENCODE_START_TIMEOUT, prompt_pattern=OPENCODE_PROMPT_PATTERN)
        self._running = True

    def send(self, prompt: str) -> str:
        """
        Send one prompt to the running OpenCode TUI. Returns cleaned pane content.

        Types prompt + Enter into the TUI, waits for OPENCODE_PROMPT_PATTERN to match
        (indicating the response is complete), then reads and returns the full pane content.

        Multi-turn: OpenCode TUI process stays running between send() calls, so
        conversation context is preserved automatically.

        Args:
            prompt: The user prompt string to type into the TUI.

        Returns:
            str: ANSI-stripped pane content (300 lines). Includes TUI chrome alongside
                 the assistant response — response text is visible in the content.

        Raises:
            RuntimeError: If called before start() (running guard).
            RuntimeError: If response not received within response_timeout seconds.
                         Sends C-c to interrupt the ongoing request before raising.
        """
        if not self._running:
            raise RuntimeError("OpenCodeSession not started — call start() first")

        subprocess.run(
            ["tmux", "send-keys", "-t", _TMUX_SESSION, prompt, "Enter"],
            capture_output=True,
            text=True,
        )
        self._wait_ready(timeout=self._response_timeout, prompt_pattern=OPENCODE_PROMPT_PATTERN)

        # Read full pane after response — 300 lines captures full response history
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", _TMUX_SESSION, "-p", "-S", "-300"],
            capture_output=True,
            text=True,
        )
        return ANSI_RE.sub("", result.stdout).rstrip()

    def exit(self) -> None:
        """
        Exit OpenCode cleanly via Ctrl+P palette sequence. Idempotent.

        3-step exit sequence (empirically verified Phase 13, 13-02-SUMMARY.md):
          Step 1: Send C-p key (opens OpenCode commands palette)
          Step 2: Wait 0.2s for palette to open, then send 'exit' + Enter
                  ('exit' filters the palette list to 'Exit the app' and executes it)
          Step 3: Wait for default shell prompt pattern to confirm shell returned

        CRITICAL: Do NOT send '/exit' directly. In OpenCode v1.2.14, the '/' character
        immediately opens the AGENT PICKER (showing 'build native', 'plan native' agents).
        'exit' then goes into the agent search box — TUI stays open, shell never returns.

        Sets self._running = False on success.
        No-op (returns immediately) if session is not running.
        """
        if not self._running:
            return

        # Step 1: Open commands palette
        subprocess.run(
            ["tmux", "send-keys", "-t", _TMUX_SESSION, "C-p"],
            capture_output=True,
            text=True,
        )
        # Step 2: Wait for palette to open, then filter + execute
        time.sleep(0.2)
        subprocess.run(
            ["tmux", "send-keys", "-t", _TMUX_SESSION, "exit", "Enter"],
            capture_output=True,
            text=True,
        )
        # Step 3: Wait for shell prompt to confirm TUI exited
        self._wait_ready(timeout=15, prompt_pattern=r'[$#>%]\s*$')
        self._running = False

    def _wait_ready(self, timeout: float, prompt_pattern: str) -> str:
        """
        Synchronous translation of TmuxTool._wait_ready (python/tools/tmux_tool.py).

        Polls tmux pane until prompt_pattern matches the last non-blank ANSI-stripped line,
        or until pane content stabilizes (stability fallback). asyncio.sleep replaced with
        time.sleep — this module is synchronous (skill code runs sync, not in async loop).

        Two detection strategies (same as TmuxTool._wait_ready):
          1. Prompt pattern: last non-blank line matches prompt_re (primary signal)
          2. Stability: consecutive captures are identical — pane stopped changing (secondary)

        Args:
            timeout: Max seconds to wait before raising RuntimeError.
            prompt_pattern: Regex string to match against last non-blank pane line.

        Returns:
            str: ANSI-stripped pane content when ready state detected.

        Raises:
            RuntimeError: On timeout — sends C-c to interrupt ongoing request, then raises.
                         Message includes timeout value and Ollama connectivity hint.
        """
        prompt_re = re.compile(prompt_pattern)
        deadline = time.time() + timeout
        prev_content = None

        # Initial 0.3s delay before first capture (Phase 12 decision):
        # Prevents stale-prompt false positive at the send/wait boundary.
        time.sleep(0.3)

        while time.time() < deadline:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", _TMUX_SESSION, "-p", "-S", "-50"],
                capture_output=True,
                text=True,
            )
            clean = ANSI_RE.sub("", result.stdout).rstrip()
            lines = [l for l in clean.splitlines() if l.strip()]

            # Strategy 1: prompt pattern on last non-blank line (primary signal)
            if lines and prompt_re.search(lines[-1]):
                return clean

            # Strategy 2: content stability — pane stopped changing (secondary signal)
            if prev_content is not None and clean == prev_content:
                return clean

            prev_content = clean
            time.sleep(0.5)

        # Timeout — interrupt ongoing request with C-c before raising
        subprocess.run(
            ["tmux", "send-keys", "-t", _TMUX_SESSION, "C-c"],
            capture_output=True,
            text=True,
        )
        raise RuntimeError(
            f"OpenCode wait_ready timed out after {timeout}s. "
            "Check: (1) Ollama is running at host:11434, "
            "(2) OpenCode TUI is active in shared tmux session, "
            "(3) model is loaded and not being pulled."
        )

    @property
    def running(self) -> bool:
        """True if session has been started via start() and not yet exited via exit()."""
        return self._running
