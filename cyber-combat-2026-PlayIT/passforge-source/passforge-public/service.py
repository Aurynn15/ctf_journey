#!/usr/bin/env python3
import base64
import csv
import hashlib
import hmac
import io
import json
import os
import shlex
import sqlite3
import time
from functools import wraps
from pathlib import Path

import jinja2

from flask import Flask, Response, jsonify, request

from workspace import WorkspaceSettings, deep_merge


STATE_DIR = Path(os.environ.get("AD_STATE_DIR", "/opt/ad/state"))
DB_PATH = STATE_DIR / "passforge.sqlite3"
SESSION_KEY_PATH = STATE_DIR / "session.key"
SERVICE_PORT = int(os.environ.get("PORT", os.environ.get("AD_PLATFORM_SERVICE_PORT", "8120")))
FLAG_PATH = "/flag.txt"
CSV_FIELDS = ["vault_handle", "title", "login", "secret", "note"]

CHECKER_TOKEN = os.environ.get("AD_CHECKER_TOKEN", "").strip()
ADMIN_PASSWORD_OVERRIDE = os.environ.get("PASSFORGE_ADMIN_PASSWORD", "").strip()

app = Flask(__name__)
app.config["SECRET_KEY"] = ""


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def now() -> int:
    return int(time.time())


def request_json() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def status_payload(status: str, code: int = 200, **extra):
    return jsonify({"status": status, **extra}), code


def rows_as_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def load_session_key() -> str:
    configured = os.environ.get("PASSFORGE_SESSION_KEY", "").strip()
    if configured:
        return configured
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not SESSION_KEY_PATH.exists():
        SESSION_KEY_PATH.write_text(os.urandom(32).hex(), encoding="utf-8")
        SESSION_KEY_PATH.chmod(0o600)
    return SESSION_KEY_PATH.read_text(encoding="utf-8").strip()


def admin_password() -> str:
    if ADMIN_PASSWORD_OVERRIDE:
        return ADMIN_PASSWORD_OVERRIDE
    seed = CHECKER_TOKEN or load_session_key()
    return "adm_" + hmac.new(seed.encode(), b"passforge-admin", hashlib.sha256).hexdigest()[:24]


