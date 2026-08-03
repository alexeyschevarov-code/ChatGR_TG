"""Магазин за монеты (без нейросети)."""
from __future__ import annotations

from typing import Any

from chatgr_core.core.xp import unlock_achievement

SHOP_ITEMS: dict[str, dict[str, Any]] = {
    "title_tiger": {
        "name": "Титул «Тигр» 🐯",
        "price": 30,
        "desc": "Показывается в профиле",
        "kind": "title",
        "value": "🐯 Тигр",
    },
    "title_legend": {
        "name": "Титул «Легенда» ⭐",
        "price": 50,
        "desc": "Показывается в профиле",
        "kind": "title",
        "value": "⭐ Легенда",
    },
    "emoji_rich": {
        "name": "Эмодзи-пак 🎉",
        "price": 15,
        "desc": "Больше эмодзи в ответах бота",
        "kind": "flag",
        "value": "emoji_rich",
    },
    "guess_plus3": {
        "name": "+3 попытки «угадай» 🎯",
        "price": 20,
        "desc": "Следующая игра «угадай число» — 13 попыток",
        "kind": "consumable",
        "value": "guess_plus3",
    },
    "quiz_reroll": {
        "name": "Реролл квиза 🔄",
        "price": 10,
        "desc": "Запас: +1 бесплатная «ещё раз» после квиза",
        "kind": "consumable",
        "value": "quiz_reroll",
    },
}


def ensure_inventory(profile: dict) -> dict:
    profile = dict(profile)
    inv = dict(profile.get("inventory") or {})
    inv.setdefault("titles", [])
    inv.setdefault("flags", [])
    inv.setdefault("consumables", {})
    inv.setdefault("active_title", None)
    profile["inventory"] = inv
    profile.setdefault("coins", 0)
    return profile


def format_shop(profile: dict) -> str:
    profile = ensure_inventory(profile)
    coins = int(profile.get("coins") or 0)
    lines = [
        "── Магазин ChatGR ──",
        f"Твои монеты: {coins} 🪙",
        "",
        "Купить: «купить ID» (например: купить emoji_rich)",
        "Или кнопка в меню.",
        "",
    ]
    for item_id, item in SHOP_ITEMS.items():
        lines.append(f"• {item_id}")
        lines.append(f"  {item['name']} — {item['price']} 🪙")
        lines.append(f"  {item['desc']}")
        lines.append("")
    inv = profile["inventory"]
    if inv.get("active_title"):
        lines.append(f"Активный титул: {inv['active_title']}")
    if inv.get("flags"):
        lines.append(f"Флаги: {', '.join(inv['flags'])}")
    cons = inv.get("consumables") or {}
    if cons:
        lines.append("Расходники: " + ", ".join(f"{k}×{v}" for k, v in cons.items() if v))
    return "\n".join(lines)


def buy_item(profile: dict, item_id: str) -> tuple[dict, str]:
    profile = ensure_inventory(profile)
    item = SHOP_ITEMS.get(item_id)
    if not item:
        return profile, "Нет такого товара. Смотри «магазин»."
    coins = int(profile.get("coins") or 0)
    price = int(item["price"])
    if coins < price:
        return profile, f"Не хватает монет: нужно {price} 🪙, у тебя {coins}."

    inv = profile["inventory"]
    kind = item["kind"]
    value = item["value"]

    if kind == "title":
        titles = list(inv.get("titles") or [])
        if value in titles:
            return profile, "Этот титул уже куплен. Надень: «титул тигр» / «титул легенда»."
        titles.append(value)
        inv["titles"] = titles
        inv["active_title"] = value
    elif kind == "flag":
        flags = list(inv.get("flags") or [])
        if value in flags:
            return profile, "Уже куплено."
        flags.append(value)
        inv["flags"] = flags
    elif kind == "consumable":
        cons = dict(inv.get("consumables") or {})
        cons[value] = int(cons.get(value) or 0) + 1
        inv["consumables"] = cons
    else:
        return profile, "Неизвестный тип товара."

    profile["coins"] = coins - price
    profile["inventory"] = inv
    profile, title = unlock_achievement(profile, "first_purchase")
    extra = f"\n🏆 {title}" if title else ""
    return profile, f"Куплено: {item['name']} (−{price} 🪙). Осталось {profile['coins']} 🪙.{extra}"


def set_title(profile: dict, which: str) -> tuple[dict, str]:
    profile = ensure_inventory(profile)
    inv = profile["inventory"]
    titles = inv.get("titles") or []
    mapping = {
        "тигр": "🐯 Тигр",
        "легенда": "⭐ Легенда",
    }
    value = mapping.get(which)
    if not value or value not in titles:
        return profile, "Титул не куплен. Смотри «магазин»."
    inv["active_title"] = value
    profile["inventory"] = inv
    return profile, f"Титул надет: {value}"


def has_flag(profile: dict, flag: str) -> bool:
    profile = ensure_inventory(profile)
    return flag in (profile["inventory"].get("flags") or [])


def use_consumable(profile: dict, key: str) -> tuple[dict, bool]:
    profile = ensure_inventory(profile)
    cons = dict(profile["inventory"].get("consumables") or {})
    n = int(cons.get(key) or 0)
    if n <= 0:
        return profile, False
    cons[key] = n - 1
    if cons[key] <= 0:
        cons.pop(key, None)
    profile["inventory"]["consumables"] = cons
    return profile, True
