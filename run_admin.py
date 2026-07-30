"""Запуск админ-панели: python run_admin.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import uvicorn

from chatgr_core.config import ADMIN_HOST, ADMIN_PORT
from chatgr_core.logging_setup import setup_logging

logger = setup_logging("chatgr_core.admin")


if __name__ == "__main__":
    logger.info("Admin panel http://%s:%s (token from ADMIN_TOKEN)", ADMIN_HOST, ADMIN_PORT)
    uvicorn.run(
        "chatgr_core.admin.app:app",
        host=ADMIN_HOST,
        port=ADMIN_PORT,
        reload=False,
    )