def init_db() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    app.config["SECRET_KEY"] = load_session_key()
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT UNIQUE NOT NULL,
              email TEXT NOT NULL,
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT 'user',
              created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vaults (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              handle TEXT UNIQUE NOT NULL,
              name TEXT NOT NULL,
              owner_uid INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vault_members (
              vault_id INTEGER NOT NULL,
              uid INTEGER NOT NULL,
              role TEXT NOT NULL,
              UNIQUE(vault_id, uid)
            );
            CREATE TABLE IF NOT EXISTS entries (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              vault_id INTEGER NOT NULL,
              title TEXT NOT NULL,
              login TEXT NOT NULL,
              secret TEXT NOT NULL,
              note TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );
            """
        )
    ensure_user("demo", "demo-password", "demo@passforge.local")
    ensure_admin()


def ensure_user(username: str, password: str, email: str, role: str = "user") -> sqlite3.Row:
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user:
            return user
        conn.execute(
            "INSERT INTO users(username, email, password_hash, role, created_at) VALUES(?, ?, ?, ?, ?)",
            (username, email, sha256(password), role, now()),
        )
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        ensure_owned_vault(conn, user["id"], f"vault-{username}", f"{username}'s Vault")
        return user


def ensure_admin() -> None:
    pw = admin_password()
    with db() as conn:
        admin = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
        if admin is None:
            conn.execute(
                "INSERT INTO users(username, email, password_hash, role, created_at) VALUES('admin', 'admin@passforge.local', ?, 'admin', ?)",
                (sha256(pw), now()),
            )
            admin = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
            ensure_owned_vault(conn, admin["id"], "vault-admin", "Administrator Vault")
        else:
            conn.execute("UPDATE users SET password_hash = ?, role = 'admin' WHERE username = 'admin'", (sha256(pw),))


def ensure_owned_vault(conn: sqlite3.Connection, uid: int, handle: str, name: str) -> sqlite3.Row:
    conn.execute("INSERT OR IGNORE INTO vaults(handle, name, owner_uid) VALUES(?, ?, ?)", (handle, name, uid))
    vault = conn.execute("SELECT * FROM vaults WHERE handle = ?", (handle,)).fetchone()
    conn.execute("INSERT OR IGNORE INTO vault_members(vault_id, uid, role) VALUES(?, ?, 'owner')", (vault["id"], uid))
    return vault


def insert_entry(conn: sqlite3.Connection, vault_id: int, row: dict) -> int:
    conn.execute(
        "INSERT INTO entries(vault_id, title, login, secret, note, created_at) VALUES(?, ?, ?, ?, ?, ?)",
        (
            vault_id,
            str(row.get("title", "entry")),
            str(row.get("login", "")),
            str(row.get("secret", "")),
            str(row.get("note", "")),
            now(),
        ),
    )
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def token_for(user: sqlite3.Row) -> str:
    payload = json.dumps({"uid": user["id"], "username": user["username"]}, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    sig = hmac.new(app.config["SECRET_KEY"].encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"


def user_from_token(token: str | None) -> sqlite3.Row | None:
    if not token or "." not in token:
        return None
    encoded, sig = token.rsplit(".", 1)
    expected = hmac.new(app.config["SECRET_KEY"].encode(), encoded.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    except Exception:
        return None
    uid = int(payload.get("uid", 0))
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


def current_user() -> sqlite3.Row | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return user_from_token(auth[7:])
    return user_from_token(request.cookies.get("pf_session"))


def require_auth(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify({"status": "unauthorized"}), 401
        return fn(user, *args, **kwargs)

    return inner


def require_admin(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify({"status": "unauthorized"}), 401
        if user["role"] != "admin":
            return jsonify({"status": "forbidden"}), 403
        return fn(user, *args, **kwargs)

    return inner


def ldap_filter_login(username: str, password: str) -> sqlite3.Row | None:
    ldap_filter = f"(&(uid={username})(userPassword={password}))"
    with db() as conn:
        users = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    injected = any(ch in username for ch in "*()|")
    if injected:
        for user in users:
            if f"(uid={user['username']})" in ldap_filter:
                return user
        if "(uid=*)" in ldap_filter:
            return users[0] if users else None
        return None
    for user in users:
        if username == user["username"] and user["password_hash"] == sha256(password):
            return user
    return None


def ldap_filter_search(query: str) -> list[dict]:
    ldap_filter = f"(|(uid=*{query}*)(mail=*{query}*))"
    with db() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.email, u.role, v.handle
            FROM users u JOIN vaults v ON v.owner_uid = u.id
            ORDER BY u.id
            """
        ).fetchall()
    if "*)" in query or "(uid=*" in query or "(|" in query:
        matches = rows
    else:
        q = query.lower()
        matches = [row for row in rows if q in row["username"].lower() or q in row["email"].lower()]
    return [{"username": r["username"], "email": r["email"], "role": r["role"], "vault_handle": r["handle"]} for r in matches]


def vault_for_user(handle: str, uid: int) -> sqlite3.Row | None:
    with db() as conn:
        return conn.execute(
            """
            SELECT v.* FROM vaults v
            JOIN vault_members m ON m.vault_id = v.id
            WHERE v.handle = ? AND m.uid = ?
            """,
            (handle, uid),
        ).fetchone()


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/health")
@app.get("/v1/health")
def health():
    return jsonify({"status": "ok", "service": "passforge"})


