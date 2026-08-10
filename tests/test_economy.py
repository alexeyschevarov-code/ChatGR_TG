from chatgr_core.core.economy import (
    DAILY_XP_CAP,
    apply_coin_cap,
    apply_xp_cap,
    ensure_economy,
    try_weekly_bonus,
)
from chatgr_core.core.xp import add_xp, level_title


def test_xp_cap():
    p = ensure_economy({"xp": 0, "economy": {"date": "2099-01-01", "xp_gained": DAILY_XP_CAP, "coins_gained": 0}})
    # force today by ensure again after wipe
    p = {"xp": 0, "level": 1, "achievements": [], "economy": {}}
    p, a1, _ = apply_xp_cap(p, 50)
    assert a1 == 50
    p["economy"]["xp_gained"] = DAILY_XP_CAP
    p, a2, note = apply_xp_cap(p, 10)
    assert a2 == 0
    assert note


def test_add_xp_respects_cap():
    p = {"xp": 0, "level": 1, "achievements": [], "economy": {}}
    p, notes = add_xp(p, 1000)
    assert p["xp"] <= DAILY_XP_CAP


def test_weekly_bonus_once():
    p = {"xp": 0, "coins": 0, "achievements": [], "economy": {}}
    p, n1 = try_weekly_bonus(p)
    assert p["coins"] > 0
    p, n2 = try_weekly_bonus(p)
    assert "уже" in n2[0].lower() or "уже" in " ".join(n2).lower()


def test_level_title():
    assert level_title(1) == "Новичок"
    assert "Легенда" in level_title(20)
