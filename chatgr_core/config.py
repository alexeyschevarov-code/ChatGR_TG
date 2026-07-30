"""Конфигурация из .env (папка ChatGR TG + родительский проект)."""
from __future__ import annotations

import os
from pathlib import Path

# ChatGR TG/  (корень TG-проекта)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# MyPythonProjects/ (общий .env, tg_data)
PARENT_ROOT = PROJECT_ROOT.parent

try:
    from dotenv import load_dotenv

    # сначала родитель (BOT_TOKEN), потом локальный перекрывает
    load_dotenv(PARENT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env", override=True)
except ImportError:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me-admin")
ADMIN_USER_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_USER_IDS", "").split(",")
    if x.strip().isdigit()
}

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = Path(os.getenv("CHATGR_DB", str(DATA_DIR / "chatgr.db")))

# JSON для миграции: сначала локально, иначе родительский tg_data
_local_json = PROJECT_ROOT / "tg_data" / "users"
_parent_json = PARENT_ROOT / "tg_data" / "users"
JSON_USERS_DIR = _local_json if _local_json.exists() else _parent_json

VERSION = "0.6.0 beta"
XP_PER_LEVEL = 100
THROTTLE_RATE = float(os.getenv("THROTTLE_RATE", "0.7"))
THROTTLE_BURST = int(os.getenv("THROTTLE_BURST", "3"))

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook/chatgr")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8080"))
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "0").lower() in ("1", "true", "yes")

ADMIN_HOST = os.getenv("ADMIN_HOST", "127.0.0.1")
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8000"))

LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "chatgr.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