@app.post("/api/register")
def register():
    payload = request_json()
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    email = str(payload.get("email", f"{username}@passforge.local")).strip()
    if not username or not password or any(ch in username for ch in "/\\ \t\r\n"):
        return status_payload("bad_request", 400)
    if username == "admin":
        return status_payload("exists", 409)
    try:
        user = ensure_user(username, password, email, role="user")
    except sqlite3.IntegrityError:
        return status_payload("exists", 409)
    return jsonify({"status": "ok", "token": token_for(user), "username": user["username"]})


@app.post("/api/login")
def login():
    payload = request_json()
    username = str(payload.get("username", ""))
    password = str(payload.get("password", ""))
    user = ldap_filter_login(username, password)
    if user is None:
        return status_payload("invalid", 403)
    response = jsonify({"status": "ok", "token": token_for(user), "username": user["username"], "role": user["role"]})
    response.set_cookie("pf_session", token_for(user), httponly=True, samesite="Lax")
    return response


@app.get("/api/me")
@require_auth
def me(user):
    return jsonify({"username": user["username"], "email": user["email"], "role": user["role"]})


@app.post("/api/profile")
@require_auth
def update_profile(user):
    payload = request_json()
    updatable = {"email", "password", "role"}
    sets, values = [], []
    for key, value in payload.items():
        if key not in updatable:
            continue
        if key == "password":
            sets.append("password_hash = ?")
            values.append(sha256(str(value)))
        else:
            sets.append(f"{key} = ?")
            values.append(str(value))
    if sets:
        values.append(user["id"])
        with db() as conn:
            conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", values)
    with db() as conn:
        fresh = conn.execute("SELECT username, email, role FROM users WHERE id = ?", (user["id"],)).fetchone()
    return jsonify({"status": "ok", "profile": dict(fresh)})


@app.get("/api/directory/search")
@require_auth
def directory_search(user):
    query = request.args.get("q", "")
    return jsonify({"status": "ok", "items": ldap_filter_search(query)})


