import asyncio
import time

from python.helpers.tool import Tool, Response
from python.helpers.app_manager import AppManager

# CDP readiness timeout for the shared browser (seconds)
_SHARED_BROWSER_CDP_PORT = 9222
_SHARED_BROWSER_CDP_WAIT = 20

# ttyd readiness timeout for the shared terminal (seconds)
_SHARED_TERMINAL_HTTP_WAIT = 15


async def _wait_for_cdp(timeout: int = _SHARED_BROWSER_CDP_WAIT) -> bool:
    """Wait until the shared browser CDP port accepts connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", _SHARED_BROWSER_CDP_PORT),
                timeout=2,
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except Exception:
            await asyncio.sleep(1)
    return False


async def _wait_for_port(host: str, port: int, timeout: int) -> bool:
    """Wait until a TCP port accepts connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=2,
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except Exception:
            await asyncio.sleep(1)
    return False


class OpenAppTool(Tool):
    """
    Opens or closes app tabs in the integrated right-side drawer.

    action=open      → add app to tabs (start it if needed), make it active, open drawer
    action=close     → hide the drawer (tabs remain, re-opening shows them again)
    action=close_tab → remove a specific tab (closes drawer if no tabs remain)
    """

    async def execute(self, **kwargs):
        action = self.args.get("action", "open")
        app_name = (self.args.get("app") or "").strip()

        mgr = AppManager.get_instance()
        state = mgr.get_drawer_state()
        apps: list[str] = list(state.get("apps") or [])

        if action == "open":
            if not app_name:
                return Response(
                    message="'app' argument is required when action is 'open'.",
                    break_loop=False,
                )

            app_info = mgr.get_app(app_name)
            if app_info is None:
                available = [a["name"] for a in mgr.list_apps()]
                return Response(
                    message=f"App '{app_name}' not found. Available: {', '.join(available) or 'none'}",
                    break_loop=False,
                )

            if app_info.get("status") != "running":
                try:
                    mgr.start_app(app_name)
                except Exception as e:
                    return Response(
                        message=f"Failed to start '{app_name}': {e}",
                        break_loop=False,
                    )

            if app_name not in apps:
                apps.append(app_name)

            mgr.set_drawer_state(open=True, apps=apps, active=app_name)

            # For the shared browser, wait for Chromium CDP to be ready so the
            # next browser_agent call doesn't race against a still-starting browser.
            if app_name == "shared-browser":
                cdp_ready = await _wait_for_cdp()
                status_note = (
                    " Chromium is ready (CDP available)."
                    if cdp_ready
                    else " Warning: Chromium CDP not yet available — browser may still be starting."
                )
                return Response(
                    message=f"Opened '{app_name}' in the side drawer.{status_note}",
                    break_loop=False,
                )

            # For the shared terminal, wait for ttyd's HTTP port to be ready.
            if app_name == "shared-terminal":
                term_port = app_info.get("port", 9004)
                ttyd_ready = await _wait_for_port(
                    "127.0.0.1", term_port, _SHARED_TERMINAL_HTTP_WAIT
                )
                status_note = (
                    " Terminal is ready."
                    if ttyd_ready
                    else " Warning: ttyd not yet available — terminal may still be starting."
                )
                return Response(
                    message=f"Opened '{app_name}' in the side drawer.{status_note}",
                    break_loop=False,
                )

            return Response(
                message=f"Opened '{app_name}' in the side drawer.",
                break_loop=False,
            )

        if action == "close":
            mgr.set_drawer_state(open=False, apps=apps, active=state.get("active"))
            return Response(message="Side drawer hidden.", break_loop=False)

        if action == "close_tab":
            if not app_name:
                return Response(
                    message="'app' argument required to close a tab.",
                    break_loop=False,
                )
            if app_name in apps:
                apps.remove(app_name)
            current_active = state.get("active")
            new_active = current_active if current_active != app_name else (apps[-1] if apps else None)
            mgr.set_drawer_state(open=bool(apps), apps=apps, active=new_active)
            return Response(message=f"Closed tab '{app_name}'.", break_loop=False)

        return Response(
            message=f"Unknown action '{action}'. Use 'open', 'close', or 'close_tab'.",
            break_loop=False,
        )
