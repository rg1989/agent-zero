"""
App Proxy — ASGI middleware that intercepts requests for registered Agent Zero
web apps and proxies them to the app's inner port.

URL pattern: localhost:50000/{app_name}/... → localhost:{inner_port}/...

Requests whose first path segment doesn't match a running registered app fall
through to the wrapped ASGI app (Flask).
"""

from __future__ import annotations

import asyncio
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
        scope_type = scope["type"]

        if scope_type not in ("http", "websocket"):
            # lifespan and other types pass straight through
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
                    if scope_type == "websocket":
                        await self._proxy_ws(scope, receive, send, app_name, info, path)
                    else:
                        await self._proxy(scope, receive, send, app_name, info, path)
                else:
                    if scope_type == "websocket":
                        await receive()  # consume websocket.connect
                        await send({"type": "websocket.close", "code": 1008,
                                    "reason": f"App '{app_name}' is not running"})
                    else:
                        await self._send_html(
                            send, 503, _not_running_html(app_name, info)
                        )
                return

        # Not a registered app — fall through to Flask / Socket.IO
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

        # Forward response, stripping hop-by-hop headers.
        # Also strip content-encoding and content-length: httpx automatically
        # decompresses gzip/br/deflate responses, so the body in resp.content
        # is already decoded.  Forwarding the original encoding header with the
        # wrong length causes h11 to reject the response.  We set a fresh
        # content-length that matches the actual (decoded) body below.
        _strip_resp = {
            "connection", "keep-alive", "transfer-encoding",
            "te", "trailers", "upgrade",
            "content-encoding", "content-length",
        }
        resp_headers = [
            [k.lower().encode() if isinstance(k, str) else k.lower(),
             v.encode() if isinstance(v, str) else v]
            for k, v in resp.headers.items()
            if k.lower() not in _strip_resp
        ]
        resp_headers.append([b"content-length", str(len(resp.content)).encode()])

        await send(
            {
                "type": "http.response.start",
                "status": resp.status_code,
                "headers": resp_headers,
            }
        )
        await send({"type": "http.response.body", "body": resp.content})

    # ──────────────────────────────────────────────
    # WebSocket proxy
    # ──────────────────────────────────────────────

    async def _proxy_ws(
        self,
        scope: "Scope",
        receive: "Receive",
        send: "Send",
        app_name: str,
        info: dict,
        path: str,
    ) -> None:
        """Proxy a WebSocket connection to the app's inner port.

        Uses ws_port (if registered) instead of port so that VNC-style apps
        can route HTTP to Flask and WebSocket directly to websockify without
        any gevent/async Flask requirement.

        Implemented with wsproto + asyncio streams — no extra dependencies.
        """
        import wsproto
        import wsproto.events as wsevents

        # ws_port overrides port for WebSocket traffic (e.g. VNC → websockify)
        port = info.get("ws_port") or info["port"]

        prefix = f"/{app_name}"
        stripped = path[len(prefix):] or "/"
        if not stripped.startswith("/"):
            stripped = "/" + stripped

        query = scope.get("query_string", b"")
        target_path = stripped + ("?" + query.decode("utf-8", errors="replace") if query else "")
        subprotocols = scope.get("subprotocols", [])

        # Consume the websocket.connect message from the ASGI server
        connect_msg = await receive()
        if connect_msg.get("type") != "websocket.connect":
            return

        # Open raw TCP connection to the inner service
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", port),
                timeout=5.0,
            )
        except (OSError, asyncio.TimeoutError):
            await send({"type": "websocket.close", "code": 1001,
                        "reason": "App port unreachable"})
            return

        # Use wsproto to perform the HTTP WebSocket upgrade handshake
        ws = wsproto.WSConnection(wsproto.ConnectionType.CLIENT)
        upgrade_bytes = ws.send(wsevents.Request(
            host=f"127.0.0.1:{port}",
            target=target_path,
            subprotocols=subprotocols,
        ))
        try:
            writer.write(upgrade_bytes)
            await writer.drain()
        except Exception:
            writer.close()
            await send({"type": "websocket.close", "code": 1001,
                        "reason": "Upstream write error"})
            return

        # Wait for AcceptConnection; buffer any data frames that arrive in
        # the same TCP segment as the HTTP 101 response
        accepted_subprotocol: str | None = None
        queued: list[dict] = []
        try:
            while True:
                chunk = await asyncio.wait_for(reader.read(4096), timeout=10.0)
                if not chunk:
                    writer.close()
                    await send({"type": "websocket.close", "code": 1001,
                                "reason": "Upstream closed during handshake"})
                    return
                ws.receive_data(chunk)
                done = False
                for event in ws.events():
                    if isinstance(event, wsevents.AcceptConnection):
                        accepted_subprotocol = event.subprotocol
                        done = True
                    elif isinstance(event, wsevents.RejectConnection):
                        writer.close()
                        await send({"type": "websocket.close", "code": 1001,
                                    "reason": "Upstream rejected handshake"})
                        return
                    elif done and isinstance(event, wsevents.Message):
                        # Data arrived in same buffer as 101 response
                        if isinstance(event.data, bytes):
                            queued.append({"type": "websocket.send", "bytes": event.data})
                        else:
                            queued.append({"type": "websocket.send", "text": event.data})
                if done:
                    break
        except asyncio.TimeoutError:
            writer.close()
            await send({"type": "websocket.close", "code": 1001,
                        "reason": "Upstream handshake timeout"})
            return

        # Accept the browser's WebSocket connection
        accept: dict = {"type": "websocket.accept"}
        if accepted_subprotocol:
            accept["subprotocol"] = accepted_subprotocol
        await send(accept)

        # Flush any frames that arrived alongside the 101 response
        for msg in queued:
            await send(msg)

        # ── Bidirectional pump ──────────────────────────────────────────────

        async def client_to_upstream() -> None:
            try:
                while True:
                    msg = await receive()
                    t = msg.get("type")
                    if t == "websocket.receive":
                        raw: bytes | None = msg.get("bytes")
                        text: str | None = msg.get("text")
                        if raw is not None:
                            out = ws.send(wsevents.Message(data=raw))
                        elif text is not None:
                            out = ws.send(wsevents.Message(data=text))
                        else:
                            continue
                        writer.write(out)
                        await writer.drain()
                    elif t == "websocket.disconnect":
                        try:
                            out = ws.send(wsevents.CloseConnection(
                                code=msg.get("code") or 1000))
                            writer.write(out)
                            await writer.drain()
                        except Exception:
                            pass
                        writer.close()
                        return
            except Exception:
                pass
            try:
                writer.close()
            except Exception:
                pass

        async def upstream_to_client() -> None:
            try:
                while True:
                    chunk = await reader.read(65536)
                    if not chunk:
                        break
                    ws.receive_data(chunk)
                    for event in ws.events():
                        if isinstance(event, wsevents.Message):
                            if isinstance(event.data, bytes):
                                await send({"type": "websocket.send", "bytes": event.data})
                            else:
                                await send({"type": "websocket.send", "text": event.data})
                        elif isinstance(event, wsevents.CloseConnection):
                            try:
                                out = ws.send(wsevents.CloseConnection(
                                    code=event.code or 1000))
                                writer.write(out)
                                await writer.drain()
                            except Exception:
                                pass
                            writer.close()
                            await send({"type": "websocket.close",
                                        "code": event.code or 1000})
                            return
                        elif isinstance(event, wsevents.Ping):
                            try:
                                out = ws.send(wsevents.Pong(payload=event.payload))
                                writer.write(out)
                                await writer.drain()
                            except Exception:
                                pass
            except Exception:
                pass
            try:
                await send({"type": "websocket.close", "code": 1001})
            except Exception:
                pass
            try:
                writer.close()
            except Exception:
                pass

        tasks = [
            asyncio.create_task(client_to_upstream()),
            asyncio.create_task(upstream_to_client()),
        ]
        try:
            _done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        except Exception:
            for task in tasks:
                task.cancel()

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