@app.get("/api/vaults")
@require_auth
def list_vaults(user):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT v.handle, v.name, m.role FROM vaults v
            JOIN vault_members m ON m.vault_id = v.id
            WHERE m.uid = ? ORDER BY v.id
            """,
            (user["id"],),
        ).fetchall()
    return jsonify({"status": "ok", "items": rows_as_dicts(rows)})


@app.post("/api/vaults")
@require_auth
def create_vault(user):
    payload = request_json()
    name = str(payload.get("name", "Vault")).strip() or "Vault"
    handle = str(payload.get("handle", f"vault-{user['username']}-{now()}")).strip()
    with db() as conn:
        ensure_owned_vault(conn, user["id"], handle, name)
    return jsonify({"status": "ok", "handle": handle})


@app.get("/api/vaults/<handle>/entries")
@require_auth
def list_entries(user, handle):
    vault = vault_for_user(handle, user["id"])
    if vault is None:
        return status_payload("not_found", 404)
    with db() as conn:
        rows = conn.execute("SELECT id, title, login, secret, note FROM entries WHERE vault_id = ? ORDER BY id", (vault["id"],)).fetchall()
    return jsonify({"status": "ok", "items": rows_as_dicts(rows)})


@app.post("/api/vaults/<handle>/entries")
@require_auth
def create_entry(user, handle):
    vault = vault_for_user(handle, user["id"])
    if vault is None:
        return status_payload("not_found", 404)
    payload = request_json()
    with db() as conn:
        entry_id = insert_entry(conn, vault["id"], payload)
    return jsonify({"status": "ok", "id": entry_id})


@app.get("/api/entries/<int:entry_id>")
@require_auth
def read_entry(user, entry_id):
    requested_vault = request.args.get("vault", "").strip()
    if requested_vault == "":
        return status_payload("bad_request", 400)
    vault = vault_for_user(requested_vault, user["id"])
    if vault is None:
        return status_payload("not_found", 404)
    with db() as conn:
        row = conn.execute(
            """
            SELECT e.id, v.handle AS vault_handle, e.title, e.login, e.secret, e.note
            FROM entries e JOIN vaults v ON v.id = e.vault_id
            WHERE e.id = ? AND e.vault_id = ?
            """,
            (entry_id, vault["id"]),
        ).fetchone()
    if row is None:
        return status_payload("not_found", 404)
    return jsonify({"status": "ok", "entry": dict(row)})


@app.get("/api/export")
@require_auth
def export_csv(user):
    handle = request.args.get("vault", "")
    vault = vault_for_user(handle, user["id"])
    if vault is None:
        return status_payload("not_found", 404)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    with db() as conn:
        rows = conn.execute("SELECT title, login, secret, note FROM entries WHERE vault_id = ? ORDER BY id", (vault["id"],)).fetchall()
    for row in rows:
        writer.writerow({"vault_handle": handle, "title": row["title"], "login": row["login"], "secret": row["secret"], "note": row["note"]})
    return Response(output.getvalue(), mimetype="text/csv")


@app.post("/api/import")
@require_auth
def import_csv(user):
    raw = request.get_data(as_text=True)
    reader = csv.DictReader(io.StringIO(raw))
    imported = 0
    with db() as conn:
        for row in reader:
            handle = (row.get("vault_handle") or f"vault-{user['username']}").strip()
            vault = vault_for_user(handle, user["id"])
            if vault is None:
                vault = ensure_owned_vault(conn, user["id"], handle, handle)
            insert_entry(conn, vault["id"], row)
            imported += 1
    return jsonify({"status": "ok", "imported": imported})


TEMPLATE_BANNED = [
    "__", "import", "popen", "system", "subprocess", "globals(", "getattr",
    "setattr", "os.", "flag", "proof", "eval", "exec", "compile", "config",
    "self", "request", "application", "lipsum", "\n", "\r",
]

_template_env = jinja2.Environment(autoescape=False)


def render_cell(template: str) -> str:
    low = template.lower()
    hits = [b for b in TEMPLATE_BANNED if b in low]
    if hits:
        raise ValueError(f"blocked tokens: {hits}")
    if len(template) > 4096:
        raise ValueError("template too long")
    return _template_env.from_string(template).render(rows=[1, 2, 3], total=6)


@app.post("/api/admin/smart-import")
@require_admin
def smart_import(user):
    raw = request.get_data(as_text=True)
    reader = csv.DictReader(io.StringIO(raw))
    results = []
    for row in reader:
        template = (row.get("template") or "").strip()
        if not template:
            results.append({"value": None})
            continue
        try:
            results.append({"value": render_cell(template)})
        except Exception as exc:
            results.append({"error": str(exc)})
    return jsonify({"status": "ok", "results": results})


RUNTIME = WorkspaceSettings()


def run_self_test(label: str = "passforge-healthy", *, prefix: str = "echo ") -> str:
    with os.popen(prefix + shlex.quote(str(label))) as pipe:
        return pipe.read().strip()


@app.post("/api/admin/settings")
@require_admin
def admin_settings(user):
    payload = request_json()
    try:
        deep_merge(payload, RUNTIME)
    except Exception as exc:
        return status_payload("merge_error", 400, reason=str(exc))
    return jsonify({
        "status": "ok",
        "settings": {
            "theme": RUNTIME.theme,
            "locale": RUNTIME.locale,
            "items_per_page": RUNTIME.items_per_page,
            "report_label": RUNTIME.report_label,
        },
    })


@app.post("/api/admin/maintenance")
@require_admin
def admin_maintenance(user):
    try:
        output = run_self_test(RUNTIME.report_label)
    finally:
        run_self_test.__kwdefaults__["prefix"] = "echo "
    return jsonify({"status": "ok", "output": output})


def main() -> None:
    init_db()
    app.run(host="0.0.0.0", port=SERVICE_PORT, threaded=True)


if __name__ == "__main__":
    main()
