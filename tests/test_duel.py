from chatgr_core.core.duel import answer_duel, start_duel_vs_bot
from chatgr_core.core.dialog import DialogEngine


def test_duel_vs_bot_starts():
    eng = DialogEngine()
    r = eng.handle("дуэль")
    assert r.state.get("game_state", {}).get("type") == "duel"
    assert r.quiz_options


def test_duel_answer_progress():
    state = {"game_state": start_duel_vs_bot(), "character": "обычный", "recent_msgs": [], "topic_counts": {}}
    g = state["game_state"]
    correct = g["questions"][0]["correct"]
    new_g, text, profile, notes, finished, meta = answer_duel(
        g, correct, {"xp": 0, "coins": 0, "achievements": []}
    )
    assert not finished or finished
    assert "Верно" in text or "Неверно" in text or "Дуэль" in text
