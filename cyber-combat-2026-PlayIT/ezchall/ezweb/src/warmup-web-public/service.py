import json
import os
import secrets
import html
import re
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, render_template_string, request, session

DB_PATH = Path(os.environ.get("AD_STATE_DIR", "/opt/ad/state")) / "relicshare.db"
SERVICE_PORT = int(os.environ.get("PORT", os.environ.get("AD_PLATFORM_SERVICE_PORT", "8080")))
SECRET_KEY = secrets.token_hex(32)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["TEMPLATES_AUTO_RELOAD"] = False

TEMPLATE_BLOCKLIST = [
    "__class__",
    "__subclasses__",
    "__globals__",
    "__builtins__",
    "__import__",
]

SAFE_PLACEHOLDER_RE = re.compile(r"\{\{\s*relic\.(id|name|category|description|owner)\s*\}\}")

def safe_render_theme(theme: str, relic: dict) -> str:
    """Render only approved relic placeholders without evaluating Jinja2."""
    def replace_placeholder(match: re.Match) -> str:
        key = match.group(1)
        return html.escape(str(relic.get(key, "")))

    return SAFE_PLACEHOLDER_RE.sub(replace_placeholder, theme)

def sanitize_theme(theme: str) -> str | None:
    """Return None if the theme contains blocked patterns."""
    for blocked in TEMPLATE_BLOCKLIST:
        if blocked in theme:
            return None
    return theme

def get_db() -> sqlite3.Connection:
    db = getattr(g, "_db", None)
    if db is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        db = g._db = sqlite3.connect(str(DB_PATH))
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exc: Exception | None) -> None:
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()

def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS relics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'uncategorized',
            description TEXT NOT NULL DEFAULT '',
            theme TEXT NOT NULL DEFAULT '<p>{{ relic.name }}</p>',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        );
    """
    )
    db.commit()

def hash_password(password: str) -> str:

    import hashlib
    return hashlib.sha256(f"relicshare-{password}".encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "authentication required"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/api/unlock", methods=["POST"])
def unlock():
    data = request.get_json(silent=True) or {}
    submitted = (data.get("flag") or "").strip()
    if not submitted:
        return jsonify({"error": "flag required"}), 400
    flag_path = Path("/flag.txt")
    try:
        stored = flag_path.read_text().strip()
    except FileNotFoundError:
        return jsonify({"error": "no flag stored"}), 404
    if submitted != stored:
        return jsonify({"error": "invalid flag"}), 403
    proof = os.environ.get("AD_PLATFORM_UNLOCK_PROOF", "")
    return jsonify({"proof": proof})

@app.route("/api/relics")
def list_relics():
    db = get_db()
    rows = db.execute(
        "SELECT r.id, r.name, r.category, r.description, u.username AS owner "
        "FROM relics r JOIN users u ON r.owner_id = u.id "
        "ORDER BY r.created_at DESC"
    ).fetchall()
    return jsonify([dict(row) for row in rows])

@app.route("/api/relics/<int:relic_id>")
def relic_detail(relic_id: int):
    db = get_db()
    row = db.execute(
        "SELECT r.id, r.name, r.category, r.description, r.theme, u.username AS owner "
        "FROM relics r JOIN users u ON r.owner_id = u.id "
        "WHERE r.id = ?",
        (relic_id,),
    ).fetchone()
    if row is None:
        return jsonify({"error": "relic not found"}), 404

    relic = dict(row)
    theme = relic.pop("theme", "")

    try:
        rendered = safe_render_theme(theme, relic)
    except Exception as exc:
        rendered = f"<p class='error'>[theme render error: {exc}]</p>"

    relic["rendered"] = rendered
    return jsonify(relic)

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if len(username) < 3 or len(password) < 6:
        return jsonify({"error": "username ≥3 chars, password ≥6 chars"}), 400

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "username taken"}), 409

    user = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    session["user_id"] = user["id"]
    return jsonify({"status": "registered", "username": username}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    db = get_db()
    user = db.execute(
        "SELECT id, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    if user is None or user["password_hash"] != hash_password(password):
        return jsonify({"error": "invalid credentials"}), 401

    session["user_id"] = user["id"]
    return jsonify({"status": "logged_in", "username": username})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "logged_out"})

@app.route("/api/relics", methods=["POST"])
@login_required
def create_relic():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    category = (data.get("category") or "uncategorized").strip()
    description = (data.get("description") or "").strip()
    theme = (data.get("theme") or "<p>{{ relic.name }}</p>").strip()

    if not name:
        return jsonify({"error": "name required"}), 400
    if len(theme) > 2048:
        return jsonify({"error": "theme too long (max 2048 chars)"}), 400

    cleaned = sanitize_theme(theme)
    if cleaned is None:
        return jsonify({"error": "theme validation failed"}), 400

    db = get_db()
    cursor = db.execute(
        "INSERT INTO relics (owner_id, name, category, description, theme) VALUES (?, ?, ?, ?, ?)",
        (session["user_id"], name, category, description, cleaned),
    )
    db.commit()
    return jsonify({"status": "created", "id": cursor.lastrowid}), 201

@app.route("/api/relics/<int:relic_id>", methods=["PUT"])
@login_required
def update_relic(relic_id: int):
    db = get_db()
    relic = db.execute(
        "SELECT id, owner_id FROM relics WHERE id = ?", (relic_id,)
    ).fetchone()
    if relic is None:
        return jsonify({"error": "relic not found"}), 404
    if relic["owner_id"] != session["user_id"]:
        return jsonify({"error": "not your relic"}), 403

    data = request.get_json(silent=True) or {}
    theme = (data.get("theme") or "").strip()
    if theme:
        if len(theme) > 2048:
            return jsonify({"error": "theme too long (max 2048 chars)"}), 400
        cleaned = sanitize_theme(theme)
        if cleaned is None:
            return jsonify({"error": "theme validation failed"}), 400
        db.execute("UPDATE relics SET theme = ? WHERE id = ?", (cleaned, relic_id))
        db.commit()
        return jsonify({"status": "updated"})

    return jsonify({"error": "no fields to update"}), 400

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=SERVICE_PORT, debug=False)
