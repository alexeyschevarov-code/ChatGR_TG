"""CRUD пользователей, сообщений, ачивок, игровых сессий (0.7.0)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from chatgr_core.core.dialog import default_profile, default_state
from chatgr_core.core.quests import ensure_daily_quests
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
            INSERT INTO users (
                tg_user_id, name, character, xp, level, coins,
                profile_json, topic_counts, daily_quests, reminders,
                spam_hits, is_banned, created_at, updated_at
            ) VALUES (?, NULL, 'обычный', 0, 1, 0, '{}', '{}', '{}', '{}', 0, 0, ?, ?)
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
        self.ensure_user(tg_user_id)
        row = self.conn.execute(
            "SELECT * FROM users WHERE tg_user_id = ?",
            (str(tg_user_id),),
        ).fetchone()
        state = default_state()
        profile = default_profile()
        if not row:
            return state, profile

        keys = row.keys()
        state["name"] = row["name"]
        state["character"] = row["character"] or "обычный"
        state["last_topic"] = row["last_topic"]
        state["spam_hits"] = int(row["spam_hits"] if "spam_hits" in keys else 0)
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
        if "coins" in keys:
            profile["coins"] = int(row["coins"] or profile.get("coins") or 0)
        try:
            if "daily_quests" in keys:
                profile["daily_quests"] = json.loads(row["daily_quests"] or "{}")
        except json.JSONDecodeError:
            pass
        try:
            if "reminders" in keys:
                rem = json.loads(row["reminders"] or "{}")
                if rem:
                    profile["reminders"] = rem
        except json.JSONDecodeError:
            pass
        profile = ensure_daily_quests(profile)

        ach_rows = self.conn.execute(
            "SELECT ach_id FROM achievements WHERE tg_user_id = ?",
            (str(tg_user_id),),
        ).fetchall()
        profile["achievements"] = [r["ach_id"] for r in ach_rows]

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
        profile = ensure_daily_quests(profile)
        xp = int(profile.get("xp") or 0)
        level = level_from_xp(xp)
        coins = int(profile.get("coins") or 0)
        profile_copy = dict(profile)
        achievements = list(profile_copy.pop("achievements", []) or [])
        daily = profile_copy.pop("daily_quests", {})
        reminders = profile_copy.pop("reminders", {})

        self.conn.execute(
            """
            UPDATE users SET
                name = ?, character = ?, last_topic = ?,
                xp = ?, level = ?, coins = ?,
                profile_json = ?, topic_counts = ?,
                daily_quests = ?, reminders = ?,
                spam_hits = ?,
                updated_at = ?
            WHERE tg_user_id = ?
            """,
            (
                state.get("name"),
                state.get("character") or "обычный",
                state.get("last_topic"),
                xp,
                level,
                coins,
                json.dumps(profile_copy, ensure_ascii=False),
                json.dumps(state.get("topic_counts") or {}, ensure_ascii=False),
                json.dumps(daily or {}, ensure_ascii=False),
                json.dumps(reminders or {}, ensure_ascii=False),
                int(state.get("spam_hits") or 0),
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
            SELECT tg_user_id, name, xp, level, coins
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
            coins = r["coins"] if "coins" in r.keys() else 0
            result.append({
                "tg_user_id": r["tg_user_id"],
                "name": display,
                "xp": r["xp"],
                "level": r["level"],
                "coins": coins,
            })
        return result

    def list_users(self, limit: int = 100) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT tg_user_id, name, xp, level, coins, is_banned, character, updated_at
            FROM users ORDER BY updated_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict[str, Any]:
        users = self.conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        banned = self.conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE is_banned = 1"
        ).fetchone()["c"]
        messages = self.conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
        games = self.conn.execute("SELECT COUNT(*) AS c FROM game_sessions").fetchone()["c"]
        total_xp = self.conn.execute(
            "SELECT COALESCE(SUM(xp), 0) AS s FROM users"
        ).fetchone()["s"]
        total_coins = self.conn.execute(
            "SELECT COALESCE(SUM(coins), 0) AS s FROM users"
        ).fetchone()["s"]
        day_ago = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        dau = self.conn.execute(
            """
            SELECT COUNT(DISTINCT tg_user_id) AS c FROM messages
            WHERE created_at >= ?
            """,
            (day_ago,),
        ).fetchone()["c"]
        msgs_today = self.conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE created_at >= ?",
            (day_ago,),
        ).fetchone()["c"]
        return {
            "users": users,
            "banned": banned,
            "messages": messages,
            "game_sessions": games,
            "total_xp": total_xp,
            "total_coins": total_coins,
            "dau_24h": dau,
            "messages_24h": msgs_today,
        }

    def users_with_reminders(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT tg_user_id, name, reminders FROM users WHERE is_banned = 0"
        ).fetchall()
        out = []
        for r in rows:
            try:
                rem = json.loads(r["reminders"] or "{}")
            except json.JSONDecodeError:
                rem = {}
            if rem.get("enabled"):
                out.append({
                    "tg_user_id": r["tg_user_id"],
                    "name": r["name"],
                    "hour": int(rem.get("hour") or 10),
                })
        return out

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

    # ---- duels ----
    def create_duel(self, code: str, host_id: str, questions: list) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO duels
            (code, host_id, guest_id, questions, host_score, guest_score, status, created_at)
            VALUES (?, ?, NULL, ?, NULL, NULL, 'waiting', ?)
            """,
            (code, str(host_id), json.dumps(questions, ensure_ascii=False), _now()),
        )
        self.conn.commit()

    def get_duel(self, code: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM duels WHERE code = ?", (code.upper(),)
        ).fetchone()
        return dict(row) if row else None

    def join_duel(self, code: str, guest_id: str) -> dict | None:
        d = self.get_duel(code)
        if not d or d["status"] not in ("waiting", "active"):
            return None
        if d["guest_id"] and d["guest_id"] != str(guest_id):
            return None
        self.conn.execute(
            "UPDATE duels SET guest_id = ?, status = 'active' WHERE code = ?",
            (str(guest_id), code.upper()),
        )
        self.conn.commit()
        return self.get_duel(code)

    def set_duel_score(self, code: str, role: str, score: int) -> dict | None:
        col = "host_score" if role == "host" else "guest_score"
        self.conn.execute(
            f"UPDATE duels SET {col} = ? WHERE code = ?",
            (score, code.upper()),
        )
        self.conn.commit()
        d = self.get_duel(code)
        if d and d["host_score"] is not None and d["guest_score"] is not None:
            self.conn.execute(
                "UPDATE duels SET status = 'done' WHERE code = ?",
                (code.upper(),),
            )
            self.conn.commit()
            return self.get_duel(code)
        return d

