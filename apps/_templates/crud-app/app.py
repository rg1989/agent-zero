# ============================================================
# CUSTOMIZATION GUIDE
# Lines marked "# CUSTOMIZE:" → change these for your entity
# Lines marked "# DO NOT CHANGE" → required for routing/proxy
# Everything else → leave as-is unless you know what you're doing
# ============================================================
"""
crud-app — Flask + SQLite CRUD data management starter.

The proxy automatically routes:
  localhost:50000/{APP_NAME}/... → localhost:{PORT}/...

Environment variables set by the app manager:
  PORT     — port to listen on (required)
  APP_NAME — used in templates for sub-path routing via <base> tag

This template implements full Create / Read / Update / Delete operations
for a sample "Item" model.  To adapt it to a different entity:
  1. Change CREATE_TABLE_SQL (table name + columns)
  2. Update the CRUD route SQL queries to match your columns
  3. Update the form fields in templates/form.html
  4. Rename "item/items" references in routes and templates
"""
import os
import sqlite3
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, g, jsonify
)

app = Flask(__name__)
app.secret_key = "change-me-in-production"

PORT     = int(os.environ.get("PORT", 9000))   # DO NOT CHANGE — required for proxy routing
APP_NAME = os.environ.get("APP_NAME", "")       # DO NOT CHANGE — required for proxy routing


# ── Model Definition ──────────────────────────────────────────────────────────
#
# Sample model: Item
#   id          — auto-incrementing primary key
#   name        — short display name (required)
#   description — longer free-text description (optional)
#   status      — one of: active, inactive, archived
#   created_at  — automatically set on insert
#
# To adapt: change the table name, columns, and form fields.
# The CRUD routes follow the same pattern for any model.

DATABASE = os.path.join(os.path.dirname(__file__), "data.db")  # CUSTOMIZE: change filename if desired

# CUSTOMIZE: Change table name, column names, and types below.
# Keep 'id INTEGER PRIMARY KEY AUTOINCREMENT' and 'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'.
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT,
    status      TEXT    DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


# ── Database helpers ──────────────────────────────────────────────────────────

def get_db():
    """Return the per-request SQLite connection, creating it if needed."""
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute(CREATE_TABLE_SQL)
        db.commit()
    return db


@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


# ── CRUD Routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("items_list"))


@app.route("/items")
def items_list():
    db    = get_db()
    # CUSTOMIZE: change "items" to your table name
    items = db.execute("SELECT * FROM items ORDER BY created_at DESC").fetchall()
    return render_template("list.html", app_name=APP_NAME, items=items)  # DO NOT CHANGE template names — list.html, form.html, detail.html, 404.html must match files in templates/


@app.route("/items/<int:item_id>")
def items_detail(item_id):
    db   = get_db()
    # CUSTOMIZE: change "items" to your table name
    item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if item is None:
        return render_template("404.html", app_name=APP_NAME), 404  # DO NOT CHANGE template names — list.html, form.html, detail.html, 404.html must match files in templates/
    return render_template("detail.html", app_name=APP_NAME, item=item)  # DO NOT CHANGE template names — list.html, form.html, detail.html, 404.html must match files in templates/


@app.route("/items/new")
def items_new():
    return render_template("form.html", app_name=APP_NAME, item=None)  # DO NOT CHANGE template names — list.html, form.html, detail.html, 404.html must match files in templates/


@app.route("/items", methods=["POST"])
def items_create():
    # CUSTOMIZE: change column names in INSERT to match your CREATE_TABLE_SQL
    name        = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    status      = request.form.get("status", "active")

    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("items_new"))

    db = get_db()
    cur = db.execute(
        # CUSTOMIZE: change column names in INSERT to match your CREATE_TABLE_SQL
        "INSERT INTO items (name, description, status) VALUES (?, ?, ?)",
        (name, description, status),
    )
    db.commit()
    flash(f'Item "{name}" created.', "success")
    return redirect(url_for("items_detail", item_id=cur.lastrowid))


@app.route("/items/<int:item_id>/edit")
def items_edit(item_id):
    db   = get_db()
    # CUSTOMIZE: change "items" to your table name
    item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if item is None:
        return render_template("404.html", app_name=APP_NAME), 404  # DO NOT CHANGE template names — list.html, form.html, detail.html, 404.html must match files in templates/
    return render_template("form.html", app_name=APP_NAME, item=item)  # DO NOT CHANGE template names — list.html, form.html, detail.html, 404.html must match files in templates/


@app.route("/items/<int:item_id>/edit", methods=["POST"])
def items_update(item_id):
    # CUSTOMIZE: change column names in UPDATE to match your CREATE_TABLE_SQL
    name        = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    status      = request.form.get("status", "active")

    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("items_edit", item_id=item_id))

    db = get_db()
    db.execute(
        # CUSTOMIZE: change column names in UPDATE to match your CREATE_TABLE_SQL
        "UPDATE items SET name = ?, description = ?, status = ? WHERE id = ?",
        (name, description, status, item_id),
    )
    db.commit()
    flash(f'Item "{name}" updated.', "success")
    return redirect(url_for("items_detail", item_id=item_id))


@app.route("/items/<int:item_id>/delete", methods=["POST"])
def items_delete(item_id):
    db   = get_db()
    # CUSTOMIZE: change "items" to your table name
    item = db.execute("SELECT name FROM items WHERE id = ?", (item_id,)).fetchone()
    if item:
        db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        db.commit()
        flash(f'Item "{item["name"]}" deleted.', "success")
    return redirect(url_for("items_list"))


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.route("/api/items")
def api_items_list():
    db    = get_db()
    # CUSTOMIZE: change "items" to your table name
    items = db.execute("SELECT * FROM items ORDER BY created_at DESC").fetchall()
    return jsonify([dict(row) for row in items])


@app.route("/api/items/<int:item_id>", methods=["DELETE"])
def api_items_delete(item_id):
    db = get_db()
    # CUSTOMIZE: change "items" to your table name
    db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    db.commit()
    return jsonify({"ok": True})


# ── Entry point ───────────────────────────────────────────────────────────────

# DO NOT CHANGE — host must be 0.0.0.0 for proxy routing
if __name__ == "__main__":
    print(f"Starting {APP_NAME or 'crud-app'} on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
