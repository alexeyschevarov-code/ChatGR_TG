"""Логирование с ротацией файлов."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from chatgr_core.config import LOG_DIR, LOG_FILE, LOG_LEVEL


def setup_logging(name: str = "chatgr_core") -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(level)

    logger.addHandler(file_handler)
    logger.addHandler(console)
    logger.propagate = False
    return logger
