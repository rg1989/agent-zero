"""
dashboard-realtime — Flask dashboard with Server-Sent Events (SSE) for live data.

Primary data channel: GET /api/stream  — SSE, pushes JSON every 2 seconds.
Fallback channel:     GET /api/data    — single JSON snapshot for polling clients.

The front-end (templates/index.html) opens an EventSource, updates 3 Chart.js
charts (line, bar, doughnut) and 4 metric cards on every message.

Extend generate_data() to return your real data.
"""
import os
import json
import time
import random
from flask import Flask, render_template, jsonify, Response, stream_with_context

app = Flask(__name__)

PORT     = int(os.environ.get("PORT", 9000))
APP_NAME = os.environ.get("APP_NAME", "")


# ── Sample data generator ──────────────────────────────────────────────────────
# Replace this function with your real data source.
# Shape is shared between SSE and polling endpoints.

def generate_data():
    """Return a dashboard data payload."""
    now = time.time()

    # ── Metric cards (replace with real metrics) ──────────────────────────────
    metrics = [
        {"label": "Total",   "value": str(random.randint(900, 1200)), "unit": "",  "color": "#00f2fe"},
        {"label": "Active",  "value": str(random.randint(10, 50)),    "unit": "",  "color": "#00ff9d"},
        {"label": "Rate",    "value": f"{random.uniform(70, 99):.1f}", "unit": "%", "color": "#ff9500"},
        {"label": "Errors",  "value": str(random.randint(0, 5)),      "unit": "",  "color": "#ff4444"},
    ]

    # ── Line chart: 12-point time series (replace with real time-series) ──────
    time_labels = [time.strftime("%H:%M", time.localtime(now - 60 * i)) for i in range(11, -1, -1)]
    line = {
        "labels": time_labels,
        "datasets": [
            {"label": "Series A", "data": [random.randint(20, 100) for _ in range(12)], "color": "#00f2fe"},
            {"label": "Series B", "data": [random.randint(5,  40)  for _ in range(12)], "color": "#ff9500"},
        ],
    }

    # ── Bar chart: 6-category snapshot ───────────────────────────────────────
    bar_labels = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]
    bar = {
        "labels": bar_labels,
        "datasets": [
            {"label": "Count", "data": [random.randint(10, 80) for _ in range(6)], "color": "#00ff9d"},
        ],
    }

    # ── Doughnut chart: 4-segment breakdown ───────────────────────────────────
    doughnut = {
        "labels": ["Type A", "Type B", "Type C", "Type D"],
        "datasets": [
            {
                "data": [random.randint(10, 40) for _ in range(4)],
                "colors": ["#00f2fe", "#00ff9d", "#ff9500", "#ff4444"],
            }
        ],
    }

    return {
        "metrics":  metrics,
        "charts":   {"line": line, "bar": bar, "doughnut": doughnut},
        "updated_at": int(now),
    }


# ── Main page ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", app_name=APP_NAME, title="Dashboard")


# ── SSE endpoint — primary data channel ───────────────────────────────────────

@app.route("/api/stream")
def api_stream():
    """
    Server-Sent Events stream — pushes fresh data every 2 seconds.
    Client opens:  new EventSource("api/stream")
    Payload:       data: {json}\n\n
    """
    def event_stream():
        while True:
            payload = generate_data()
            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(2)

    resp = Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
    )
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Connection"]    = "keep-alive"
    return resp


# ── Polling fallback endpoint ──────────────────────────────────────────────────

@app.route("/api/data")
def api_data():
    """
    Single JSON snapshot — polling fallback for clients that cannot use SSE.
    Returns the same shape as the SSE payload.
    """
    return jsonify(generate_data())


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Realtime dashboard '{APP_NAME or 'app'}' starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
