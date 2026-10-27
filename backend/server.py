"""
GetRank.fun - Flask API server

Endpoints
---------
Auth
  POST   /api/auth/register     {email, password, display_name}
  POST   /api/auth/login        {email, password}
  POST   /api/auth/logout       (token in header)
  GET    /api/auth/me           (token in header)

Leaderboards
  GET    /api/leaderboards               ?category=&q=
  POST   /api/leaderboards               {name, description, category}   [auth]
  GET    /api/leaderboards/<id>          -> board + ranked entries
  DELETE /api/leaderboards/<id>                                    [owner]

Entries
  POST   /api/leaderboards/<id>/entries  {title, submitter, description, image_url}

Votes
  POST   /api/entries/<id>/vote          {direction: +1|-1}   [auth]

Meta
  GET    /api/categories
  GET    /api/health

Auth: send `Authorization: Bearer <token>` OR cookie `gr_token=<token>`.
"""

import os
import time
from functools import wraps

from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS

import database as db

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

SECRET_NAME = "gr_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


@app.route('/')
def index():
    """Serve frontend."""
    return send_from_directory(app.static_folder, 'index.html')


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _email_ok(email: str) -> bool:
    e = (email or "").strip().lower()
    return bool(e) and "@" in e and "." in e.split("@")[-1]


def _user_row_to_dict(row) -> dict:
    return {"id": row["id"], "email": row["email"], "display_name": row["display_name"]}


def _current_user(conn) -> dict | None:
    """Resolve the caller from Authorization header or gr_token cookie."""
    token = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
    if not token:
        token = request.cookies.get(SECRET_NAME)
    if not token:
        return None
    return db.get_user_by_token(conn, token)


