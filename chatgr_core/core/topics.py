"""Распознавание тем и настроения: фразы, синонимы, контекст, fuzzy (без нейросетей)."""
from __future__ import annotations

import re

from chatgr_core.core.content import (
    MOOD_ALIASES,
    MOOD_RESPONSES,
    PHRASE_TO_TOPIC,
    TOPIC_ROOTS,
)

# Баллы (чем выше — тем надёжнее)
SCORE_PHRASE = 100
SCORE_BIGRAM = 75
SCORE_SYNONYM = 70
SCORE_ROOT = 40
SCORE_FUZZY = 15
SCORE_CONTEXT = 25  # бонус если тема в last/recent

# Синонимы: topic -> слова/фразы
TOPIC_SYNONYMS: dict[str, tuple[str, ...]] = {
    "космос": (
        "вселенная", "галактика", "марс", "юпитер", "сатурн", "nasa", "мкс",
        "астронавт", "комета", "метеор", "нептун", "венера", "меркурий",
        "чёрная дыра", "черная дыра", "орбита", "спутник",
    ),
    "код": (
        "кодинг", "программирование", "разработка", "скриптик", "баг",
        "функция", "переменная", "алгоритм", "github", "гитхаб",
    ),
    "игра": (
        "гейминг", "геймер", "плей", "игровой", "прохождение", "стрим",
        "шутер", "rpg", "ммo", "онлайн-игра", "консоль",
    ),
    "майнкрафт": ("майн", "кубики", "крафт", "крипер", "алмазы", "редстоун"),
    "фильм": ("кино", "кинотеатр", "блокбастер", "премьера", "режиссёр", "режиссер"),
    "сериалы": ("сериалчик", "нетфликс", "netflix", "эпизод", "сезон"),
    "еда": ("кушать", "перекус", "завтрак", "ужин", "обед", "бургер", "суши", "шаурма"),
    "футбол": ("гол", "чемпионат", "месси", "рональдо", "чемпион", "лига"),
    "животные": ("кот", "пёс", "пес", "щенок", "котёнок", "котенок", "хомяк", "попугай"),
    "музыка": ("песня", "трек", "альбом", "концерт", "клип", "плейлист", "spotify"),
    "школа": ("урок", "учитель", "домашка", "контрольная", "класс", "директор", "перемена"),
    "друзья": ("бро", "кореш", "подруга", "компания", "тусовка"),
    "семья": ("родители", "мама", "папа", "брат", "сестра", "бабушка", "дедушка"),
    "технологии": ("гаджет", "айфон", "андроид", "нейросеть", "ии", "ai", "чип"),
    "компьютер": ("комп", "ноут", "клавиатура", "мышка", "монитор", "винда", "windows"),
    "ютуб": ("ролик", "видео", "блогер", "стример", "лайк", "подписка"),
    "мемы": ("мемасик", "прикол", "ржака", "кринж", "вайб"),
    "война": ("фронт", "солдат", "оружие", "армия", "бой"),
    "танк": ("т-34", "тигр", "шерман", "броня"),
    "история": ("прошлое", "эпоха", "империя", "фараон", "рыцарь"),
    "наука": ("эксперимент", "формула", "открытие", "учёный", "ученый"),
    "природа": ("лес", "река", "озеро", "горы", "поход", "палатка"),
    "путешествия": ("отпуск", "чемодан", "самолёт", "пляж", "отель", "тур"),
    "машины": ("тачка", "авто", "мотор", "тюнинг", "гонк"),
    "рисование": ("арт", "скетч", "рисунок", "карандаш", "холст"),
    "спорт": ("тренировка", "качалка", "зарядка", "марафон"),
    "сон": ("выспаться", "бессонница", "подушка", "храп"),
    "выходные": ("уикенд", "суббота", "воскресенье", "отдых"),
    "погода": ("дождь", "снег", "жара", "холод", "туман", "гроза"),
    "книга": ("роман", "рассказ", "автор", "глава", "фэнтези"),
    "ужасы": ("хоррор", "страшное", "крипи", "слэшер"),
    "фантастика": ("sci-fi", "космоопера", "киберпанк"),
    "привет": ("хай", "здарова", "приветик", "салют", "йоу"),
    "дела": ("настроение", "день", "жизнь"),
    "спасибо": ("благодарю", "сенкс", "thanks"),
}


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _bigrams(words: list[str]) -> list[str]:
    if len(words) < 2:
        return []
    return [f"{words[i]} {words[i + 1]}" for i in range(len(words) - 1)]


def _bump(scores: dict[str, int], topic: str, points: int) -> None:
    if topic and points > 0:
        scores[topic] = scores.get(topic, 0) + points


