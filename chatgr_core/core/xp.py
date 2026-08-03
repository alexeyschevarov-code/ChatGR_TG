"""XP, уровни и ачивки (чистое ядро без I/O)."""
from __future__ import annotations

from chatgr_core.core.content import ACHIEVEMENT_NAMES, XP_PER_LEVEL


def level_from_xp(xp: int) -> int:
    return max(1, 1 + int(xp) // XP_PER_LEVEL)


def xp_to_next(xp: int, level: int | None = None) -> int:
    level = level if level is not None else level_from_xp(xp)
    return max(0, level * XP_PER_LEVEL - int(xp))


def add_xp(profile: dict, amount: int) -> tuple[dict, list[str]]:
    """
    Начисляет XP в dict-профиле.
    Возвращает (обновлённый_профиль, сообщения_для_пользователя).
    """
    if amount <= 0:
        return profile, []
    notes: list[str] = []
    profile = dict(profile)
    profile.setdefault("xp", 0)
    profile.setdefault("level", 1)
    profile.setdefault("achievements", [])
    old_level = int(profile["level"])
    profile["xp"] = int(profile["xp"]) + amount
    profile["level"] = level_from_xp(profile["xp"])
    if profile["level"] > old_level:
        notes.append(f"🎉 Уровень {profile['level']}! (+{amount} XP)")
    notes.extend(check_progress_achievements(profile))
    return profile, notes


def unlock_achievement(profile: dict, ach_id: str) -> tuple[dict, str | None]:
    profile = dict(profile)
    ach = list(profile.get("achievements") or [])
    if ach_id in ach:
        return profile, None
    ach.append(ach_id)
    profile["achievements"] = ach
    return profile, ACHIEVEMENT_NAMES.get(ach_id, ach_id)


def check_progress_achievements(profile: dict, topic_count: int = 0) -> list[str]:
    notes: list[str] = []
    xp = int(profile.get("xp") or 0)
    for thr, ach_id in ((50, "xp_50"), (200, "xp_200")):
        if xp >= thr:
            profile, title = unlock_achievement(profile, ach_id)
            if title:
                notes.append(f"🏆 {title}")
    if topic_count >= 5:
        profile, title = unlock_achievement(profile, "topic_explorer")
        if title:
            notes.append(f"🏆 {title}")
    coins = int(profile.get("coins") or 0)
    if coins >= 100:
        profile, title = unlock_achievement(profile, "rich")
        if title:
            notes.append(f"🏆 {title}")
    dq = profile.get("daily_quests") or {}
    if dq.get("bonus_claimed"):
        profile, title = unlock_achievement(profile, "quest_day")
        if title:
            notes.append(f"🏆 {title}")
    if int(profile.get("quiz_wins") or 0) >= 10:
        profile, title = unlock_achievement(profile, "quiz_master")
        if title:
            notes.append(f"🏆 {title}")
    return notes
