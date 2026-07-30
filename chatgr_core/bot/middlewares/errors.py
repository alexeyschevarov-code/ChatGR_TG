"""Глобальная обработка ошибок хендлеров."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger("chatgr.bot")


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception:
            logger.exception("Handler error")
            try:
                if isinstance(event, Message):
                    await event.answer("⚠️ Ошибка. Попробуй ещё раз или /start.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Ошибка", show_alert=True)
            except Exception:
                logger.exception("Failed to notify user about error")
            return None
