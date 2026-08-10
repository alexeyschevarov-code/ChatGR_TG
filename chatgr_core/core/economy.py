"""Баланс: дневные лимиты XP/монет, недельный бонус."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

DAILY_XP_CAP = 80
DAILY_COIN_CAP = 40
WEEKLY_BONUS_COINS = 25
WEEKLY_BONUS_XP = 30


def today_str() -> str:
    return date.today().isoformat()


def week_id(d: date | None = None) -> str:
    d = d or date.today()
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def ensure_economy(profile: dict) -> dict:
    profile = dict(profile)
    eco = dict(profile.get("economy") or {})
    day = today_str()
    if eco.get("date") != day:
        eco = {
            "date": day,
            "xp_gained": 0,
            "coins_gained": 0,
        }
    week = week_id()
    if eco.get("week") != week:
        eco["week"] = week
        eco["week_bonus_claimed"] = False
    eco.setdefault("week_bonus_claimed", False)
    profile["economy"] = eco
    profile.setdefault("coins", 0)
    return profile


def apply_xp_cap(profile: dict, amount: int) -> tuple[dict, int, str | None]:
    """Возвращает (profile, actual_amount, note)."""
    if amount <= 0:
        return profile, 0, None
    profile = ensure_economy(profile)
    eco = profile["economy"]
    gained = int(eco.get("xp_gained") or 0)
    left = max(0, DAILY_XP_CAP - gained)
    if left <= 0:
        return profile, 0, f"⏳ Дневной лимит XP ({DAILY_XP_CAP}) исчерпан."
    actual = min(amount, left)
    eco["xp_gained"] = gained + actual
    profile["economy"] = eco
    note = None
    if actual < amount:
        note = f"⏳ XP урезано до {actual} (лимит {DAILY_XP_CAP}/день)."
    return profile, actual, note


def apply_coin_cap(profile: dict, amount: int) -> tuple[dict, int, str | None]:
    if amount <= 0:
        return profile, 0, None
    profile = ensure_economy(profile)
    eco = profile["economy"]
    gained = int(eco.get("coins_gained") or 0)
    left = max(0, DAILY_COIN_CAP - gained)
    if left <= 0:
        return profile, 0, f"⏳ Дневной лимит монет ({DAILY_COIN_CAP}) исчерпан."
    actual = min(amount, left)
    eco["coins_gained"] = gained + actual
    profile["economy"] = eco
    note = None
    if actual < amount:
        note = f"⏳ Монеты урезаны до {actual} (лимит {DAILY_COIN_CAP}/день)."
    return profile, actual, note


def try_weekly_bonus(profile: dict) -> tuple[dict, list[str]]:
    """Раз в ISO-неделю — бонус (по команде «бонус недели»)."""
    profile = ensure_economy(profile)
    eco = profile["economy"]
    notes: list[str] = []
    if eco.get("week_bonus_claimed"):
        return profile, ["Бонус этой недели уже получен. Загляни на следующей!"]
    eco["week_bonus_claimed"] = True
    profile["economy"] = eco
    profile, c_amt, c_note = apply_coin_cap(profile, WEEKLY_BONUS_COINS)
    profile["coins"] = int(profile.get("coins") or 0) + c_amt
    from chatgr_core.core.xp import add_xp

    profile, xp_notes = add_xp(profile, WEEKLY_BONUS_XP)
    notes.append(f"📅 Недельный бонус: +{c_amt} 🪙")
    notes.extend(xp_notes)
    if c_note:
        notes.append(c_note)
    return profile, notes


def format_economy(profile: dict) -> str:
    profile = ensure_economy(profile)
    eco = profile["economy"]
    return (
        "── Лимиты дня ──\n"
        f"XP сегодня: {eco.get('xp_gained', 0)} / {DAILY_XP_CAP}\n"
        f"Монеты сегодня: {eco.get('coins_gained', 0)} / {DAILY_COIN_CAP}\n"
        f"Неделя: {eco.get('week')} · бонус: "
        f"{'✅' if eco.get('week_bonus_claimed') else '⬜ напиши «бонус недели»'}"
    )
