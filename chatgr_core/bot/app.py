"""Сборка Bot + Dispatcher (aiogram 3)."""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from chatgr_core.bot.handlers import setup_routers
from chatgr_core.bot.middlewares import ErrorMiddleware, ThrottlingMiddleware
from chatgr_core.config import BOT_TOKEN
from chatgr_core.repositories.db import get_connection, init_db
from chatgr_core.repositories.users import UserRepository
from chatgr_core.services.dialog_service import DialogService


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher, DialogService]:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в .env")

    init_db()
    conn = get_connection()
    repo = UserRepository(conn)
    dialog_service = DialogService(repo)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    # DI: handlers получают dialog_service: DialogService
    dp["dialog_service"] = dialog_service
    dp["db_conn"] = conn

    dp.message.middleware(ErrorMiddleware())
    dp.callback_query.middleware(ErrorMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.include_router(setup_routers())
    return bot, dp, dialog_service
