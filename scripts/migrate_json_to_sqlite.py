"""
Миграция tg_data/users/*.json → SQLite (users, messages, achievements).

Запуск из корня проекта:
  python scripts/migrate_json_to_sqlite.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from chatgr_core.config import DB_PATH, JSON_USERS_DIR  # noqa: E402
from chatgr_core.core.xp import level_from_xp  # noqa: E402
from chatgr_core.repositories.db import get_connection, init_db  # noqa: E402


def migrate(json_dir: Path | None = None, db_path: Path | None = None) -> int:
    json_dir = Path(json_dir or JSON_USERS_DIR)
    db_path = Path(db_path or DB_PATH)
    init_db(db_path)
    conn = get_connection(db_path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = 0

    if not json_dir.exists():
        print(f"Нет папки {json_dir} — нечего мигрировать.")
        conn.close()
        return 0

    for path in sorted(json_dir.glob("*.json")):
        if path.name.endswith(".bak") or path.parent.name == "backups":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  skip {path.name}: {e}")
            continue

        tg_id = path.stem
        profile = data.get("profile") or {}
        xp = int(profile.get("xp") or 0)
        level = int(profile.get("level") or level_from_xp(xp))
        achievements = profile.get("achievements") or []
        topic_counts = data.get("topic_counts") or {}
        history = data.get("history") or []

        profile_copy = {
            k: v
            for k, v in profile.items()
            if k not in ("xp", "level", "achievements")
        }

        conn.execute(
            """
            INSERT INTO users (
                tg_user_id, name, character, last_topic, xp, level,
                profile_json, topic_counts, is_banned, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            ON CONFLICT(tg_user_id) DO UPDATE SET
                name=excluded.name,
                character=excluded.character,
                last_topic=excluded.last_topic,
                xp=excluded.xp,
                level=excluded.level,
                profile_json=excluded.profile_json,
                topic_counts=excluded.topic_counts,
                updated_at=excluded.updated_at
            """,
            (
                tg_id,
                data.get("name"),
                data.get("character") or "обычный",
                data.get("last_topic"),
                xp,
                level,
                json.dumps(profile_copy, ensure_ascii=False),
                json.dumps(topic_counts, ensure_ascii=False),
                now,
                now,
            ),
        )

        for ach_id in achievements:
            conn.execute(
                """
                INSERT OR IGNORE INTO achievements (tg_user_id, ach_id, unlocked_at)
                VALUES (?, ?, ?)
                """,
                (tg_id, ach_id, now),
            )

        # история сообщений
        conn.execute("DELETE FROM messages WHERE tg_user_id = ?", (tg_id,))
        for item in history[-100:]:
            conn.execute(
                """
                INSERT INTO messages (tg_user_id, user_text, bot_text, topic, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    tg_id,
                    item.get("user"),
                    item.get("bot"),
                    item.get("topic"),
                    item.get("datetime") or now,
                ),
            )
        count += 1
        print(f"  + {tg_id} (xp={xp}, msgs={len(history)})")

    conn.commit()
    conn.close()
    print(f"\nГотово: {count} пользователей → {db_path}")
    return count


if __name__ == "__main__":
    migrate()
