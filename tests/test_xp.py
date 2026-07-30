from chatgr_core.core.xp import add_xp, level_from_xp, unlock_achievement


def test_level_from_xp():
    assert level_from_xp(0) == 1
    assert level_from_xp(99) == 1
    assert level_from_xp(100) == 2
    assert level_from_xp(250) == 3


def test_add_xp_level_up():
    profile = {"xp": 95, "level": 1, "achievements": []}
    profile, notes = add_xp(profile, 10)
    assert profile["xp"] == 105
    assert profile["level"] == 2
    assert any("Уровень" in n for n in notes)


def test_unlock_achievement_once():
    profile = {"achievements": []}
    profile, title = unlock_achievement(profile, "first_quiz")
    assert title is not None
    profile, title2 = unlock_achievement(profile, "first_quiz")
    assert title2 is None
    assert profile["achievements"] == ["first_quiz"]
