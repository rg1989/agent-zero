from flask import Flask, Response, render_template_string, request, jsonify
import os
import threading
import time
import json
import base64
import asyncio
import urllib.request

app = Flask(__name__)

CDP_URL = "http://localhost:9222"
SCREENSHOT_TTL = 0.8  # seconds

_lock = threading.Lock()
_last_png: bytes | None = None
_last_png_time: float = 0.0


# ── CDP helpers ───────────────────────────────────────────────────────────────

async def _get_ws_url() -> str:
    import websockets  # noqa: F401 (confirm available)
    with urllib.request.urlopen(f"{CDP_URL}/json", timeout=3) as r:
        tabs = json.loads(r.read())
    if not tabs:
        raise RuntimeError("No CDP tabs")
    return tabs[0]["webSocketDebuggerUrl"]


async def _cdp(method: str, params: dict | None = None, msg_id: int = 1) -> dict:
    """Send one CDP command and return the result."""
    import websockets
    ws_url = await _get_ws_url()
    async with websockets.connect(ws_url, max_size=None, open_timeout=5) as ws:
        await ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            msg = json.loads(raw)
            if msg.get("id") == msg_id:
                return msg.get("result", {})


async def _cdp_multi(commands: list[tuple]) -> None:
    """Send multiple CDP commands on one connection."""
    import websockets
    ws_url = await _get_ws_url()
    async with websockets.connect(ws_url, max_size=None, open_timeout=5) as ws:
        for msg_id, (method, params) in enumerate(commands, start=1):
            await ws.send(json.dumps({"id": msg_id, "method": method, "params": params}))
        # drain responses
        for _ in commands:
            await asyncio.wait_for(ws.recv(), timeout=5)


def _run(coro):
    return asyncio.run(coro)


# ── Screenshot (cached) ───────────────────────────────────────────────────────

async def _cdp_screenshot_async() -> bytes | None:
    result = await _cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
    data = result.get("data")
    return base64.b64decode(data) if data else None


def _take_screenshot() -> bytes | None:
    global _last_png, _last_png_time
    with _lock:
        now = time.time()
        if now - _last_png_time < SCREENSHOT_TTL and _last_png:
            return _last_png
        try:
            data = _run(_cdp_screenshot_async())
            if data:
                _last_png = data
                _last_png_time = now
        except Exception as e:
            app.logger.debug(f"screenshot: {e}")
        return _last_png


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/api/screenshot')
def screenshot():
    data = _take_screenshot()
    if data:
        return Response(data, mimetype='image/png',
                        headers={'Cache-Control': 'no-cache, no-store'})
    return Response(status=503)


@app.route('/api/url')
def current_url():
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json", timeout=2) as r:
            tabs = json.loads(r.read())
        url = tabs[0].get("url", "") if tabs else ""
    except Exception:
        url = ""
    return Response(url, mimetype='text/plain',
                    headers={'Cache-Control': 'no-cache, no-store'})


@app.route('/api/navigate', methods=['POST'])
def navigate():
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify({"ok": False, "error": "no url"}), 400
    if "://" not in url:
        url = "https://" + url
    try:
        _run(_cdp("Page.navigate", {"url": url}))
        # Invalidate screenshot cache so next poll shows new page
        global _last_png_time
        _last_png_time = 0
        return jsonify({"ok": True, "url": url})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/click', methods=['POST'])
def click():
    body = request.json or {}
    x, y = float(body.get("x", 0)), float(body.get("y", 0))
    try:
        _run(_cdp_multi([
            ("Input.dispatchMouseEvent",
             {"type": "mousePressed", "x": x, "y": y,
              "button": "left", "clickCount": 1, "buttons": 1}),
            ("Input.dispatchMouseEvent",
             {"type": "mouseReleased", "x": x, "y": y,
              "button": "left", "clickCount": 1, "buttons": 0}),
        ]))
        global _last_png_time
        _last_png_time = 0
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/scroll', methods=['POST'])
def scroll():
    body = request.json or {}
    x = float(body.get("x", 210))
    y = float(body.get("y", 400))
    dx = float(body.get("deltaX", 0))
    dy = float(body.get("deltaY", 0))
    try:
        _run(_cdp("Input.dispatchMouseEvent",
                  {"type": "mouseWheel", "x": x, "y": y,
                   "deltaX": dx, "deltaY": dy}))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/key', methods=['POST'])
