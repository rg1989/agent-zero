"""
static-html server — serves the current directory as a static website.

Automatically injects <base href="/APP_NAME/"> so all relative asset URLs
work correctly through the Agent Zero proxy.

No template engine needed — just edit index.html, style.css, app.js directly.
"""
import os
from flask import Flask, send_from_directory, Response

PORT     = int(os.environ.get("PORT", 9000))
APP_NAME = os.environ.get("APP_NAME", "")
BASE_TAG = f'<base href="/{APP_NAME}/">' if APP_NAME else ""

app = Flask(__name__, static_folder=".", static_url_path="")


@app.route("/")
def index():
    with open(os.path.join(os.path.dirname(__file__), "index.html"), encoding="utf-8") as f:
        html = f.read()
    # Inject base tag right after <head> so all relative URLs resolve correctly
    html = html.replace("<head>", f"<head>\n  {BASE_TAG}", 1)
    return Response(html, mimetype="text/html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


if __name__ == "__main__":
    print(f"Static app '{APP_NAME or 'app'}' serving on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
