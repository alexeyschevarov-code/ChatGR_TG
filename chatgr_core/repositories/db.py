"""SQLite schema, migrations, connection."""
from __future__ import annotations

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from chatgr_core.config import DATA_DIR, DB_PATH

logger = logging.getLogger("chatgr_core.db")

SCHEMA_VERSION = 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    tg_user_id   TEXT PRIMARY KEY,
    name         TEXT,
    character    TEXT NOT NULL DEFAULT 'обычный',
    last_topic   TEXT,
    xp           INTEGER NOT NULL DEFAULT 0,
    level        INTEGER NOT NULL DEFAULT 1,
    coins        INTEGER NOT NULL DEFAULT 0,
    profile_json TEXT NOT NULL DEFAULT '{}',
    topic_counts TEXT NOT NULL DEFAULT '{}',
    daily_quests TEXT NOT NULL DEFAULT '{}',
    reminders    TEXT NOT NULL DEFAULT '{}',
    spam_hits    INTEGER NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS duels (
    code         TEXT PRIMARY KEY,
    host_id      TEXT NOT NULL,
    guest_id     TEXT,
    questions    TEXT NOT NULL,
    host_score   INTEGER,
    guest_score  INTEGER,
    status       TEXT NOT NULL DEFAULT 'waiting',
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(tg_user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
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


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r["name"] for r in rows}


def _migrate(conn: sqlite3.Connection) -> None:
    """Идемпотентные миграции схемы."""
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key = 'version'"
    ).fetchone() if _table_exists(conn, "schema_meta") else None
    version = int(row["value"]) if row else 1

    # v2 columns on users
    if _table_exists(conn, "users"):
        cols = _column_names(conn, "users")
        alters = []
        if "coins" not in cols:
            alters.append("ALTER TABLE users ADD COLUMN coins INTEGER NOT NULL DEFAULT 0")
        if "daily_quests" not in cols:
            alters.append("ALTER TABLE users ADD COLUMN daily_quests TEXT NOT NULL DEFAULT '{}'")
        if "reminders" not in cols:
            alters.append("ALTER TABLE users ADD COLUMN reminders TEXT NOT NULL DEFAULT '{}'")
        if "spam_hits" not in cols:
            alters.append("ALTER TABLE users ADD COLUMN spam_hits INTEGER NOT NULL DEFAULT 0")
        for sql in alters:
            conn.execute(sql)
            logger.info("Migration: %s", sql)

    conn.execute(
        "INSERT INTO schema_meta(key, value) VALUES('version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(SCHEMA_VERSION),),
    )
    if version < SCHEMA_VERSION:
        logger.info("DB schema upgraded to v%s", SCHEMA_VERSION)


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    r = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return bool(r)


def init_db(db_path: Path | None = None) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(db_path or DB_PATH)
    conn = get_connection(path)
    try:
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()
    return path


def backup_db(db_path: Path | None = None, keep: int = 7) -> Path | None:
    """Копия БД в data/backups/ (дата + час, чтобы не перетирать)."""
    path = Path(db_path or DB_PATH)
    if not path.exists():
        return None
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    dest = backup_dir / f"chatgr_{stamp}.db"
    shutil.copy2(path, dest)
    files = sorted(backup_dir.glob("chatgr_*.db"), reverse=True)
    for old in files[keep:]:
        try:
            old.unlink()
        except OSError:
            pass
    logger.info("DB backup: %s", dest)
    return dest


async def backup_loop(interval_hours: float = 24.0) -> None:
    """Фоновый бэкап раз в interval_hours."""
    import asyncio

    while True:
        try:
            backup_db()
        except Exception:
            logger.exception("Scheduled backup failed")
        await asyncio.sleep(max(3600.0, interval_hours * 3600.0))
