from chatgr_core.core.quests import complete_quest, ensure_daily_quests, format_quests_text, fresh_daily_quests


def test_fresh_quests():
    dq = fresh_daily_quests("2026-07-30")
    assert dq["date"] == "2026-07-30"
    assert dq["talk_topic"] is False


def test_complete_quest_coins():
    profile = ensure_daily_quests({"xp": 0, "coins": 0, "achievements": []})
    profile, notes = complete_quest(profile, "talk_topic")
    assert profile["daily_quests"]["talk_topic"] is True
    assert profile["coins"] == 5
    assert notes


def test_all_quests_bonus():
    profile = ensure_daily_quests({"xp": 0, "coins": 0, "achievements": []})
    for k in ("talk_topic", "quiz_win", "guess_win"):
        profile, _ = complete_quest(profile, k)
    assert profile["daily_quests"]["bonus_claimed"] is True
    assert profile["coins"] >= 15 + 10  # 3*5 + 10 bonus


def test_format_quests():
    text = format_quests_text({"coins": 0})
    assert "Дневные квесты" in text
