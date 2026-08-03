"""Простые ежедневные напоминания о квестах (фоновая задача)."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from aiogram import Bot

from chatgr_core.repositories.db import get_connection, init_db
from chatgr_core.repositories.users import UserRepository

logger = logging.getLogger("chatgr_core.reminders")

# чтобы не слать повторно в тот же час
_sent_today: set[str] = set()


async def reminder_loop(bot: Bot, interval_sec: int = 300) -> None:
    """Каждые interval_sec проверяет пользователей с reminders.enabled."""
    while True:
        try:
            await _tick(bot)
        except Exception:
            logger.exception("reminder tick failed")
        await asyncio.sleep(interval_sec)


async def _tick(bot: Bot) -> None:
    global _sent_today
    now = datetime.now()
    day_key = now.strftime("%Y-%m-%d")
    # сброс ключей прошлого дня
    _sent_today = {k for k in _sent_today if k.startswith(day_key)}

    init_db()
    conn = get_connection()
    try:
        repo = UserRepository(conn)
        users = repo.users_with_reminders()
        for u in users:
            hour = int(u.get("hour") or 10)
            if now.hour != hour:
                continue
            key = f"{day_key}:{u['tg_user_id']}"
            if key in _sent_today:
                continue
            name = u.get("name") or "друг"
            text = (
                f"Доброе утро, {name}! 🌅\n"
                "Дневные квесты ждут — напиши «квесты» или /quests.\n"
                "Выкл: «стоп напоминаний»."
            )
            try:
                await bot.send_message(int(u["tg_user_id"]), text)
                _sent_today.add(key)
            except Exception:
                logger.warning("Cannot remind %s", u["tg_user_id"])
    finally:
        conn.close()
