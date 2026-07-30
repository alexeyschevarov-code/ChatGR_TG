"""CRUD пользователей, сообщений, ачивок, игровых сессий."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from chatgr_core.core.dialog import default_profile, default_state
from chatgr_core.core.xp import level_from_xp


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class UserRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def ensure_user(self, tg_user_id: str) -> None:
        cur = self.conn.execute(
            "SELECT tg_user_id FROM users WHERE tg_user_id = ?",
            (str(tg_user_id),),
        )
        if cur.fetchone():
            return
        now = _now()
        self.conn.execute(
            """
            INSERT INTO users (tg_user_id, name, character, xp, level, profile_json,
                               topic_counts, is_banned, created_at, updated_at)
            VALUES (?, NULL, 'обычный', 0, 1, '{}', '{}', 0, ?, ?)
            """,
            (str(tg_user_id), now, now),
        )
        self.conn.commit()

    def is_banned(self, tg_user_id: str) -> bool:
        row = self.conn.execute(
            "SELECT is_banned FROM users WHERE tg_user_id = ?",
            (str(tg_user_id),),
        ).fetchone()
        return bool(row and row["is_banned"])

    def set_banned(self, tg_user_id: str, banned: bool) -> None:
        self.ensure_user(tg_user_id)
        self.conn.execute(
            "UPDATE users SET is_banned = ?, updated_at = ? WHERE tg_user_id = ?",
            (1 if banned else 0, _now(), str(tg_user_id)),
        )
        self.conn.commit()

    def load_dialog_context(self, tg_user_id: str) -> tuple[dict, dict]:
        """Загружает state + profile для DialogEngine."""
        self.ensure_user(tg_user_id)
        row = self.conn.execute(
            "SELECT * FROM users WHERE tg_user_id = ?",
            (str(tg_user_id),),
        ).fetchone()
        state = default_state()
        profile = default_profile()
        if not row:
            return state, profile

        state["name"] = row["name"]
        state["character"] = row["character"] or "обычный"
        state["last_topic"] = row["last_topic"]
        try:
            state["topic_counts"] = json.loads(row["topic_counts"] or "{}")
        except json.JSONDecodeError:
            state["topic_counts"] = {}

        try:
            saved = json.loads(row["profile_json"] or "{}")
        except json.JSONDecodeError:
            saved = {}
        profile.update(saved)
        profile["xp"] = int(row["xp"] or 0)
        profile["level"] = int(row["level"] or level_from_xp(profile["xp"]))

        # achievements from table
        ach_rows = self.conn.execute(
            "SELECT ach_id FROM achievements WHERE tg_user_id = ?",
            (str(tg_user_id),),
        ).fetchall()
        profile["achievements"] = [r["ach_id"] for r in ach_rows]

        # active game session
        g = self.conn.execute(
            """
            SELECT * FROM game_sessions
            WHERE tg_user_id = ? AND finished_at IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (str(tg_user_id),),
        ).fetchone()
        if g and g["state_json"]:
            try:
                state["game_state"] = json.loads(g["state_json"])
            except json.JSONDecodeError:
                state["game_state"] = None
        return state, profile

    def save_dialog_context(
        self,
        tg_user_id: str,
        state: dict,
        profile: dict,
        user_text: str = "",
        bot_text: str = "",
        topic: str | None = None,
    ) -> None:
        self.ensure_user(tg_user_id)
        now = _now()
        xp = int(profile.get("xp") or 0)
        level = level_from_xp(xp)
        profile_copy = dict(profile)
        achievements = list(profile_copy.pop("achievements", []) or [])

        self.conn.execute(
            """
            UPDATE users SET
                name = ?, character = ?, last_topic = ?,
                xp = ?, level = ?, profile_json = ?, topic_counts = ?,
                updated_at = ?
            WHERE tg_user_id = ?
            """,
            (
                state.get("name"),
                state.get("character") or "обычный",
                state.get("last_topic"),
                xp,
                level,
                json.dumps(profile_copy, ensure_ascii=False),
                json.dumps(state.get("topic_counts") or {}, ensure_ascii=False),
                now,
                str(tg_user_id),
            ),
        )

        for ach_id in achievements:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO achievements (tg_user_id, ach_id, unlocked_at)
                VALUES (?, ?, ?)
                """,
                (str(tg_user_id), ach_id, now),
            )

        if user_text or bot_text:
            self.conn.execute(
                """
                INSERT INTO messages (tg_user_id, user_text, bot_text, topic, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(tg_user_id), user_text, bot_text, topic, now),
            )

        # game session
        gstate = state.get("game_state")
        open_sess = self.conn.execute(
            """
            SELECT id FROM game_sessions
            WHERE tg_user_id = ? AND finished_at IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (str(tg_user_id),),
        ).fetchone()

        if gstate:
            payload = json.dumps(gstate, ensure_ascii=False)
            gtype = gstate.get("type", "unknown")
            score = int(gstate.get("score") or 0)
            attempts = int(gstate.get("attempts") or 0)
            if open_sess:
                self.conn.execute(
                    """
                    UPDATE game_sessions SET game_type=?, score=?, attempts=?, state_json=?
                    WHERE id=?
                    """,
                    (gtype, score, attempts, payload, open_sess["id"]),
                )
            else:
                self.conn.execute(
                    """
                    INSERT INTO game_sessions
                    (tg_user_id, game_type, score, attempts, state_json, started_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (str(tg_user_id), gtype, score, attempts, payload, now),
                )
        elif open_sess:
            self.conn.execute(
                "UPDATE game_sessions SET finished_at = ?, state_json = NULL WHERE id = ?",
                (now, open_sess["id"]),
            )

        self.conn.commit()

    def leaderboard(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT tg_user_id, name, xp, level
            FROM users
            WHERE is_banned = 0
            ORDER BY xp DESC, name ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        result = []
        for r in rows:
            display = r["name"] or f"Игрок {str(r['tg_user_id'])[-4:]}"
            result.append({
                "tg_user_id": r["tg_user_id"],
                "name": display,
                "xp": r["xp"],
                "level": r["level"],
            })
        return result

    def list_users(self, limit: int = 100) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT tg_user_id, name, xp, level, is_banned, character, updated_at
            FROM users ORDER BY updated_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict[str, int]:
        users = self.conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        banned = self.conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE is_banned = 1"
        ).fetchone()["c"]
        messages = self.conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
        games = self.conn.execute("SELECT COUNT(*) AS c FROM game_sessions").fetchone()["c"]
        total_xp = self.conn.execute(
            "SELECT COALESCE(SUM(xp), 0) AS s FROM users"
        ).fetchone()["s"]
        return {
            "users": users,
            "banned": banned,
            "messages": messages,
            "game_sessions": games,
            "total_xp": total_xp,
        }

    def recent_messages(self, tg_user_id: str, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT user_text, bot_text, topic, created_at
            FROM messages WHERE tg_user_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (str(tg_user_id), limit),
        ).fetchall()
        return [dict(r) for r in rows]
