"""Сборка Bot + Dispatcher — 0.8.0 beta."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from chatgr_core.bot.handlers import setup_routers
from chatgr_core.bot.middlewares import ErrorMiddleware, ThrottlingMiddleware
from chatgr_core.bot.reminders import reminder_loop
from chatgr_core.config import BOT_TOKEN
from chatgr_core.repositories.db import backup_db, backup_loop, get_connection, init_db
from chatgr_core.repositories.users import UserRepository
from chatgr_core.services.dialog_service import DialogService

logger = logging.getLogger("chatgr_core.bot")


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher, DialogService]:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в .env")

    init_db()
    try:
        backup_db()
    except Exception:
        logger.exception("Backup on startup failed")

    conn = get_connection()
    repo = UserRepository(conn)
    dialog_service = DialogService(repo)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp["dialog_service"] = dialog_service
    dp["db_conn"] = conn

    dp.message.middleware(ErrorMiddleware())
    dp.callback_query.middleware(ErrorMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.include_router(setup_routers())

    @dp.startup()
    async def _on_startup() -> None:
        asyncio.create_task(reminder_loop(bot))
        asyncio.create_task(backup_loop(24.0))
        logger.info("Reminders + daily backup loops started")

    return bot, dp, dialog_service
