"""Эмодзи-ответы (не стикер-паки Telegram — юникод-эмодзи)."""
from __future__ import annotations

import random

TOPIC_EMOJI = {
    "привет": ["👋", "🙂", "✨"],
    "дела": ["💭", "🌤️"],
    "космос": ["🚀", "🌌", "🪐", "⭐"],
    "игра": ["🎮", "🕹️", "👾"],
    "майнкрафт": ["🧱", "⛏️"],
    "школа": ["📚", "✏️"],
    "война": ["⚔️", "🛡️"],
    "музыка": ["🎵", "🎧"],
    "фильм": ["🎬", "🍿"],
    "спорт": ["⚽", "🏆"],
    "еда": ["🍕", "🍔", "🍰"],
    "животные": ["🐱", "🐶", "🐯"],
    "код": ["💻", "🐍"],
    "настроение": ["💙", "🌈"],
}

MOOD_EMOJI = {
    "плохо": ["💙", "🌧️"],
    "хорошо": ["😊", "✨"],
    "отлично": ["🔥", "🎉"],
    "супер": ["🚀", "💥"],
    "ужасно": ["🫂", "💙"],
}

WIN_EMOJI = ["🎉", "🏆", "🔥", "✨", "🐯"]
LOSE_EMOJI = ["😅", "💪", "🔁"]


def decorate_text(text: str, topic: str | None = None, rich: bool = False) -> str:
    """Добавляет эмодзи к ответу."""
    if not text:
        return text
    pool = TOPIC_EMOJI.get(topic or "", ["💬"])
    if topic == "настроение":
        # generic
        pool = ["💭", "💙", "✨"]
    emoji = random.choice(pool)
    if rich:
        extra = random.choice(pool)
        return f"{emoji} {text} {extra}"
    # ~60% chance add leading emoji
    if random.random() < 0.65:
        return f"{emoji} {text}"
    return text


def reaction_emoji(kind: str = "ok") -> str:
    if kind == "win":
        return random.choice(WIN_EMOJI)
    if kind == "lose":
        return random.choice(LOSE_EMOJI)
    return random.choice(["👍", "✨", "😊", "🐯", "🎮"])
