"""
Точка входа Telegram-бота ChatGR (aiogram 3).

Polling (разработка):
  python main.py

Webhook (продакшен, USE_WEBHOOK=1):
  WEBHOOK_HOST=https://your.domain python main.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# корень проекта в PYTHONPATH
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aiohttp import web

from chatgr_core.bot.app import create_bot_and_dispatcher
from chatgr_core.config import (
    USE_WEBHOOK,
    WEBAPP_HOST,
    WEBAPP_PORT,
    WEBHOOK_HOST,
    WEBHOOK_PATH,
    WEBHOOK_SECRET,
)
from chatgr_core.logging_setup import setup_logging

logger = setup_logging("chatgr_core")


async def run_polling() -> None:
    bot, dp, _ = create_bot_and_dispatcher()
    logger.info("Starting polling…")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def run_webhook() -> None:
    if not WEBHOOK_HOST:
        raise RuntimeError("WEBHOOK_HOST не задан (например https://example.com)")

    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    bot, dp, _ = create_bot_and_dispatcher()
    url = f"{WEBHOOK_HOST.rstrip('/')}{WEBHOOK_PATH}"
    logger.info("Setting webhook: %s", url)
    await bot.set_webhook(url, secret_token=WEBHOOK_SECRET or None)

    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET or None,
    ).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
    logger.info("Webhook server on %s:%s path=%s", WEBAPP_HOST, WEBAPP_PORT, WEBHOOK_PATH)
    await site.start()
    await asyncio.Event().wait()


def main() -> None:
    try:
        if USE_WEBHOOK:
            asyncio.run(run_webhook())
        else:
            asyncio.run(run_polling())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception:
        logger.exception("Fatal error")
        raise


if __name__ == "__main__":
    main()