def auth_required(fn):
    """Require a valid session; otherwise 401."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = getattr(g, "user", None)
        if not user:
            return _json_error("Authentication required", 401)
        g.user = user
        return fn(*args, **kwargs)

    return wrapper


def board_to_dict(row, stats: dict | None = None) -> dict:
    d = {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "category": row["category"],
        "creator_id": row["creator_id"],
        "created_at": row["created_at"],
    }
    if stats:
        d["entry_count"] = stats["entries"]
        d["vote_count"] = stats["votes"]
    return d


def entry_to_dict(row, score: int, votes: int, my_vote: int | None, rank: int | None = None) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "submitter": row["submitter"],
        "description": row["description"],
        "image_url": row["image_url"],
        "created_at": row["created_at"],
        "score": score,
        "votes": votes,
        "my_vote": my_vote,
        "rank": rank,
    }


# --------------------------------------------------------------------------- #
# Per-request setup / teardown
# --------------------------------------------------------------------------- #


@app.before_request
def _before():
    g.conn = db.get_db()
    g.user = _current_user(g.conn)


@app.teardown_request
def _teardown(exc):
    conn = getattr(g, "conn", None)
    if conn is not None:
        conn.close()


# --------------------------------------------------------------------------- #
# Meta
# --------------------------------------------------------------------------- #


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "getrank", "time": time.time()})


@app.get("/api/categories")
def categories():
    return jsonify({"categories": db.VALID_CATEGORIES})


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #


@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("display_name") or "").strip()

    if not _email_ok(email):
        return _json_error("A valid email address is required", 400)
    if len(password) < 6:
        return _json_error("Password must be at least 6 characters", 400)
    if not name:
        name = email.split("@")[0][:24]

    conn = g.conn
    exists = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if exists:
        return _json_error("An account with that email already exists", 409)

    phash, salt = db.hash_password(password)
    conn.execute(
        "INSERT INTO users(email, display_name, password_hash, salt, created_at) VALUES(?,?,?,?,?)",
        (email, name[:64], phash, salt, time.time()),
    )
    conn.commit()
    user_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    token = db.token_for_user(conn, user_id)
    conn.commit()

    user = conn.execute(
        "SELECT id, email, display_name FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    resp = jsonify({"user": _user_row_to_dict(user), "token": token})
    resp.set_cookie(SECRET_NAME, token, max_age=COOKIE_MAX_AGE, httponly=True, samesite="Lax")
    return resp, 201


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    row = g.conn.execute(
        "SELECT id, email, display_name, password_hash, salt FROM users WHERE email = ?", (email,)
    ).fetchone()
    if not row or not db.verify_password(password, row["password_hash"], row["salt"]):
        return _json_error("Invalid email or password", 401)

    token = db.token_for_user(g.conn, row["id"])
    g.conn.commit()
    resp = jsonify({"user": _user_row_to_dict(row), "token": token})
    resp.set_cookie(SECRET_NAME, token, max_age=COOKIE_MAX_AGE, httponly=True, samesite="Lax")
    return resp


@app.post("/api/auth/logout")
def logout():
    token = request.cookies.get(SECRET_NAME) or (
        request.headers.get("Authorization", "")[7:]
        if request.headers.get("Authorization", "").startswith("Bearer ")
        else None
    )
    if token:
        db.delete_token(g.conn, token)
        g.conn.commit()
    resp = jsonify({"ok": True})
    resp.delete_cookie(SECRET_NAME)
    return resp


@app.get("/api/auth/me")
def me():
    if not g.user:
        return jsonify({"user": None})
    return jsonify({"user": g.user})


# --------------------------------------------------------------------------- #
# Leaderboards
# --------------------------------------------------------------------------- #


@app.get("/api/leaderboards")
def list_leaderboards():
    conn = g.conn
    query = "SELECT * FROM leaderboards WHERE 1=1"
    params: list = []
    if request.args.get("category"):
        query += " AND category = ?"
        params.append(request.args["category"])
    q = (request.args.get("q") or "").strip()
    if q:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    query += " ORDER BY created_at DESC"

    boards = [dict(r) for r in conn.execute(query, params).fetchall()]
    if not boards:
        return jsonify({"leaderboards": []})

    # aggregate entry/vote counts per board in one pass
    ids = [b["id"] for b in boards]
    marks = ",".join("?" for _ in ids)
    entry_counts = {
        r["leaderboard_id"]: r["c"]
        for r in conn.execute(
            f"SELECT leaderboard_id, COUNT(*) c FROM entries WHERE leaderboard_id IN ({marks}) GROUP BY leaderboard_id",
            ids,
        ).fetchall()
    }
    vote_counts = {
        lb_id: r["c"]
        for lb_id in ids
        for r in conn.execute(
            f"""
            SELECT e.leaderboard_id, COUNT(*) c
              FROM entries e LEFT JOIN votes v ON v.entry_id = e.id
             WHERE e.leaderboard_id IN ({marks})
             GROUP BY e.leaderboard_id
            """,
            ids,
        ).fetchall()
        if r["leaderboard_id"] == lb_id
    }

    out = []
    for b in boards:
        out.append(
            board_to_dict(
                b,
                stats={
                    "entries": entry_counts.get(b["id"], 0),
                    "votes": vote_counts.get(b["id"], 0),
                },
            )
        )
    return jsonify({"leaderboards": out})


@app.post("/api/leaderboards")
@auth_required
def create_leaderboard():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    desc = (data.get("description") or "").strip()
    cat = (data.get("category") or "").strip()

    if not name:
        return _json_error("Board name is required", 400)
    if len(name) > 120:
        return _json_error("Board name is too long (max 120 chars)", 400)
    if cat not in db.VALID_CATEGORIES:
        return _json_error(
            "Category must be one of: " + ", ".join(db.VALID_CATEGORIES), 400
        )

    conn = g.conn
    conn.execute(
        "INSERT INTO leaderboards(name, description, category, creator_id, created_at) VALUES(?,?,?,?,?)",
        (name[:120], desc[:1000], cat, g.user["id"], time.time()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM leaderboards WHERE id = ?",
        (conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"],),
    ).fetchone()
    return jsonify({"leaderboard": board_to_dict(row)}), 201


@app.get("/api/leaderboards/<int:board_id>")
def get_leaderboard(board_id: int):
    conn = g.conn
    board = conn.execute("SELECT * FROM leaderboards WHERE id = ?", (board_id,)).fetchone()
    if not board:
        return _json_error("Leaderboard not found", 404)

    entries = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM entries WHERE leaderboard_id = ? ORDER BY id", (board_id,)
        ).fetchall()
    ]
    ids = [e["id"] for e in entries]
    scores = db.scores_for_entries(conn, ids)
    counts = db.vote_counts_for_entries(conn, ids)
    mine = db.my_votes_for_entries(conn, g.user["id"] if g.user else 0, ids)

    # rank by score desc, then votes desc, then newest
    ranked = sorted(
        entries, key=lambda e: (-scores.get(e["id"], 0), -counts.get(e["id"], 0), -e["created_at"])
    )
    ranked_entries = []
    for i, e in enumerate(ranked, start=1):
        ranked_entries.append(
            entry_to_dict(
                e, scores.get(e["id"], 0), counts.get(e["id"], 0), mine.get(e["id"]), rank=i
            )
        )

    return jsonify(
        {
            "leaderboard": board_to_dict(
                board,
                stats={"entries": len(entries), "votes": sum(counts.values())},
            ),
            "entries": ranked_entries,
        }
    )


@app.delete("/api/leaderboards/<int:board_id>")
@auth_required
def delete_leaderboard(board_id: int):
    conn = g.conn
    board = conn.execute("SELECT id FROM leaderboards WHERE id = ?", (board_id,)).fetchone()
    if not board:
        return _json_error("Leaderboard not found", 404)
    if board["id"] != g.user["id"] and _creator_of(conn, board_id) != g.user["id"]:
        return _json_error("You can only delete boards you created", 403)
    conn.execute("DELETE FROM leaderboards WHERE id = ?", (board_id,))
    conn.commit()
    return jsonify({"ok": True})


def _creator_of(conn, board_id: int):
    row = conn.execute("SELECT creator_id FROM leaderboards WHERE id = ?", (board_id,)).fetchone()
    return row["creator_id"] if row else None


# --------------------------------------------------------------------------- #
# Entries
# --------------------------------------------------------------------------- #


@app.post("/api/leaderboards/<int:board_id>/entries")
def submit_entry(board_id: int):
    conn = g.conn
    board = conn.execute("SELECT id FROM leaderboards WHERE id = ?", (board_id,)).fetchone()
    if not board:
        return _json_error("Leaderboard not found", 404)

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    submitter = (data.get("submitter") or "").strip()
    desc = (data.get("description") or "").strip()
    image = (data.get("image_url") or "").strip()

    if not title:
        return _json_error("Entry title is required", 400)
    if len(title) > 140:
        return _json_error("Title is too long (max 140 chars)", 400)
    if not submitter:
        submitter = g.user["display_name"] if g.user else "Anonymous"

    conn.execute(
        "INSERT INTO entries(leaderboard_id, title, submitter, description, image_url, created_at) VALUES(?,?,?,?,?,?)",
        (board_id, title[:140], submitter[:64], desc[:1000], image[:500], time.time()),
    )
    conn.commit()
    eid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    row = conn.execute("SELECT * FROM entries WHERE id = ?", (eid,)).fetchone()
    return jsonify(
        {"entry": entry_to_dict(row, 0, 0, None, rank=None)},
    ), 201


# --------------------------------------------------------------------------- #
# Votes
# --------------------------------------------------------------------------- #


@app.post("/api/entries/<int:entry_id>/vote")
@auth_required
def vote(entry_id: int):
    conn = g.conn
    entry = conn.execute("SELECT id FROM entries WHERE id = ?", (entry_id,)).fetchone()
    if not entry:
        return _json_error("Entry not found", 404)

    data = request.get_json(silent=True) or {}
    try:
        direction = int(data.get("direction", 1))
    except (TypeError, ValueError):
        direction = 1
    direction = 1 if direction > 0 else -1

    existing = conn.execute(
        "SELECT direction FROM votes WHERE entry_id = ? AND user_id = ?",
        (entry_id, g.user["id"]),
    ).fetchone()

    if existing and existing["direction"] == direction:
        # clicking same direction again = withdraw the vote
        conn.execute("DELETE FROM votes WHERE entry_id = ? AND user_id = ?", (entry_id, g.user["id"]))
        new_dir = None
    else:
        if existing:
            conn.execute(
                "UPDATE votes SET direction = ?, created_at = ? WHERE entry_id = ? AND user_id = ?",
                (direction, time.time(), entry_id, g.user["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO votes(entry_id, user_id, direction, created_at) VALUES(?,?,?,?,?)",
                (entry_id, g.user["id"], direction, time.time()),
            )
        new_dir = direction
    conn.commit()

    scores = db.scores_for_entries(conn, [entry_id])
    counts = db.vote_counts_for_entries(conn, [entry_id])
    return jsonify(
        {
            "entry_id": entry_id,
            "direction": new_dir,
            "score": scores.get(entry_id, 0),
            "votes": counts.get(entry_id, 0),
        }
    )


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


if __name__ == "__main__":
    db.init_db(seed_demo=True)
    port = int(os.environ.get("PORT", 5002))
    print(f"GetRank API running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
