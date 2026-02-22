"""
SSE stream for Welcome Screen banners. Updates every second so system resources
and other dynamic banners stay current without manual refresh.
"""
import asyncio
import json
import time
from flask import Response, request
from python.helpers.api import ApiHandler, Request
from python.helpers.extension import call_extensions


class BannersStream(ApiHandler):
    """
    GET endpoint that streams banner updates via Server-Sent Events (SSE).
    Emits a JSON event every second with the current banners.
    """

    async def process(self, input: dict, req: Request) -> Response:
        def build_context():
            if not request:
                return {}
            scheme = request.scheme or "http"
            if scheme and not scheme.endswith(":"):
                scheme = scheme + ":"
            host_parts = (request.host or "").split(":")
            return {
                "url": request.url or "",
                "protocol": scheme,
                "hostname": host_parts[0] if host_parts else "",
                "port": host_parts[-1] if len(host_parts) > 1 else "",
                "browser": request.headers.get("User-Agent", ""),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }

        async def fetch_banners():
            banners = []
            ctx = build_context()
            await call_extensions("banners", agent=None, banners=banners, frontend_context=ctx)
            return banners

        def stream_body():
            while True:
                try:
                    banners = asyncio.run(fetch_banners())
                    yield f"data: {json.dumps({'banners': banners})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(1)

        return Response(
            stream_body(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False  # GET, read-only; session auth is sufficient
