from chatgr_core.core.dialog import DialogEngine, _memory_hint, format_memory
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


def test_boo_does_not_continue_youtube():
    eng = DialogEngine()
    state = {
        "last_topic": "ютуб",
        "character": "обычный",
        "recent_msgs": [],
        "topic_counts": {"ютуб": 3},
        "game_state": None,
    }
    r = eng.handle("бу", state=state, profile={})
    assert "YouTube" not in r.text and "ютуб" not in r.text.lower()
    assert "пуг" in r.text.lower() or "🐯" in (r.emoji_burst or "") or "бот" in r.text.lower()


def test_continue_after_game_is_games_not_youtube():
    eng = DialogEngine()
    state = {
        "last_topic": "ютуб",
        "character": "обычный",
        "recent_msgs": [],
        "topic_counts": {"ютуб": 2},
        "game_state": None,
    }
    r = eng.handle("угадай число", state=state, profile={"xp": 0, "coins": 0, "achievements": []})
    assert r.state.get("last_topic") == "игра"
    r2 = eng.handle("стоп", state=r.state, profile=r.profile)
    assert r2.state.get("last_topic") == "игра"
    r3 = eng.handle("продолжи", state=r2.state, profile=r2.profile)
    assert "YouTube" not in r3.text
    assert "игр" in r3.text.lower() or "Minecraft" in r3.text or "стратег" in r3.text.lower()


def test_start_duel_bot_sets_last_topic_game():
    eng = DialogEngine()
    state = {"last_topic": "ютуб", "character": "обычный", "recent_msgs": [], "topic_counts": {}}
    profile = {"xp": 0, "coins": 0, "achievements": []}
    r = eng.start_duel_bot(state, profile)
    assert r.state.get("last_topic") == "игра"


def test_boo_then_continue_not_youtube():
    eng = DialogEngine()
    state = {
        "last_topic": "ютуб",
        "character": "обычный",
        "recent_msgs": [],
        "topic_counts": {"ютуб": 9},
        "game_state": None,
    }
    r = eng.handle("бу", state=state, profile={})
    assert r.state.get("last_topic") != "ютуб"
    r2 = eng.handle("продолжи", state=r.state, profile=r.profile)
    assert "YouTube" not in r2.text
    assert "ютуб" not in r2.text.lower()


def test_continue_eshcho_after_game_not_youtube():
    eng = DialogEngine()
    state = {
        "last_topic": "ютуб",
        "character": "обычный",
        "recent_msgs": [],
        "topic_counts": {"ютуб": 9},
        "game_state": None,
    }
    r = eng.handle("угадай число", state=state, profile={"xp": 0, "coins": 0, "achievements": []})
    r2 = eng.handle("стоп", state=r.state, profile=r.profile)
    r3 = eng.handle("ещё", state=r2.state, profile=r2.profile)
    assert "YouTube" not in r3.text
    assert r2.state.get("last_topic") == "игра"


def test_memory_hint_after_game_no_youtube():
    state = {
        "last_topic": "игра",
        "recent_topics": ["игра"],
        "topic_counts": {"ютуб": 99, "игра": 1},
        "character": "обычный",
    }
    hint = _memory_hint(state)
    assert "YouTube" not in hint
    assert "ютуб" not in hint.lower()
    empty = _memory_hint({"last_topic": None, "topic_counts": {"ютуб": 99}})
    assert empty == ""


def test_war_causes_not_menu_loop():
    eng = DialogEngine()
    r1 = eng.handle("расскажи про войны")
    assert r1.state.get("last_topic") == "война"
    r2 = eng.handle("причины войн", state=r1.state, profile=r1.profile)
    assert r2.state.get("last_topic") == "причины_войны"
    low = r2.text.lower()
    assert "танки, сражения или причины" not in low
    assert any(w in low for w in ("ресурс", "территор", "союз", "причин"))


def test_forget_context_keeps_name_and_xp():
    eng = DialogEngine()
    state = {
        "name": "Лёша",
        "last_topic": "ютуб",
        "recent_topics": ["ютуб", "космос"],
        "recent_msgs": ["привет"],
        "topic_counts": {"ютуб": 5},
        "character": "весёлый",
        "game_state": None,
    }
    profile = {"xp": 42, "coins": 7, "achievements": []}
    r = eng.handle("забудь контекст", state=state, profile=profile)
    assert r.state.get("last_topic") is None
    assert r.state.get("recent_topics") == []
    assert r.state.get("topic_counts") == {}
    assert r.state.get("name") == "Лёша"
    assert r.profile.get("xp") == 42
