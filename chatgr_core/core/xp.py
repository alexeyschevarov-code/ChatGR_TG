"""XP, уровни, названия уровней, ачивки, дневные лимиты."""
from __future__ import annotations

from chatgr_core.core.content import ACHIEVEMENT_NAMES, XP_PER_LEVEL

# level (min) -> title  (from high to low)
LEVEL_TITLES = (
    (20, "Легенда ChatGR"),
    (15, "Мастер"),
    (10, "Ветеран"),
    (7, "Исследователь"),
    (5, "Игрок"),
    (3, "Ученик"),
    (1, "Новичок"),
)


def level_from_xp(xp: int) -> int:
    return max(1, 1 + int(xp) // XP_PER_LEVEL)


def level_title(level: int) -> str:
    level = max(1, int(level))
    for min_lvl, title in LEVEL_TITLES:
        if level >= min_lvl:
            return title
    return "Новичок"


def xp_to_next(xp: int, level: int | None = None) -> int:
    level = level if level is not None else level_from_xp(xp)
    return max(0, level * XP_PER_LEVEL - int(xp))


def achievements_progress(profile: dict) -> tuple[int, int, int]:
    """unlocked, total, percent."""
    unlocked = len(profile.get("achievements") or [])
    total = max(1, len(ACHIEVEMENT_NAMES))
    pct = min(100, int(100 * unlocked / total))
    return unlocked, total, pct


def add_xp(profile: dict, amount: int) -> tuple[dict, list[str]]:
    if amount <= 0:
        return profile, []
    notes: list[str] = []
    profile = dict(profile)
    profile.setdefault("xp", 0)
    profile.setdefault("level", 1)
    profile.setdefault("achievements", [])

    from chatgr_core.core.economy import apply_xp_cap

    profile, actual, cap_note = apply_xp_cap(profile, amount)
    if actual <= 0:
        return profile, [cap_note] if cap_note else []
    if cap_note:
        notes.append(cap_note)

    old_level = int(profile["level"])
    profile["xp"] = int(profile["xp"]) + actual
    profile["level"] = level_from_xp(profile["xp"])
    if profile["level"] > old_level:
        title = level_title(profile["level"])
        notes.append(f"🎉 Уровень {profile['level']} — {title}! (+{actual} XP)")
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
