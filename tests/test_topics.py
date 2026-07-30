from chatgr_core.core.topics import find_mood, find_topic


def test_find_topic_phrase():
    assert find_topic("расскажи про космос") == "космос"


def test_find_topic_root():
    assert find_topic("люблю танки") == "танк"


def test_find_mood():
    assert find_mood(["сегодня", "плохо"]) == "плохо"
    assert find_mood(["всё", "отлично"]) == "отлично"
