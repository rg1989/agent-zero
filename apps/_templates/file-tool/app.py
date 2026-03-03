"""
file-tool — Flask app for file upload, management, and conversion.

The proxy automatically routes:
  localhost:50000/{APP_NAME}/... → localhost:{PORT}/...

Environment variables set by the app manager:
  PORT     — port to listen on (required)
  APP_NAME — used in templates for sub-path routing via <base> tag

Features:
  - Drag-and-drop / multi-file upload (50 MB limit)
  - File listing with metadata (size, type, upload time)
  - File download and deletion
  - Format conversion: txt→json, csv→json, json→csv, txt→uppercase
"""
import os
import csv
import io
import json
import time
import mimetypes
import shutil
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

PORT = int(os.environ.get("PORT", 9000))
APP_NAME = os.environ.get("APP_NAME", "")

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

ALLOWED_EXTENSIONS = {
    "txt", "csv", "json", "md", "html", "css", "js", "py",
    "png", "jpg", "jpeg", "gif", "svg", "pdf", "zip",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename):
    """Return True if the file extension is in the allowed set."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_info(filename):
    """Return a dict of metadata for a file in UPLOAD_DIR."""
    path = os.path.join(UPLOAD_DIR, filename)
    size = os.path.getsize(path)
    if size < 1024:
        size_human = f"{size} B"
    elif size < 1024 * 1024:
        size_human = f"{size / 1024:.1f} KB"
    else:
        size_human = f"{size / (1024 * 1024):.1f} MB"
    mime_type, _ = mimetypes.guess_type(filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mtime = os.path.getmtime(path)
    uploaded_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime))
    return {
        "name": filename,
        "size": size,
        "size_human": size_human,
        "ext": ext,
        "mime_type": mime_type or "application/octet-stream",
        "uploaded_at": uploaded_at,
    }


# ── Page routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", app_name=APP_NAME, title="File Manager")


# ── API routes ────────────────────────────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Accept multipart/form-data upload. Field name: 'file' (single) or 'files' (multiple)."""
    uploaded_files = request.files.getlist("files") or request.files.getlist("file")
    if not uploaded_files or all(f.filename == "" for f in uploaded_files):
        return jsonify({"error": "No file provided"}), 400

    results = []
    for f in uploaded_files:
        if f.filename == "":
            continue
        if not allowed_file(f.filename):
            ext = f.filename.rsplit(".", 1)[-1] if "." in f.filename else "(none)"
            return jsonify({"error": f"File type '.{ext}' not allowed"}), 400
        filename = secure_filename(f.filename)
        f.save(os.path.join(UPLOAD_DIR, filename))
        results.append(get_file_info(filename))

    if not results:
        return jsonify({"error": "No valid files provided"}), 400

    return jsonify({"uploaded": results})


@app.route("/api/files", methods=["GET"])
def api_files():
    """List all files in UPLOAD_DIR sorted by upload time descending."""
    try:
        files = [
            get_file_info(f)
            for f in os.listdir(UPLOAD_DIR)
            if os.path.isfile(os.path.join(UPLOAD_DIR, f))
        ]
    except OSError:
        files = []
    files.sort(key=lambda x: x["uploaded_at"], reverse=True)
    return jsonify(files)


@app.route("/api/download/<filename>", methods=["GET"])
def api_download(filename):
    """Serve a file from UPLOAD_DIR as an attachment."""
    filename = secure_filename(filename)
    if not os.path.isfile(os.path.join(UPLOAD_DIR, filename)):
        abort(404)
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)


@app.route("/api/files/<filename>", methods=["DELETE"])
def api_delete(filename):
    """Delete a file from UPLOAD_DIR."""
    filename = secure_filename(filename)
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(path):
        return jsonify({"error": "File not found"}), 404
    os.remove(path)
    return jsonify({"ok": True})


@app.route("/api/convert/<filename>", methods=["POST"])
def api_convert(filename):
    """Convert a file to a target format.

    Supported conversions (POST JSON body: {"format": "target"}):
      txt  → json      (wrap lines as JSON array)
      csv  → json      (parse CSV to list of dicts)
      json → csv       (flatten JSON array of dicts to CSV)
      txt  → uppercase (save content as uppercase, new file *_upper.txt)
    """
    filename = secure_filename(filename)
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(path):
        abort(404)

    body = request.get_json(force=True, silent=True) or {}
    fmt = (body.get("format") or "").strip().lower()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename

    try:
        # txt → json
        if ext == "txt" and fmt == "json":
            with open(path, "r", encoding="utf-8") as fh:
                lines = [line.rstrip("\n") for line in fh]
            out_name = stem + "_converted.json"
            with open(os.path.join(UPLOAD_DIR, out_name), "w", encoding="utf-8") as fh:
                json.dump(lines, fh, indent=2)
            return jsonify(get_file_info(out_name))

        # csv → json
        if ext == "csv" and fmt == "json":
            with open(path, "r", encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
            out_name = stem + "_converted.json"
            with open(os.path.join(UPLOAD_DIR, out_name), "w", encoding="utf-8") as fh:
                json.dump(rows, fh, indent=2)
            return jsonify(get_file_info(out_name))

        # json → csv
        if ext == "json" and fmt == "csv":
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, list) or not data:
                return jsonify({"error": "JSON file must contain a non-empty array of objects"}), 400
            fieldnames = list(data[0].keys())
            out_name = stem + "_converted.csv"
            with open(os.path.join(UPLOAD_DIR, out_name), "w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(data)
            return jsonify(get_file_info(out_name))

        # txt → uppercase
        if ext == "txt" and fmt == "uppercase":
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            out_name = stem + "_upper.txt"
            with open(os.path.join(UPLOAD_DIR, out_name), "w", encoding="utf-8") as fh:
                fh.write(content.upper())
            return jsonify(get_file_info(out_name))

    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"error": "Unsupported conversion"}), 400


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Starting {APP_NAME or 'file-tool'} on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
