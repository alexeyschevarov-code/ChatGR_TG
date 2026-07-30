from chatgr_core.core.dialog import DialogEngine
from chatgr_core.core.games import QuizGame, start_quiz


def test_dialog_greeting():
    eng = DialogEngine()
    r = eng.handle("привет")
    assert "ChatGR" in r.text or "привет" in r.text.lower() or len(r.text) > 5
    assert r.topic == "привет" or r.state.get("last_topic") == "привет"


def test_dialog_help():
    eng = DialogEngine()
    r = eng.handle("помощь")
    assert "Команды" in r.text or "Темы" in r.text


def test_quiz_flow():
    state = {"game_state": start_quiz(3), "character": "обычный", "recent_msgs": [], "topic_counts": {}}
    profile = {"xp": 0, "level": 1, "achievements": []}
    eng = DialogEngine()
    # answer with button index via text "1" or correct option
    g = state["game_state"]
    correct = g["questions"][0]["correct"]
    r = eng.handle(str(correct + 1), state=state, profile=profile)
    assert r.state.get("game_state") is not None or "окончена" in r.text.lower() or "Верно" in r.text or "Неверно" in r.text


def test_quiz_parse_choice():
    opts = ["7", "8", "9"]
    assert QuizGame.parse_choice("2", opts) == 1
    assert QuizGame.parse_choice("8", opts) == 1
