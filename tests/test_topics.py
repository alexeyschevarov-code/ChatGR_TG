from chatgr_core.core.topics import find_mood, find_topic, score_topics


def test_find_topic_phrase():
    assert find_topic("расскажи про космос") == "космос"


def test_find_topic_root():
    assert find_topic("люблю танки") == "танк"


def test_find_mood():
    assert find_mood(["сегодня", "плохо"]) == "плохо"
    assert find_mood(["всё", "отлично"]) == "отлично"


def test_mood_synonyms():
    assert find_mood([], "мне грустно") == "плохо"
    assert find_mood([], "день огонь") == "супер"
    assert find_mood(["устал"]) == "плохо"
    assert find_mood([], "так себе") == "норм"


def test_synonym_space():
    assert find_topic("расскажи про вселенную") == "космос"
    assert find_topic("интересны чёрные дыры") == "космос"


def test_synonym_school():
    assert find_topic("опять домашка") == "школа"


def test_more_phrases():
    assert find_topic("как жизнь") == "дела"
    assert find_topic("учу python") == "код"
    assert find_topic("смотрю нетфликс") in ("сериалы", "фильм")


def test_context_apro():
    # «а про луну» после космоса
    t = find_topic("а про луну", last_topic="космос", recent_topics=["космос"])
    assert t == "космос"


def test_context_short_followup():
    # короткое «да» без темы — не всегда last, но «про этом» да
    t = find_topic("про этом", last_topic="игра", recent_topics=["игра"])
    assert t == "игра"


def test_scoring_prefers_phrase():
    s = score_topics("расскажи про космос")
    assert s.get("космос", 0) >= 100
