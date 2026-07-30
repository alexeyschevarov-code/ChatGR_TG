"""Rate limiting: не чаще rate секунд между сообщениями (с burst)."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from chatgr_core.config import THROTTLE_BURST, THROTTLE_RATE


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate: float | None = None, burst: int | None = None):
        self.rate = rate if rate is not None else THROTTLE_RATE
        self.burst = burst if burst is not None else THROTTLE_BURST
        # user_id -> list of timestamps
        self._hits: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)
        if not event.from_user:
            return await handler(event, data)

        uid = event.from_user.id
        now = time.monotonic()
        window = self._hits[uid]
        # drop old
        window[:] = [t for t in window if now - t < 1.0]
        if len(window) >= self.burst:
            await event.answer("⏳ Слишком быстро. Подожди секунду.")
            return None
        # min interval between messages
        if window and (now - window[-1]) < self.rate:
            await event.answer("⏳ Подожди чуть-чуть…")
            return None
        window.append(now)
        return await handler(event, data)
