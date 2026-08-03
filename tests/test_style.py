from chatgr_core.core.style import decorate_text, reaction_emoji


def test_decorate():
    t = decorate_text("Привет мир", topic="привет", rich=True)
    assert "Привет" in t
    assert len(t) > len("Привет мир")


def test_reaction():
    assert reaction_emoji("win")
    assert reaction_emoji("ok")