def score_topics(
    user_input: str,
    words: list[str] | None = None,
    *,
    phrase_to_topic=None,
    topic_roots=None,
    synonyms: dict[str, tuple[str, ...]] | None = None,
    last_topic: str | None = None,
    recent_topics: list[str] | None = None,
) -> dict[str, int]:
    text = (user_input or "").lower().strip()
    words = words if words is not None else text.split()
    words = [w.strip(".,!?;:()[]\"'") for w in words if w.strip(".,!?;:()[]\"'")]
    phrases = list(phrase_to_topic if phrase_to_topic is not None else PHRASE_TO_TOPIC)
    roots = list(topic_roots if topic_roots is not None else TOPIC_ROOTS)
    syn_map = synonyms if synonyms is not None else TOPIC_SYNONYMS
    scores: dict[str, int] = {}

    for phrase, topic in phrases:
        if phrase and phrase in text:
            _bump(scores, topic, SCORE_PHRASE + min(len(phrase), 20))

    for bigram in _bigrams(words):
        for phrase, topic in phrases:
            if not phrase:
                continue
            if bigram == phrase:
                _bump(scores, topic, SCORE_BIGRAM)
            elif len(phrase) >= 5 and bigram in phrase:
                _bump(scores, topic, SCORE_BIGRAM - 10)

    for topic, syns in syn_map.items():
        for syn in syns:
            if len(syn) >= 4 and syn in text:
                _bump(scores, topic, SCORE_SYNONYM)
                break
            if syn in words:
                _bump(scores, topic, SCORE_SYNONYM)
                break

    for topic, root_list in roots:
        for root in root_list:
            if root and any(w.startswith(root) for w in words):
                _bump(scores, topic, SCORE_ROOT)
                break

    for word in words:
        if len(word) < 4:
            continue
        for topic, root_list in roots:
            hit = False
            for root in root_list:
                if len(root) < 4 or word.startswith(root):
                    continue
                if levenshtein(word[: len(root)], root) <= 1 or levenshtein(word, root) <= 1:
                    _bump(scores, topic, SCORE_FUZZY)
                    hit = True
                    break
            if hit:
                break

    # контекст: лёгкий бонус недавним темам (не перебивает сильные совпадения)
    if last_topic and last_topic in scores:
        _bump(scores, last_topic, SCORE_CONTEXT)
    for t in recent_topics or []:
        if t and t in scores and t != last_topic:
            _bump(scores, t, SCORE_CONTEXT // 2)

    return scores


def find_topic(
    user_input: str,
    words: list[str] | None = None,
    *,
    last_topic: str | None = None,
    recent_topics: list[str] | None = None,
) -> str | None:
    text = (user_input or "").lower().strip()
    words = words if words is not None else text.split()
    words = [w.strip(".,!?;:()[]\"'") for w in words if w.strip(".,!?;:()[]\"'")]

    age_hints = (
        "когда ты родился", "когда родился", "когда создан",
        "дата создания", "когда тебя создали", "дата рождения",
        "когда ты появился", "когда появился",
    )
    if ("сколько" in words and "лет" in words) or any(h in text for h in age_hints):
        return "возраст"

    # «а про X» / «про X» — если X пустой, оставляем last_topic
    m = re.match(
        r"^(а\s+)?(про|насчёт|насчет|о|об)\s+(.+)$",
        text,
    )
    if m:
        rest = m.group(3).strip()
        if not rest or rest in ("этом", "этом?", "нём", "нем", "ней", "том", "том?"):
            return last_topic
        # ищем тему в хвосте «про чёрные дыры»
        sub = find_topic(rest, last_topic=last_topic, recent_topics=recent_topics)
        if sub:
            return sub
        # если не нашли, но есть контекст — продолжаем его
        if last_topic:
            return last_topic

    scores = score_topics(
        text, words, last_topic=last_topic, recent_topics=recent_topics
    )
    if not scores:
        # короткие follow-up без явной темы → last_topic
        short_follow = {
            "да", "нет", "ок", "окей", "ага", "угу", "ну", "хм", "hmm",
            "ясно", "понял", "понятно", "точно", "может", "наверное",
        }
        if last_topic and (text in short_follow or len(words) <= 2 and text in short_follow):
            return last_topic
        return None

    topic, points = max(scores.items(), key=lambda kv: (kv[1], len(kv[0])))
    if points < SCORE_FUZZY:
        return None
    return topic


def find_mood(words: list[str], user_input: str = "") -> str | None:
    """Настроение по словам и синонимам (MOOD_ALIASES)."""
    text = (user_input or " ".join(words)).lower()
    # длинные фразы / синонимы в тексте
    for alias in sorted(MOOD_ALIASES.keys(), key=len, reverse=True):
        if alias in text:
            return MOOD_ALIASES[alias]
    for w in words:
        w = w.strip(".,!?;:")
        if w in MOOD_ALIASES:
            return MOOD_ALIASES[w]
        if w in MOOD_RESPONSES:
            return w
    return None
