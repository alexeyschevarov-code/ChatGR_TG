from chatgr_core.core.dialog import DialogEngine, format_memory


def test_memory_command():
    eng = DialogEngine()
    state = {
        "name": "Лёша",
        "topic_counts": {"космос": 5, "игра": 2},
        "last_topic": "космос",
        "character": "обычный",
        "recent_msgs": [],
    }
    r = eng.handle("память", state=state, profile={})
    assert "Лёша" in r.text
    assert "космос" in r.text.lower() or "Космос" in r.text or "космос" in format_memory(state).lower()


def test_memory_after_game_current_is_game_not_youtube():
    state = {
        "name": "Лёша",
        "last_topic": "игра",
        "recent_topics": ["игра"],
        "topic_counts": {"ютуб": 12, "игра": 1},
        "character": "обычный",
        "recent_msgs": [],
    }
    text = format_memory(state)
    # текущая тема — игра, не YouTube
    current = text.split("Часто")[0]
    assert "игр" in current.lower()
    assert "YouTube" not in current
    # lifetime list may still mention YouTube as «часто»
    assert "Часто" in text


def test_name_recall():
    eng = DialogEngine()
    r1 = eng.handle("меня зовут Лёша")
    assert "Лёша" in r1.text
    r2 = eng.handle("как меня зовут", state=r1.state, profile=r1.profile)
    assert "Лёша" in r2.text
