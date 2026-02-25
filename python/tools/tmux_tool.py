import asyncio
import subprocess
import time
import re
from python.helpers.tool import Tool, Response

_TMUX_SESSION = "shared"

# Pre-established project ANSI strip regex (STATE.md, claude_cli.py)
# Covers: 2-char ESC sequences, CSI color/cursor, OSC title sequences
ANSI_RE = re.compile(r'\x1b(?:\][^\x07]*\x07|[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# OpenCode TUI ready-state prompt pattern — empirically verified in Phase 13 (13-01-OBSERVATION.md)
# Use this with: tmux_tool(action="wait_ready", prompt_pattern=OPENCODE_PROMPT_PATTERN, timeout=120)
# Matches two states:
#   1. Initial startup: status bar shows "/a0  ...  1.2.14" at bottom-right
#   2. Post-response: hints bar shows "ctrl+t variants  tab agents" WITHOUT "esc interrupt" (busy indicator)
OPENCODE_PROMPT_PATTERN = r'^(?:\s*/a0\s+\d+\.\d+\.\d+\s*$|(?!.*esc interrupt).*ctrl\+t variants\s+tab agents)'

# Timeout for OpenCode TUI startup (seconds) — observed startup ~1.5s; 10x safety buffer
OPENCODE_START_TIMEOUT = 15  # seconds


class TmuxTool(Tool):
    """
    Primitive interface to the shared tmux session.

    Provides four actions:
      - send:       Type literal text + Enter into the pane (TERM-01)
      - keys:       Send tmux key names without Enter (TERM-02, TERM-03)
      - read:       Capture current pane content as clean plain text (TERM-04)
      - wait_ready: Poll until prompt detected or timeout expires (TERM-05)

    Coexists with terminal_agent.py (sentinel pattern). This tool is sentinel-free.
    Sentinel-free: no injected echo sequences, no $? probing, no subshell. Only subprocess list-form calls.
    """

    async def execute(self, **kwargs):
        action = self.args.get("action", "").strip().lower()
        dispatch = {
            "send": self._send,
            "keys": self._keys,
            "read": self._read,
            "wait_ready": self._wait_ready,
        }
        handler = dispatch.get(action)
        if not handler:
            return Response(
                message=f"Unknown action '{action}'. Valid actions: send, keys, read, wait_ready.",
                break_loop=False,
            )
        return await handler()

    async def _send(self):
        """TERM-01: Send literal text followed by Enter to the tmux pane."""
        text = self.args.get("text", "")
        if isinstance(text, str):
            text = text.strip()
        if not text:
            return Response(
                message="Missing or empty 'text' argument for action 'send'.",
                break_loop=False,
            )
        pane = self.args.get("pane", _TMUX_SESSION)

        # text is ONE list element (prevents tmux interpreting words like "Tab" as key names)
        # "Enter" is the SEPARATE final argument — this is the key press
        result = subprocess.run(
            ["tmux", "send-keys", "-t", pane, text, "Enter"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return Response(
                message=f"tmux send-keys failed: {result.stderr.strip()} — Is shared-terminal running?",
                break_loop=False,
            )
        return Response(message=f"Sent: {text!r} + Enter", break_loop=False)

    async def _keys(self):
        """TERM-02/TERM-03: Send tmux key names without appending Enter."""
        raw_keys = self.args.get("keys", "")
        if isinstance(raw_keys, list):
            key_args = raw_keys
        else:
            key_args = raw_keys.split() if isinstance(raw_keys, str) else []

        if not key_args:
            return Response(
                message="Missing or empty 'keys' argument for action 'keys'.",
                break_loop=False,
            )
        pane = self.args.get("pane", _TMUX_SESSION)

        # Each element of key_args IS a tmux key name (intentional — unlike _send)
        result = subprocess.run(
            ["tmux", "send-keys", "-t", pane] + key_args,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return Response(
                message=f"tmux send-keys failed: {result.stderr.strip()}",
                break_loop=False,
            )
        return Response(message=f"Keys sent: {key_args}", break_loop=False)

    async def _read(self):
        """TERM-04: Capture current pane content; strip ANSI sequences before returning."""
        pane = self.args.get("pane", _TMUX_SESSION)
        try:
            lines = int(self.args.get("lines", 100))
        except (ValueError, TypeError):
            lines = 100

        # CRITICAL: NO -e flag — omitting it prevents tmux from including raw escape sequences
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", pane, "-p", "-S", f"-{lines}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return Response(
                message=f"tmux capture-pane failed: {result.stderr.strip()} — Is shared-terminal running?",
                break_loop=False,
            )

        clean = ANSI_RE.sub("", result.stdout).rstrip()
        return Response(message=clean or "(pane is empty)", break_loop=False)

    async def _wait_ready(self):
        """
        TERM-05: Poll pane until prompt pattern matches or idle timeout expires.

        Two detection strategies:
        1. Prompt pattern: last non-blank ANSI-stripped line matches a shell prompt regex
        2. Stability fallback: consecutive captures are identical (pane stopped changing)

        Falls back to timeout return — never hangs indefinitely.
        """
        pane = self.args.get("pane", _TMUX_SESSION)
        try:
            timeout = float(self.args.get("timeout", 10.0))
        except (ValueError, TypeError):
            timeout = 10.0
        pattern_str = self.args.get("prompt_pattern", r"[$#>%]\s*$")
        try:
            prompt_re = re.compile(pattern_str)
        except re.error as e:
            return Response(
                message=f"Invalid prompt_pattern: {e}",
                break_loop=False,
            )

        deadline = time.time() + timeout
        prev_content = None

        # Brief initial delay to let the command start executing before first check
        await asyncio.sleep(0.3)

        while time.time() < deadline:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", pane, "-p", "-S", "-50"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return Response(
                    message=f"capture-pane failed: {result.stderr.strip()} — Is shared-terminal running?",
                    break_loop=False,
                )

            clean = ANSI_RE.sub("", result.stdout).rstrip()

            # Strategy 1: prompt pattern on last non-blank line (primary signal)
            lines = [l for l in clean.splitlines() if l.strip()]
            if lines and prompt_re.search(lines[-1]):
                return Response(
                    message=f"ready (prompt matched)\n{clean}",
                    break_loop=False,
                )

            # Strategy 2: content stability — pane stopped changing (secondary signal)
            if prev_content is not None and clean == prev_content:
                return Response(
                    message=f"ready (stable)\n{clean}",
                    break_loop=False,
                )

            prev_content = clean
            await asyncio.sleep(0.5)

        # Timeout fallback
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", pane, "-p", "-S", "-50"],
            capture_output=True, text=True,
        )
        content = ANSI_RE.sub("", result.stdout).rstrip() if result.returncode == 0 else "(capture failed)"
        return Response(
            message=f"wait_ready timed out after {timeout}s\n{content}",
            break_loop=False,
        )
