import asyncio
import subprocess
import time
import uuid

from python.helpers.tool import Tool, Response

_TMUX_SESSION = "shared"


class TerminalAgent(Tool):
    """
    Run a shell command in the persistent shared tmux session.

    The same session is visible to the user in the shared-terminal drawer tab.
    Uses tmux send-keys to inject the command and tmux capture-pane to collect
    the output once a sentinel line appears (or after timeout).
    """

    async def execute(self, **kwargs):
        command = self.args.get("command", "").strip()
        try:
            timeout = int(self.args.get("timeout", 10))
        except (TypeError, ValueError):
            timeout = 10

        if not command:
            return Response(message="'command' argument is required.", break_loop=False)

        # Unique sentinel so we know exactly when the command finished
        marker = f"__A0_{uuid.uuid4().hex[:12]}"
        full_cmd = f'{command} ; echo "{marker}:$?"'

        send = subprocess.run(
            ["tmux", "send-keys", "-t", _TMUX_SESSION, full_cmd, "Enter"],
            capture_output=True,
            text=True,
        )
        if send.returncode != 0:
            return Response(
                message=(
                    f"Failed to send command to the shared terminal.\n"
                    f"Is the shared-terminal app running? Try opening it first with open_app.\n"
                    f"tmux error: {send.stderr.strip()}"
                ),
                break_loop=False,
            )

        # Poll until the sentinel appears in the pane or we time out
        deadline = time.time() + timeout
        output = ""
        exit_code = None

        while time.time() < deadline:
            await asyncio.sleep(0.5)
            cap = subprocess.run(
                ["tmux", "capture-pane", "-t", _TMUX_SESSION, "-p", "-S", "-500"],
                capture_output=True,
                text=True,
            )
            pane = cap.stdout
            if marker in pane:
                for line in pane.splitlines():
                    if line.startswith(marker + ":"):
                        exit_code = line.split(":", 1)[1].strip()
                        break
                idx = pane.find(marker)
                output = pane[:idx].rstrip()
                break
        else:
            # Timed out — return whatever is on screen
            cap = subprocess.run(
                ["tmux", "capture-pane", "-t", _TMUX_SESSION, "-p", "-S", "-500"],
                capture_output=True,
                text=True,
            )
            output = cap.stdout.rstrip()
            return Response(
                message=(
                    f"Command timed out after {timeout}s. "
                    f"Last terminal output:\n{output}"
                ),
                break_loop=False,
            )

        result = output
        if exit_code is not None:
            result += f"\n[exit code: {exit_code}]"

        return Response(message=result, break_loop=False)
