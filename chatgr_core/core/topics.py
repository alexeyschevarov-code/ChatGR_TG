"""Распознавание тем и настроения."""
from __future__ import annotations

from chatgr_core.core.content import MOOD_RESPONSES, PHRASE_TO_TOPIC, TOPIC_ROOTS


def find_topic(user_input: str, words: list[str] | None = None) -> str | None:
    words = words if words is not None else user_input.split()
    age_hints = (
        "когда ты родился", "когда родился", "когда создан",
        "дата создания", "когда тебя создали",
    )
    if ("сколько" in words and "лет" in words) or any(h in user_input for h in age_hints):
        return "возраст"
    for phrase, topic in sorted(PHRASE_TO_TOPIC, key=lambda x: len(x[0]), reverse=True):
        if phrase in user_input:
            return topic
    for topic, roots in TOPIC_ROOTS:
        for root in roots:
            if any(word.startswith(root) for word in words):
                return topic
    return None


def find_mood(words: list[str]) -> str | None:
    for mood in sorted(MOOD_RESPONSES, key=len, reverse=True):
        if mood in words:
            return mood
    return None