def key():
    body = request.json or {}
    try:
        _run(_cdp("Input.dispatchKeyEvent", body))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/back', methods=['POST'])
def go_back():
    try:
        _run(_cdp("Runtime.evaluate", {"expression": "window.history.back()"}))
        global _last_png_time
        _last_png_time = 0
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/reload', methods=['POST'])
def reload_page():
    try:
        _run(_cdp("Page.reload", {}))
        global _last_png_time
        _last_png_time = 0
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── HTML ──────────────────────────────────────────────────────────────────────

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shared Browser - Agent Zero</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body {
            width: 100%; height: 100%;
            overflow: hidden;
            background: #111;
            display: flex; flex-direction: column;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* ── URL bar ── */
        #urlbar {
            display: flex; align-items: center; gap: 4px;
            padding: 5px 7px;
            background: #1a1a1a;
            border-bottom: 1px solid #2e2e2e;
            flex-shrink: 0;
        }
        .nav-btn {
            flex-shrink: 0;
            width: 26px; height: 26px;
            background: transparent;
            border: none;
            border-radius: 5px;
            color: #888;
            font-size: 14px;
            cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            transition: background .15s, color .15s;
        }
        .nav-btn:hover { background: #2e2e2e; color: #ccc; }
        .nav-btn:active { opacity: .6; }
        #status-dot {
            width: 7px; height: 7px; border-radius: 50%;
            background: #444; flex-shrink: 0;
            transition: background .3s;
        }
        #status-dot.on { background: #00c853; }
        #url-form { flex: 1; display: flex; }
        #url-input {
            flex: 1;
            background: #2a2a2a;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 4px 8px;
            color: #ddd;
            font-size: 12px;
            outline: none;
            transition: border-color .15s;
        }
        #url-input:focus { border-color: #00f2fe; }

        /* ── Viewport ── */
        #viewport {
            flex: 1;
            position: relative;
            overflow: hidden;
            cursor: default;
        }
        #live-view {
            display: block;
            width: 100%;
            height: auto;
            image-rendering: auto;
        }
        /* scroll container so tall pages don't get clipped */
        #scroll-area {
            position: absolute; inset: 0;
            overflow-y: auto;
            overflow-x: hidden;
        }

        /* ── Connecting overlay ── */
        #overlay {
            position: absolute; inset: 0;
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            background: #111;
            color: #888; font-size: 13px; gap: 12px;
        }
        .spinner {
            border: 3px solid rgba(255,255,255,.1);
            border-top-color: #00f2fe;
            border-radius: 50%; width: 28px; height: 28px;
            animation: spin .8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>

    <div id="urlbar">
        <button class="nav-btn" title="Back" onclick="goBack()">&#8592;</button>
        <button class="nav-btn" title="Reload" onclick="doReload()">&#8635;</button>
        <div id="status-dot"></div>
        <form id="url-form" onsubmit="navigateTo(event)">
            <input id="url-input" type="text"
                   placeholder="Enter URL and press Enter..."
                   autocomplete="off" spellcheck="false" />
        </form>
    </div>

    <div id="viewport">
        <div id="scroll-area">
            <img id="live-view" alt="" draggable="false" />
        </div>
        <div id="overlay">
            <div class="spinner"></div>
            <div>Connecting to browser&#8230;</div>
        </div>
    </div>

    <script>
    (function () {
        const img     = document.getElementById('live-view');
        const overlay = document.getElementById('overlay');
        const urlInput= document.getElementById('url-input');
        const dot     = document.getElementById('status-dot');
        const scrollEl= document.getElementById('scroll-area');

        // ── Screenshot polling ──────────────────────────────────────
        let connected  = false;
        let failCount  = 0;
        const REFRESH_MS = 800;

        // Natural browser viewport dimensions (updated from screenshot)
        let nativeW = 420, nativeH = 800;

        function refreshShot() {
            const next = new Image();
            next.onload = () => {
                img.src = next.src;
                nativeW = next.naturalWidth  || nativeW;
                nativeH = next.naturalHeight || nativeH;
                if (!connected) {
                    connected = true;
                    overlay.style.display = 'none';
                    dot.classList.add('on');
                }
                failCount = 0;
            };
            next.onerror = () => {
                failCount++;
                if (failCount >= 3 && connected) {
                    connected = false;
                    dot.classList.remove('on');
                    overlay.style.display = 'flex';
                }
            };
            next.src = './api/screenshot?' + Date.now();
        }

        // ── URL polling ─────────────────────────────────────────────
        function refreshUrl() {
            fetch('./api/url?' + Date.now())
                .then(r => r.text())
                .then(u => {
                    if (u && document.activeElement !== urlInput)
                        urlInput.value = u;
                })
                .catch(() => {});
        }

        setInterval(refreshShot, REFRESH_MS);
        setInterval(refreshUrl, 1500);
        refreshShot();
        refreshUrl();

        // ── Navigation ──────────────────────────────────────────────
        window.navigateTo = function (e) {
            e.preventDefault();
            const url = urlInput.value.trim();
            if (!url) return;
            urlInput.blur();
            fetch('./api/navigate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url })
            });
        };

        window.goBack = function () {
            fetch('./api/back', { method: 'POST' });
        };

        window.doReload = function () {
            fetch('./api/reload', { method: 'POST' });
        };

        // ── Coordinate mapping ──────────────────────────────────────
        // img is rendered at 100% width; height scales proportionally.
        function imgCoords(e) {
            const r = img.getBoundingClientRect();
            const sx = nativeW / r.width;
            const sy = nativeH / r.height;
            return {
                x: (e.clientX - r.left)  * sx,
                y: (e.clientY - r.top)   * sy,
            };
        }

        // ── Click forwarding ────────────────────────────────────────
        let viewportFocused = false;

        img.addEventListener('click', (e) => {
            viewportFocused = true;
            urlInput.blur();
            const {x, y} = imgCoords(e);
            fetch('./api/click', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ x, y })
            });
        });

        urlInput.addEventListener('focus', () => { viewportFocused = false; });

        // ── Scroll forwarding ───────────────────────────────────────
        scrollEl.addEventListener('wheel', (e) => {
            e.preventDefault();
            const {x, y} = imgCoords(e);
            fetch('./api/scroll', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    x, y,
                    deltaX: e.deltaX,
                    deltaY: e.deltaY,
                })
            });
        }, { passive: false });

        // ── Keyboard forwarding ─────────────────────────────────────
        document.addEventListener('keydown', (e) => {
            if (!viewportFocused) return;
            // Let the browser keep ctrl/alt/meta combos
            if (e.ctrlKey && e.key !== 'Control') return;
            if (e.metaKey) return;

            e.preventDefault();

            const base = {
                key:                  e.key,
                code:                 e.code,
                windowsVirtualKeyCode:e.keyCode,
                nativeVirtualKeyCode: e.keyCode,
                modifiers:            (e.shiftKey ? 8 : 0) | (e.altKey ? 1 : 0),
            };

            const send = (extra) =>
                fetch('./api/key', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ ...base, ...extra })
                });

            send({ type: 'keyDown' });
            if (e.key.length === 1 || e.key === 'Enter' || e.key === 'Tab')
                send({ type: 'char', text: e.key === 'Enter' ? '\\r'
                                          : e.key === 'Tab'  ? '\\t' : e.key });
            send({ type: 'keyUp' });
        });
    })();
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9003))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
