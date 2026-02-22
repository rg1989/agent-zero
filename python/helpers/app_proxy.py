"""
App Proxy — ASGI middleware that intercepts requests for registered Agent Zero
web apps and proxies them to the app's inner port.

URL pattern: localhost:50000/{app_name}/... → localhost:{inner_port}/...

Requests whose first path segment doesn't match a running registered app fall
through to the wrapped ASGI app (Flask).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

# Reserved first-path-segments that belong to Agent Zero itself and must never
# be intercepted, even if someone registers an app with the same name.
_RESERVED = frozenset(
    {
        "",
        "mcp",
        "a2a",
        "login",
        "logout",
        "health",
        "dev-ping",
        "socket.io",
        "static",
        # common api handlers (non-exhaustive – the registry check is the real guard)
        "message",
        "poll",
        "settings_get",
        "settings_set",
        "csrf_token",
        "chat_create",
        "chat_load",
        "upload",
        "webapp",
    }
)


def _app_name_from_path(path: str) -> str | None:
    """Extract the first path segment, return None for reserved segments."""
    seg = path.strip("/").split("/")[0]
    if not seg or seg in _RESERVED:
        return None
    return seg


def _not_running_html(app_name: str, info: dict | None) -> bytes:
    status = info.get("status", "unknown") if info else "not registered"
    port = info.get("port", "?") if info else "?"
    desc = info.get("description", "") if info else ""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>App not running — {app_name}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background:#111; color:#eee;
            display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }}
    .box {{ background:#1e1e1e; border:1px solid #333; border-radius:12px;
             padding:2rem 3rem; max-width:480px; text-align:center; }}
    h1 {{ font-size:1.4rem; margin-bottom:.5rem; color:#f90; }}
    p {{ color:#aaa; font-size:.95rem; line-height:1.5; }}
    code {{ background:#2a2a2a; padding:.2em .5em; border-radius:4px; font-size:.9em; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>/{app_name}/ is not running</h1>
    <p>Status: <code>{status}</code> &nbsp;|&nbsp; Port: <code>{port}</code></p>
    {"<p>" + desc + "</p>" if desc else ""}
    <p>Ask Agent Zero to start it:<br>
       <code>"start the {app_name} app"</code></p>
  </div>
</body>
</html>""".encode()
    return html


class AppProxy:
    """
    ASGI middleware that routes /{app_name}/... to the app's inner port.
    Falls through to the wrapped app for everything else.
    """

    def __init__(self, app: "ASGIApp") -> None:
        self._app = app

    async def __call__(
        self, scope: "Scope", receive: "Receive", send: "Send"
    ) -> None:
        if scope["type"] not in ("http",):
            # WebSocket and lifespan pass straight through
            await self._app(scope, receive, send)
            return

        path: str = scope.get("path", "/")
        app_name = _app_name_from_path(path)

        if app_name:
            from python.helpers.app_manager import AppManager

            manager = AppManager.get_instance()
            info = manager.get_app(app_name)

            if info is not None:
                # App is registered — proxy if running, else show status page
                if info.get("status") == "running":
                    await self._proxy(scope, receive, send, app_name, info, path)
                else:
                    await self._send_html(
                        send, 503, _not_running_html(app_name, info)
                    )
                return

        # Not a registered app — fall through to Flask
        await self._app(scope, receive, send)

    # ──────────────────────────────────────────────
    # HTTP proxy
    # ──────────────────────────────────────────────

    async def _proxy(
        self,
        scope: "Scope",
        receive: "Receive",
        send: "Send",
        app_name: str,
        info: dict,
        path: str,
    ) -> None:
        try:
            import httpx
        except ImportError:
            body = b"httpx not installed - cannot proxy app requests"
            await self._send_html(send, 500, body, content_type=b"text/plain")
            return

        port = info["port"]

        # Strip the leading /{app_name} prefix, keep the rest (including /)
        prefix = f"/{app_name}"
        stripped = path[len(prefix):] or "/"
        if not stripped.startswith("/"):
            stripped = "/" + stripped

        query = scope.get("query_string", b"")
        target = f"http://127.0.0.1:{port}{stripped}"
        if query:
            target += "?" + (query.decode("utf-8", errors="replace"))

        method: str = scope.get("method", "GET")

        # Collect request headers, drop hop-by-hop and host
        _skip = {b"host", b"connection", b"keep-alive", b"transfer-encoding",
                 b"te", b"trailers", b"upgrade", b"proxy-authorization"}
        headers = {
            k: v
            for k, v in scope.get("headers", [])
            if k.lower() not in _skip
        }

        # Read request body
        body_chunks: list[bytes] = []
        more = True
        while more:
            msg = await receive()
            body_chunks.append(msg.get("body", b""))
            more = msg.get("more_body", False)
        body = b"".join(body_chunks)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.request(
                    method=method,
                    url=target,
                    headers=headers,
                    content=body,
                    follow_redirects=False,
                )
        except httpx.ConnectError:
            # App port not listening yet
            await self._send_html(send, 502, _not_running_html(app_name, info))
            return
        except Exception as exc:
            err = f"Proxy error for '{app_name}': {exc}".encode()
            await self._send_html(send, 502, err, content_type=b"text/plain")
            return

        # Forward response, stripping hop-by-hop headers
        resp_headers = [
            [k.lower().encode() if isinstance(k, str) else k.lower(),
             v.encode() if isinstance(v, str) else v]
            for k, v in resp.headers.items()
            if k.lower() not in {
                "connection", "keep-alive", "transfer-encoding",
                "te", "trailers", "upgrade"
            }
        ]

        await send(
            {
                "type": "http.response.start",
                "status": resp.status_code,
                "headers": resp_headers,
            }
        )
        await send({"type": "http.response.body", "body": resp.content})

    # ──────────────────────────────────────────────
    # Helper
    # ──────────────────────────────────────────────

    @staticmethod
    async def _send_html(
        send: "Send",
        status: int,
        body: bytes,
        content_type: bytes = b"text/html; charset=utf-8",
    ) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    [b"content-type", content_type],
                    [b"content-length", str(len(body)).encode()],
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
