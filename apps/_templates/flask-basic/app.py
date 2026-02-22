"""
flask-basic — General-purpose Flask web app starter.

The proxy automatically routes:
  localhost:50000/{APP_NAME}/... → localhost:{PORT}/...

Environment variables set by the app manager:
  PORT     — port to listen on (required)
  APP_NAME — used in templates for sub-path routing via <base> tag
"""
import os
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

PORT = int(os.environ.get("PORT", 9000))
APP_NAME = os.environ.get("APP_NAME", "")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", app_name=APP_NAME, title="My App")


# Example API endpoint — replace or extend with your own logic
@app.route("/api/data")
def api_data():
    return jsonify({
        "status": "ok",
        "app": APP_NAME,
        "message": "Replace this with your actual data",
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Starting {APP_NAME or 'app'} on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
