from chatgr_core.core.games import start_quiz
from chatgr_core.core.dialog import DialogEngine


def test_start_quiz_category():
    g = start_quiz(n=5, category="space")
    assert g["type"] == "quiz"
    assert g["category"] == "space"
    assert len(g["questions"]) == 5
    for q in g["questions"]:
        assert q.get("cat") == "space"


def test_quiz_menu_keyboard():
    eng = DialogEngine()
    r = eng.handle("викторина")
    assert r.keyboard == "quiz_cat"
