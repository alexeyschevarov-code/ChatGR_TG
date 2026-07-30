from aiogram import Router

from chatgr_core.bot.handlers.callbacks import router as callbacks_router
from chatgr_core.bot.handlers.common import router as common_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(common_router)
    root.include_router(callbacks_router)
    return root
