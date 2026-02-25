import subprocess
import re
from python.helpers.tool import Tool, Response

_TMUX_SESSION = "shared"

# Pre-established project ANSI strip regex (STATE.md, claude_cli.py)
# Covers: 2-char ESC sequences, CSI color/cursor, OSC title sequences
ANSI_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07)')


class TmuxTool(Tool):
    """
    Primitive interface to the shared tmux session.

    Provides three actions:
      - send:  Type literal text + Enter into the pane (TERM-01)
      - keys:  Send tmux key names without Enter (TERM-02, TERM-03)
      - read:  Capture current pane content as clean plain text (TERM-04)

    Coexists with terminal_agent.py (sentinel pattern). This tool is sentinel-free.
    Sentinel-free: no injected echo sequences, no $? probing, no subshell. Only subprocess list-form calls.
    """

    async def execute(self, **kwargs):
        action = self.args.get("action", "").strip().lower()
        dispatch = {"send": self._send, "keys": self._keys, "read": self._read}
        handler = dispatch.get(action)
        if not handler:
            return Response(
                message=f"Unknown action '{action}'. Valid actions: send, keys, read.",
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
