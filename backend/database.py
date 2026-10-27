"""
GetRank.fun - Database layer (SQLite)

Owns all persistence for the ranking platform:
  - users        : account + email/password auth
  - leaderboards : a ranking board scoped to a category
  - entries      : submitted items competing on a board
  - votes        : one vote per user per entry (up / down)

Public helpers:
  init_db()         -> create tables + seed demo data
  get_db()          -> request-local connection (call close_db in teardown)
  close_db()
  new_token()       -> opaque session token string
  store_token() / token_for_user() / get_user_by_token()
  helpers used by server.py for ranking math
"""

import hashlib
import secrets
import sqlite3
import time
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths / constants
# --------------------------------------------------------------------------- #

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "getrank.db"

VALID_CATEGORIES = [
    "Gaming",
    "Music",
    "Art",
    "Photography",
    "Sports",
    "Tech",
    "Food",
    "Design",
]

# --------------------------------------------------------------------------- #
# Password hashing (PBKDF2-HMAC-SHA256, constant-time compare)
# --------------------------------------------------------------------------- #


def hash_password(password: str, salt: bytes | None = None):
    """Return (hash_hex, salt_hex). Reuses salt when supplied."""
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return dk.hex(), salt.hex()


def verify_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 120_000
    )
    return secrets.compare_digest(dk.hex(), hash_hex)


# --------------------------------------------------------------------------- #
# Connection management
# --------------------------------------------------------------------------- #


def get_db() -> sqlite3.Connection:
    """A fresh connection per call. Server.py closes it in a teardown handler."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def close_db():
    pass  # server.py wraps each conn in try/finally


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE,
    display_name  TEXT    NOT NULL,
    password_hash TEXT    NOT NULL,
    salt          TEXT    NOT NULL,
    created_at    REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    created_at REAL    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS leaderboards (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    description  TEXT    NOT NULL DEFAULT '',
    category     TEXT    NOT NULL,
    creator_id   INTEGER NOT NULL,
    created_at   REAL    NOT NULL,
    FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS entries (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    leaderboard_id INTEGER NOT NULL,
    title          TEXT    NOT NULL,
    submitter      TEXT    NOT NULL,
    description    TEXT    NOT NULL DEFAULT '',
    image_url      TEXT    NOT NULL DEFAULT '',
    created_at     REAL    NOT NULL,
    FOREIGN KEY (leaderboard_id) REFERENCES leaderboards(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS votes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    direction  INTEGER NOT NULL,           -- +1 upvote, -1 downvote
    created_at REAL    NOT NULL,
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
    UNIQUE(entry_id, user_id)               -- one vote per user per entry
);

CREATE INDEX IF NOT EXISTS idx_entries_lb   ON entries(leaderboard_id);
CREATE INDEX IF NOT EXISTS idx_votes_entry  ON votes(entry_id);
CREATE INDEX IF NOT EXISTS idx_tokens_user  ON tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_lb_category  ON leaderboards(category);
"""


def init_db(seed_demo: bool = True):
    """Create schema. Optionally seed a couple of demo boards on first run."""
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    if seed_demo and conn.execute("SELECT COUNT(*) FROM leaderboards").fetchone()[0] == 0:
        _seed_demo(conn)
        conn.commit()
    conn.close()


# --------------------------------------------------------------------------- #
# Session tokens
# --------------------------------------------------------------------------- #


def new_token() -> str:
    return secrets.token_urlsafe(32)


def store_token(conn: sqlite3.Connection, user_id: int, token: str):
    conn.execute(
        "INSERT INTO tokens(token, user_id, created_at) VALUES(?, ?, ?)",
        (token, user_id, time.time()),
    )


def token_for_user(conn: sqlite3.Connection, user_id: int) -> str:
    token = new_token()
    store_token(conn, user_id, token)
    return token


def get_user_by_token(conn: sqlite3.Connection, token: str):
    row = conn.execute(
        """
        SELECT u.id, u.email, u.display_name, u.created_at
          FROM users u
          JOIN tokens t ON t.user_id = u.id
         WHERE t.token = ?
        """,
        (token,),
    ).fetchone()
    return dict(row) if row else None


def delete_token(conn: sqlite3.Connection, token: str):
    conn.execute("DELETE FROM tokens WHERE token = ?", (token,))


# --------------------------------------------------------------------------- #
# Ranking math
# --------------------------------------------------------------------------- #


