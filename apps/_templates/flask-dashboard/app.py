"""
flask-dashboard — Flask app pre-wired for charts, metrics, and live data.

Extend /api/data to return your real data.
Chart.js is loaded from CDN — no npm needed.
"""
import os
import json
import time
import random
from flask import Flask, render_template, jsonify

app = Flask(__name__)

PORT     = int(os.environ.get("PORT", 9000))
APP_NAME = os.environ.get("APP_NAME", "")


# ── Main page ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", app_name=APP_NAME, title="Dashboard")


# ── Data API ──────────────────────────────────────────────────────────────────
# Replace the sample data below with your real data source.
# The front-end polls this every REFRESH_INTERVAL seconds.

@app.route("/api/data")
def api_data():
    """
    Return dashboard data.
    Shape expected by the default template:
      {
        "metrics": [{"label": str, "value": str, "unit": str, "color": str}],
        "chart":   {"labels": [...], "datasets": [{"label": str, "data": [...], "color": str}]}
      }
    """
    now = time.time()

    # ── Replace with your real metrics ───────────────────────────────────────
    metrics = [
        {"label": "Total",   "value": str(random.randint(900, 1200)), "unit": "",  "color": "#00f2fe"},
        {"label": "Active",  "value": str(random.randint(10, 50)),    "unit": "",  "color": "#00ff9d"},
        {"label": "Rate",    "value": f"{random.uniform(70,99):.1f}", "unit": "%", "color": "#ff9500"},
        {"label": "Errors",  "value": str(random.randint(0, 5)),      "unit": "",  "color": "#ff4444"},
    ]

    # ── Replace with your real time-series data ───────────────────────────────
    labels  = [time.strftime("%H:%M", time.localtime(now - 60 * i)) for i in range(11, -1, -1)]
    series1 = [random.randint(20, 100) for _ in range(12)]
    series2 = [random.randint(5,  40)  for _ in range(12)]

    return jsonify({
        "metrics": metrics,
        "chart": {
            "labels": labels,
            "datasets": [
                {"label": "Series A", "data": series1, "color": "#00f2fe"},
                {"label": "Series B", "data": series2, "color": "#ff9500"},
            ],
        },
        "updated_at": int(now),
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Dashboard '{APP_NAME or 'app'}' starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
