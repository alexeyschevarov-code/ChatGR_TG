"""SQLite schema and connection."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from chatgr_core.config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    tg_user_id   TEXT PRIMARY KEY,
    name         TEXT,
    character    TEXT NOT NULL DEFAULT 'обычный',
    last_topic   TEXT,
    xp           INTEGER NOT NULL DEFAULT 0,
    level        INTEGER NOT NULL DEFAULT 1,
    profile_json TEXT NOT NULL DEFAULT '{}',
    topic_counts TEXT NOT NULL DEFAULT '{}',
    is_banned    INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_user_id   TEXT NOT NULL,
    user_text    TEXT,
    bot_text     TEXT,
    topic        TEXT,
    created_at   TEXT NOT NULL,
    FOREIGN KEY (tg_user_id) REFERENCES users(tg_user_id)
);

CREATE TABLE IF NOT EXISTS achievements (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_user_id   TEXT NOT NULL,
    ach_id       TEXT NOT NULL,
    unlocked_at  TEXT NOT NULL,
    UNIQUE(tg_user_id, ach_id),
    FOREIGN KEY (tg_user_id) REFERENCES users(tg_user_id)
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_user_id   TEXT NOT NULL,
    game_type    TEXT NOT NULL,
    score        INTEGER DEFAULT 0,
    attempts     INTEGER DEFAULT 0,
    state_json   TEXT,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    FOREIGN KEY (tg_user_id) REFERENCES users(tg_user_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(tg_user_id);
CREATE INDEX IF NOT EXISTS idx_achievements_user ON achievements(tg_user_id);
CREATE INDEX IF NOT EXISTS idx_users_xp ON users(xp DESC);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(db_path or DB_PATH)
    conn = get_connection(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    return path