def scores_for_entries(conn: sqlite3.Connection, entry_ids: list[int]) -> dict[int, int]:
    """Map entry_id -> net vote score. Empty list -> {} (avoids SQL `IN ()`)."""
    if not entry_ids:
        return {}
    scores: dict[int, int] = {eid: 0 for eid in entry_ids}
    marks = ",".join("?" for _ in entry_ids)
    rows = conn.execute(
        f"SELECT entry_id, SUM(direction) AS s FROM votes WHERE entry_id IN ({marks}) GROUP BY entry_id",
        entry_ids,
    ).fetchall()
    for r in rows:
        scores[r["entry_id"]] = int(r["s"] or 0)
    return scores


def vote_counts_for_entries(conn: sqlite3.Connection, entry_ids: list[int]) -> dict[int, int]:
    if not entry_ids:
        return {}
    counts: dict[int, int] = {eid: 0 for eid in entry_ids}
    marks = ",".join("?" for _ in entry_ids)
    rows = conn.execute(
        f"SELECT entry_id, COUNT(*) AS c FROM votes WHERE entry_id IN ({marks}) GROUP BY entry_id",
        entry_ids,
    ).fetchall()
    for r in rows:
        counts[r["entry_id"]] = int(r["c"] or 0)
    return counts


def my_votes_for_entries(conn: sqlite3.Connection, user_id: int, entry_ids: list[int]) -> dict[int, int]:
    if not user_id or not entry_ids:
        return {}
    mine: dict[int, int] = {}
    marks = ",".join("?" for _ in entry_ids)
    rows = conn.execute(
        f"SELECT entry_id, direction FROM votes WHERE user_id = ? AND entry_id IN ({marks})",
        [user_id, *entry_ids],
    ).fetchall()
    for r in rows:
        mine[r["entry_id"]] = int(r["direction"])
    return mine


# --------------------------------------------------------------------------- #
# Demo seed data
# --------------------------------------------------------------------------- #


def _seed_demo(conn: sqlite3.Connection):
    """A demo creator + a handful of boards so the app isn't empty on first boot."""
    now = time.time()

    demo_hash, demo_salt = hash_password("demo1234")
    conn.execute(
        "INSERT INTO users(email, display_name, password_hash, salt, created_at) VALUES(?,?,?,?,?)",
        ("demo@getrank.fun", "Demo Creator", demo_hash, demo_salt, now),
    )
    demo_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    boards = [
        ("Best FPS Games of 2026", "Community-picked top competitive shooters this year.", "Gaming"),
        ("Best Albums of the Decade", "The records that defined the last ten years.", "Music"),
        ("Top Indie Game Art", "Stunning pixel & concept art from indie studios.", "Art"),
        ("Best Street Photography", "Award-winning street shots from around the world.", "Photography"),
    ]
    for name, desc, cat in boards:
        conn.execute(
            "INSERT INTO leaderboards(name, description, category, creator_id, created_at) VALUES(?,?,?,?,?)",
            (name, desc, cat, demo_id, now),
        )

    sample_entries = [
        (1, "Cyber Strike", "Nova Studio", "Fast tactical shooter with destructible arenas."),
        (1, "Rush Protocol", "Iron Wolf", "5v5 elimination with vehicle traversal."),
        (1, "Hollow Point", "Maverick", "Brutal close-quarters gunplay."),
        (2, "Lunar Tides", "Aurora", "Ambient electronic with orchestral swells."),
        (2, "Concrete Bloom", "The Verge", "Post-punk revival, raw and angular."),
        (3, "Neon Botanica", "Pixel Fern", "Hand-painted flora in a rainy city."),
        (3, "Clockwork Sparrow", "Brass & Bolt", "Steampunk creature concept sheets."),
        (4, "Crosswalk", "M. Reyes", "Split-second capture of a commuter crossing."),
        (4, "Last Light Bus Stop", "H. Park", "Dusk silhouettes at a lonely stop."),
    ]
    for lb, title, submitter, desc in sample_entries:
        conn.execute(
            "INSERT INTO entries(leaderboard_id, title, submitter, description, created_at) VALUES(?,?,?,?,?)",
            (lb, title, submitter, desc, now),
        )
        eid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        # deterministic pseudo-votes so rankings are visible immediately
        # Only add votes from demo user (id=1) to avoid FK errors
        conn.execute(
                "INSERT OR IGNORE INTO votes(entry_id, user_id, direction, created_at) VALUES(?,?,?,?)",
                (eid, 1, 1, now),
            )
