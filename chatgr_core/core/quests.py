"""Дневные квесты и монеты (чистое ядро)."""
from __future__ import annotations

from datetime import date
from typing import Any

QUEST_KEYS = ("talk_topic", "quiz_win", "guess_win")
QUEST_LABELS = {
    "talk_topic": "Поговорить на любую тему",
    "quiz_win": "Победить в викторине (>50%)",
    "guess_win": "Угадать число",
}
COINS_PER_QUEST = 5
COINS_ALL_BONUS = 10
XP_ALL_BONUS = 15


def today_str() -> str:
    return date.today().isoformat()


def fresh_daily_quests(day: str | None = None) -> dict[str, Any]:
    return {
        "date": day or today_str(),
        "talk_topic": False,
        "quiz_win": False,
        "guess_win": False,
        "bonus_claimed": False,
    }


def ensure_daily_quests(profile: dict) -> dict:
    """Обновляет daily_quests на сегодняшний день."""
    profile = dict(profile)
    dq = dict(profile.get("daily_quests") or {})
    if dq.get("date") != today_str():
        dq = fresh_daily_quests()
    for k in QUEST_KEYS:
        dq.setdefault(k, False)
    dq.setdefault("bonus_claimed", False)
    profile["daily_quests"] = dq
    profile.setdefault("coins", 0)
    return profile


def complete_quest(profile: dict, key: str) -> tuple[dict, list[str]]:
    """Отмечает квест. Возвращает (profile, notes)."""
    if key not in QUEST_KEYS:
        return profile, []
    profile = ensure_daily_quests(profile)
    dq = dict(profile["daily_quests"])
    notes: list[str] = []
    if dq.get(key):
        return profile, notes
    dq[key] = True
    profile["coins"] = int(profile.get("coins") or 0) + COINS_PER_QUEST
    notes.append(f"✅ Квест: {QUEST_LABELS[key]} (+{COINS_PER_QUEST} 🪙)")

    if all(dq.get(k) for k in QUEST_KEYS) and not dq.get("bonus_claimed"):
        dq["bonus_claimed"] = True
        profile["coins"] = int(profile["coins"]) + COINS_ALL_BONUS
        from chatgr_core.core.xp import add_xp

        profile, xp_notes = add_xp(profile, XP_ALL_BONUS)
        notes.append(f"🎁 Все квесты дня! +{COINS_ALL_BONUS} 🪙 +{XP_ALL_BONUS} XP")
        notes.extend(xp_notes)

    profile["daily_quests"] = dq
    return profile, notes


def format_quests_text(profile: dict) -> str:
    profile = ensure_daily_quests(profile)
    dq = profile["daily_quests"]
    lines = [
        "── Дневные квесты ──",
        f"Дата: {dq.get('date')}",
        f"Монеты: {int(profile.get('coins') or 0)} 🪙",
        "",
    ]
    for k in QUEST_KEYS:
        mark = "✅" if dq.get(k) else "⬜"
        lines.append(f"{mark} {QUEST_LABELS[k]}  → +{COINS_PER_QUEST} 🪙")
    if all(dq.get(k) for k in QUEST_KEYS):
        lines.append("")
        lines.append("🔥 Все квесты выполнены! Завтра — новые.")
    else:
        lines.append("")
        lines.append(f"Бонус за все 3: +{COINS_ALL_BONUS} 🪙 и +{XP_ALL_BONUS} XP")
    return "\n".join(lines)
