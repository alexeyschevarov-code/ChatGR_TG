"""Движок диалога — ChatGR 0.8.0 beta (без нейросети)."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from chatgr_core.core.content import (
    CHARACTER_ALIASES,
    CHARACTER_LABELS,
    CONTINUE_HINTS,
    CONTINUE_PHRASES,
    MODE_FALLBACKS,
    MODE_OVERRIDES,
    MOOD_RESPONSES,
    PARROT_LIMIT,
    PARROT_REPLIES,
    QUIZ_CATEGORIES,
    QUIZ_START_EXACT,
    QUIZ_START_PHRASES,
    RESPONSES,
    SPAM_SOFT_BAN_HITS,
    TOPIC_GROUPS,
    TOPIC_NAMES,
    VERSION,
    XP_CONTINUE,
    XP_MOOD,
    XP_TOPIC,
)
from chatgr_core.core.duel import (
    answer_duel,
    create_friend_duel,
    duel_question_text,
    start_duel_vs_bot,
)
from chatgr_core.core.games import GuessGame, QuizGame, start_guess, start_quiz
from chatgr_core.core.quests import complete_quest, ensure_daily_quests, format_quests_text
from chatgr_core.core.changelog import format_changelog
from chatgr_core.core.economy import format_economy, try_weekly_bonus
from chatgr_core.core.facts import format_daily_fact
from chatgr_core.core.shop import buy_item, ensure_inventory, format_shop, has_flag, set_title, use_consumable
from chatgr_core.core.style import decorate_text, reaction_emoji
from chatgr_core.core.topics import find_mood, find_topic
from chatgr_core.core.xp import (
    achievements_progress,
    add_xp,
    check_progress_achievements,
    level_from_xp,
    level_title,
    xp_to_next,
)


@dataclass
class DialogResult:
    text: str
    state: dict[str, Any]
    profile: dict[str, Any]
    topic: str | None = None
    keyboard: str | None = None
    quiz_options: list[str] | None = None
    save: bool = True
    quest_event: str | None = None
    # 0.8
    emoji_burst: str | None = None  # отдельное сообщение-эмодзи
    duel_meta: dict | None = None  # для синхронизации дружеской дуэли


def default_state() -> dict[str, Any]:
    return {
        "character": "обычный",
        "last_topic": None,
        "recent_topics": [],  # последние 5 тем для контекста
        "game_state": None,
        "name": None,
        "recent_msgs": [],
        "topic_counts": {},
        "spam_hits": 0,
        "session_msgs": 0,
        "session_xp": 0,
        "onboarding_step": 0,  # 0 done, 1 name, 2 quest, 3 quiz hint
    }


def _push_topic(state: dict, topic: str | None) -> None:
    if not topic or topic == "настроение":
        return
    state["last_topic"] = topic
    recent = [t for t in (state.get("recent_topics") or []) if t != topic]
    recent.insert(0, topic)
    state["recent_topics"] = recent[:5]


def default_profile() -> dict[str, Any]:
    return {
        "favorite_game": None,
        "hobby": None,
        "favorite_topic": None,
        "age": None,
        "profile_complete": False,
        "xp": 0,
        "level": 1,
        "coins": 0,
        "quiz_wins": 0,
        "achievements": [],
        "daily_quests": {},
        "reminders": {"enabled": False, "hour": 10},
        "inventory": {},
        "economy": {},
        "onboarding_done": False,
    }


def _active_pool(character: str) -> dict:
    pool = dict(RESPONSES)
    pool.update(MODE_OVERRIDES.get(character, {}))
    return pool


def _pick(pool: dict, key: str, last_answers: dict) -> str:
    options = pool.get(key) or ["..."]
    last = last_answers.get(key)
    available = [o for o in options if o != last] or list(options)
    choice = random.choice(available)
    last_answers[key] = choice
    return choice


def top_topics(state: dict, limit: int = 3) -> list[tuple[str, int]]:
    counts = state.get("topic_counts") or {}
    return sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]


def format_memory(state: dict) -> str:
    lines = ["── Память ChatGR ──", ""]
    if state.get("name"):
        lines.append(f"Тебя зовут: {state['name']}")
    else:
        lines.append("Имя не знаю. Напиши: меня зовут …")
    lt = state.get("last_topic")
    if lt:
        lines.append(f"Последняя тема: {TOPIC_NAMES.get(lt, lt)}")
    top = top_topics(state, 5)
    lines.append("")
    lines.append("Топ тем:")
    if top:
        for i, (t, c) in enumerate(top, 1):
            lines.append(f"  {i}. {TOPIC_NAMES.get(t, t)} — {c}")
    else:
        lines.append("  Пока пусто — поболтай!")
    return "\n".join(lines)


def format_session(state: dict, profile: dict) -> str:
    return (
        "── Сессия ──\n"
        f"Сообщений: {int(state.get('session_msgs') or 0)}\n"
        f"Монеты: {int(profile.get('coins') or 0)} 🪙\n"
        f"XP всего: {int(profile.get('xp') or 0)}\n"
        f"Уровень: {level_from_xp(int(profile.get('xp') or 0))}"
    )


def format_profile(state: dict, profile: dict) -> str:
    profile = ensure_daily_quests(ensure_inventory(profile))
    lines = ["── Твой профиль ──", ""]
    inv = profile.get("inventory") or {}
    if inv.get("active_title"):
        lines.append(f"Титул: {inv['active_title']}")
    if state.get("name"):
        lines.append(f"Имя: {state['name']}")
    xp = int(profile.get("xp") or 0)
    level = level_from_xp(xp)
    lines.append(f"Уровень: {level} — {level_title(level)}")
    lines.append(f"XP: {xp} (до следующего: {xp_to_next(xp, level)})")
    lines.append(f"Монеты: {int(profile.get('coins') or 0)} 🪙")
    u, t, pct = achievements_progress(profile)
    lines.append(f"Ачивки: {u}/{t} ({pct}%)")
    lines.append(f"Побед в викторине: {int(profile.get('quiz_wins') or 0)}")
    lines.append(f"Любимая игра: {profile.get('favorite_game') or '—'}")
    lines.append(f"Хобби: {profile.get('hobby') or '—'}")
    rem = profile.get("reminders") or {}
    lines.append(f"Напоминания: {'вкл' if rem.get('enabled') else 'выкл'}")
    ach = profile.get("achievements") or []
    lines.append("")
    lines.append("── Ачивки ──")
    if ach:
        from chatgr_core.core.content import ACHIEVEMENT_NAMES

        for a in ach:
            lines.append(f"  🏆 {ACHIEVEMENT_NAMES.get(a, a)}")
    else:
        lines.append("  Пока пусто!")
    lines.append("")
    lines.append(format_economy(profile))
    return "\n".join(lines)


def format_help(state: dict) -> str:
    char = state.get("character", "обычный")
    lines = [f"Я ChatGR v{VERSION} — режим: {CHARACTER_LABELS.get(char, char)}", ""]
    lines.append("Темы:")
    for group, keys in TOPIC_GROUPS.items():
        names = [TOPIC_NAMES.get(k, k) for k in keys]
        lines.append(f"  {group}: {', '.join(names)}")
    lines += [
        "",
        "Команды:",
        "  помощь | профиль | память | квесты | сессия | факт",
        "  магазин | купить ID | дуэль | что нового | экспорт",
        "  бонус недели | режим | играть | викторина | рекорды",
        "  напомни / стоп напоминаний",
        "",
        "Монеты → магазин. Есть дневные лимиты XP/монет.",
    ]
    return "\n".join(lines)


def _memory_hint(state: dict) -> str:
    if random.random() > 0.25:
        return ""
    top = top_topics(state, 1)
    if top:
        return f"\n(Кстати, ты часто говоришь про {TOPIC_NAMES.get(top[0][0], top[0][0])}.)"
    if state.get("name") and random.random() < 0.5:
        return f"\n(Помню тебя, {state['name']}!)"
    return ""


def _style(text: str, profile: dict, topic: str | None = None) -> str:
    rich = has_flag(profile, "emoji_rich")
    return decorate_text(text, topic=topic, rich=rich or random.random() < 0.4)


class DialogEngine:
    def handle(
        self,
        user_input: str,
        state: dict | None = None,
        profile: dict | None = None,
        last_answers: dict | None = None,
    ) -> DialogResult:
        state = {**default_state(), **(state or {})}
        profile = ensure_inventory(
            ensure_daily_quests({**default_profile(), **(profile or {})})
        )
        last_answers = last_answers if last_answers is not None else {}
        user_input = (user_input or "").lower().strip()
        words = user_input.split()

        recent = list(state.get("recent_msgs") or [])
        recent.append(user_input)
        state["recent_msgs"] = recent[-10:]
        state["session_msgs"] = int(state.get("session_msgs") or 0) + 1

        if not user_input:
            return DialogResult("Напиши хоть что-нибудь! ✍️", state, profile)

        # ---- onboarding steps 1–3 ----
        step = int(state.get("onboarding_step") or 0)
        if step == 1:
            if "меня зовут" in user_input:
                rest = user_input.split("меня зовут", 1)[1].strip(" .,!?")
                if rest:
                    state["name"] = rest.split()[0].capitalize()
            elif len(words) == 1 and words[0].isalpha() and len(words[0]) > 1:
                state["name"] = words[0].capitalize()
            if state.get("name"):
                state["onboarding_step"] = 2
                return DialogResult(
                    f"Приятно, {state['name']}! 🐯\n\n"
                    f"<b>Шаг 2/3</b> — открой квесты: напиши <b>квесты</b>.",
                    state,
                    profile,
                )
            return DialogResult(
                "Напиши имя: <b>меня зовут …</b> или одно слово.",
                state,
                profile,
            )
        if step == 2:
            if "квест" in user_input or user_input in ("задания", "daily"):
                state["onboarding_step"] = 3
                return DialogResult(
                    format_quests_text(profile)
                    + "\n\n<b>Шаг 3/3</b> — напиши <b>викторина</b>.",
                    state,
                    profile,
                )
            return DialogResult("Сначала: <b>квесты</b> 📋", state, profile)
        if step == 3:
            if "викторин" in user_input or user_input in ("квиз", "quiz"):
                state["onboarding_step"] = 0
                profile["onboarding_done"] = True
                return DialogResult(
                    "Онбординг готов! 🎉 Выбери категорию:",
                    state,
                    profile,
                    keyboard="quiz_cat",
                )
            return DialogResult("Почти! Напиши <b>викторина</b> 📚", state, profile)

        if (
            user_input not in (
                "помощь", "квесты", "память", "магазин", "сессия",
                "факт", "экспорт", "что нового",
            )
            and len(recent) >= PARROT_LIMIT
            and all(m == user_input for m in recent[-PARROT_LIMIT:])
        ):
            state["spam_hits"] = int(state.get("spam_hits") or 0) + 1
            if state["spam_hits"] >= SPAM_SOFT_BAN_HITS:
                return DialogResult("⛔ Слишком много спама. Напиши что-то новое.", state, profile)
            return DialogResult(random.choice(PARROT_REPLIES), state, profile)

        # ---- active game / duel ----
        gstate = state.get("game_state")
        if gstate:
            if user_input in ("стоп", "выход", "хватит"):
                state["game_state"] = None
                return DialogResult("Игра окончена. 👋", state, profile)

            if gstate.get("type") == "duel":
                opts = list(gstate["questions"][gstate["index"]]["options"])
                choice = QuizGame.parse_choice(user_input, opts)
                if choice is None:
                    return DialogResult(
                        "Ответь 1–3 или кнопкой. «стоп» — выход.",
                        state,
                        profile,
                        keyboard="quiz",
                        quiz_options=opts,
                    )
                new_g, text, profile, _, finished, meta = answer_duel(gstate, choice, profile)
                state["game_state"] = new_g
                return DialogResult(
                    text,
                    state,
                    profile,
                    keyboard=None if finished else "quiz",
                    quiz_options=None if finished else (
                        list(new_g["questions"][new_g["index"]]["options"]) if new_g else None
                    ),
                    emoji_burst=reaction_emoji("win" if finished and "🏆" in text else "ok") if finished else None,
                    duel_meta=meta,
                )

            if gstate.get("type") == "quiz":
                opts = QuizGame.options(gstate)
                choice = QuizGame.parse_choice(user_input, opts)
                if choice is None:
                    return DialogResult(
                        "Ответь 1–3 или кнопкой.",
                        state,
                        profile,
                        keyboard="quiz",
                        quiz_options=opts,
                    )
                new_g, text, profile, _, finished = QuizGame.answer(gstate, choice, profile)
                state["game_state"] = new_g
                kb = None if finished else "quiz"
                if finished:
                    kb = "quiz_again"
                return DialogResult(
                    text,
                    state,
                    profile,
                    keyboard=kb,
                    quiz_options=None if finished else (QuizGame.options(new_g) if new_g else None),
                    emoji_burst=reaction_emoji("win") if finished and "🎉" in text else None,
                )

            new_g, text, profile, _ = GuessGame.handle(gstate, user_input, profile)
            state["game_state"] = new_g
            return DialogResult(
                text,
                state,
                profile,
                emoji_burst=reaction_emoji("win") if new_g is None and "🎉" in text else None,
            )

        # ---- commands ----
        if user_input in ("помощь", "команды", "что ты умеешь"):
            return DialogResult(format_help(state), state, profile)

        if user_input in ("что нового", "новости", "changelog", "что нового?"):
            return DialogResult(format_changelog(), state, profile)

        if user_input in ("факт", "факт дня", "интересный факт"):
            return DialogResult(
                format_daily_fact(state.get("last_topic")),
                state,
                profile,
            )

        if user_input in ("бонус недели", "недельный бонус"):
            profile, notes = try_weekly_bonus(profile)
            return DialogResult("\n".join(notes), state, profile)

        if user_input in ("экспорт", "export", "выгрузка"):
            # handler will detect and send as file; here mark
            state["_export"] = True
            return DialogResult("Готовлю экспорт профиля…", state, profile)

        if user_input in ("мой профиль", "профиль", "покажи профиль"):
            return DialogResult(format_profile(state, profile), state, profile)

        if user_input in ("сессия", "статистика сессии", "статистика"):
            return DialogResult(
                format_session(state, profile) + "\n\n" + format_economy(profile),
                state,
                profile,
            )

        if user_input in ("квесты", "квест", "задания", "daily"):
            return DialogResult(format_quests_text(profile), state, profile)

        if user_input in ("магазин", "shop", "магаз"):
            return DialogResult(format_shop(profile), state, profile, keyboard="shop")

        if user_input.startswith("купить "):
            item_id = user_input.split("купить ", 1)[1].strip()
            profile, msg, ok = buy_item(profile, item_id)
            if ok:
                state["_purchase"] = item_id
            return DialogResult(msg, state, profile, keyboard="shop")

        if user_input.startswith("титул "):
            which = user_input.split("титул ", 1)[1].strip()
            profile, msg = set_title(profile, which)
            return DialogResult(msg, state, profile)

        if user_input in ("память", "о чём мы говорили", "о чем мы говорили", "что ты помнишь"):
            return DialogResult(format_memory(state), state, profile)

        if user_input in ("как меня зовут", "моё имя", "мое имя", "помнишь меня"):
            if state.get("name"):
                return DialogResult(f"Конечно — тебя зовут {state['name']}! 🐯", state, profile)
            return DialogResult("Имя не знаю. Напиши: меня зовут …", state, profile)

        if user_input in ("напомни", "напоминания", "включи напоминания"):
            rem = dict(profile.get("reminders") or {})
            rem["enabled"] = True
            rem.setdefault("hour", 10)
            profile["reminders"] = rem
            return DialogResult("Ок! Напоминания вкл. Выкл: «стоп напоминаний».", state, profile)

        if user_input in ("стоп напоминаний", "выкл напоминания", "не напоминай"):
            rem = dict(profile.get("reminders") or {})
            rem["enabled"] = False
            profile["reminders"] = rem
            return DialogResult("Напоминания выключены.", state, profile)

        # duel
        if user_input in ("дуэль", "дуель", "duel"):
            state["game_state"] = start_duel_vs_bot()
            text = "⚔️ Дуэль против бота!\n\n" + duel_question_text(state["game_state"])
            opts = list(state["game_state"]["questions"][0]["options"])
            return DialogResult(text, state, profile, keyboard="quiz", quiz_options=opts)

        if user_input.startswith("дуэль ") or user_input.startswith("duel "):
            part = user_input.split(maxsplit=1)[1].strip().upper()
            if part in ("БОТ", "BOT"):
                state["game_state"] = start_duel_vs_bot()
                text = "⚔️ Дуэль vs бот!\n\n" + duel_question_text(state["game_state"])
                opts = list(state["game_state"]["questions"][0]["options"])
                return DialogResult(text, state, profile, keyboard="quiz", quiz_options=opts)
            if part in ("ДРУГ", "FRIEND", "СОЗДАТЬ"):
                code, dstate = create_friend_duel(state.get("name") or "host")
                dstate["host_id"] = dstate.get("host_id")  # filled by service
                state["game_state"] = dstate
                state["_pending_duel_create"] = True
                return DialogResult(
                    f"⚔️ Дуэль создана!\nКод: <b>{code}</b>\n"
                    f"Друг пишет: дуэль {code}\n"
                    f"Потом оба отвечают на вопросы.",
                    state,
                    profile,
                    duel_meta={"action": "create", "code": code, "payload": dstate},
                )
            # join by code
            state["_pending_duel_join"] = part
            return DialogResult(
                f"Пробую войти в дуэль {part}…",
                state,
                profile,
                duel_meta={"action": "join", "code": part},
                save=True,
            )

        if user_input.startswith("режим"):
            parts = user_input.split()
            if len(parts) == 1:
                return DialogResult(
                    f"Сейчас: {CHARACTER_LABELS.get(state['character'], state['character'])}.",
                    state,
                    profile,
                    keyboard="mode",
                )
            mode = CHARACTER_ALIASES.get(parts[-1])
            if mode:
                state["character"] = mode
                return DialogResult(f"Режим: {CHARACTER_LABELS[mode]}. ✨", state, profile)
            return DialogResult("Неизвестный режим.", state, profile, keyboard="mode")

        if user_input in ("играть", "мини-игра", "игры"):
            return DialogResult("Выбери игру:", state, profile, keyboard="play")

        if user_input in ("угадай число", "угадай"):
            max_att = 10
            profile, used = use_consumable(profile, "guess_plus3")
            if used:
                max_att = 13
            state["game_state"] = start_guess(max_attempts=max_att)
            extra = " (буст +3 попытки!)" if used else ""
            return DialogResult(
                f"Загадал 1–100. {max_att} попыток{extra}. «стоп» — выход. 🎯",
                state,
                profile,
            )

        if user_input in QUIZ_START_EXACT or any(p in user_input for p in QUIZ_START_PHRASES):
            return DialogResult("Выбери категорию викторины:", state, profile, keyboard="quiz_cat")

        for cat, label in QUIZ_CATEGORIES.items():
            if f"викторина {label.lower()}" in user_input or f"квиз {label.lower()}" in user_input:
                return self.start_quiz_session(state, profile, category=cat)
            if f"викторина {cat}" in user_input:
                return self.start_quiz_session(state, profile, category=cat)

        if "меня зовут" in user_input:
            rest = user_input.split("меня зовут", 1)[1].strip(" .,!?")
            if rest:
                state["name"] = rest.split()[0].capitalize()
                return DialogResult(f"Приятно, {state['name']}! Запомнил. 🐯", state, profile)

        if any(p in user_input for p in CONTINUE_PHRASES) and state.get("last_topic"):
            lt = state["last_topic"]
            pool = _active_pool(state["character"])
            if lt in pool:
                extra = _pick(pool, lt, last_answers)
                hint = CONTINUE_HINTS.get(lt, "")
                profile, notes = add_xp(profile, XP_CONTINUE)
                text = _style(
                    f"Продолжаем про {TOPIC_NAMES.get(lt, lt)}. {extra}\n{hint}",
                    profile,
                    lt,
                )
                text += _memory_hint(state)
                if notes:
                    text += "\n" + "\n".join(notes)
                return DialogResult(text, state, profile, topic=lt)

        mood = find_mood(words, user_input)
        if mood:
            ans = _pick(MOOD_RESPONSES, mood, last_answers)
            profile, notes = add_xp(profile, XP_MOOD)
            text = _style(ans, profile, "настроение") + _memory_hint(state)
            if notes:
                text += "\n" + "\n".join(notes)
            return DialogResult(
                text, state, profile, topic="настроение",
                emoji_burst=reaction_emoji("ok") if random.random() < 0.3 else None,
            )

        recent_topics = list(state.get("recent_topics") or [])
        topic = find_topic(
            user_input,
            words,
            last_topic=state.get("last_topic"),
            recent_topics=recent_topics,
        )
        if topic:
            _push_topic(state, topic)
            counts = dict(state.get("topic_counts") or {})
            counts[topic] = counts.get(topic, 0) + 1
            state["topic_counts"] = counts
            pool = _active_pool(state["character"])
            ans = _pick(pool, topic, last_answers) if topic in pool else MODE_FALLBACKS["обычный"]
            profile, notes = add_xp(profile, XP_TOPIC)
            notes.extend(check_progress_achievements(profile, topic_count=len(counts)))
            profile, qnotes = complete_quest(profile, "talk_topic")
            notes.extend(qnotes)
            if state.get("name") and random.random() < 0.3:
                ans = f"{state['name']}, {ans[0].lower()}{ans[1:]}"
            # если это продолжение контекста «а про…» — чуть яснее
            if user_input.startswith("а про") or user_input.startswith("про "):
                label = TOPIC_NAMES.get(topic, topic)
                ans = f"Ок, про {label}. {ans}"
            text = _style(ans, profile, topic) + _memory_hint(state)
            if notes:
                text += "\n" + "\n".join(notes)
            burst = reaction_emoji("ok") if random.random() < 0.35 else None
            return DialogResult(
                text, state, profile, topic=topic, quest_event="talk_topic", emoji_burst=burst
            )

        char = state.get("character", "обычный")
        lt = state.get("last_topic")
        if lt:
            label = TOPIC_NAMES.get(lt, lt)
            return DialogResult(
                f"Не совсем понял 🤔 Мы про {label} — напиши «продолжи», "
                f"«а про …» (например «а про луну») или «помощь».",
                state,
                profile,
            )
        return DialogResult(
            _style(MODE_FALLBACKS.get(char, MODE_FALLBACKS["обычный"]), profile),
            state,
            profile,
        )

    def set_mode(self, state: dict, mode: str) -> DialogResult:
        state = {**default_state(), **state}
        if mode not in CHARACTER_LABELS:
            return DialogResult("Неизвестный режим.", state, default_profile())
        state["character"] = mode
        return DialogResult(f"Режим: {CHARACTER_LABELS[mode]}. ✨", state, default_profile())

    def start_quiz_session(
        self, state: dict, profile: dict, category: str = "mixed"
    ) -> DialogResult:
        state = {**default_state(), **state}
        profile = ensure_inventory(ensure_daily_quests({**default_profile(), **profile}))
        state["game_state"] = start_quiz(category=category)
        text = QuizGame.current_question(state["game_state"])
        opts = QuizGame.options(state["game_state"])
        label = QUIZ_CATEGORIES.get(category, category)
        return DialogResult(
            f"📚 Категория: {label}\n\n{text}\n\nЖми кнопку:",
            state,
            profile,
            keyboard="quiz",
            quiz_options=opts,
        )

    def quiz_callback(self, state: dict, profile: dict, choice: int) -> DialogResult:
        state = {**default_state(), **state}
        profile = ensure_inventory(ensure_daily_quests({**default_profile(), **profile}))
        gstate = state.get("game_state")
        if not gstate:
            return DialogResult("Нет активной игры.", state, profile)
        if gstate.get("type") == "duel":
            new_g, text, profile, _, finished, meta = answer_duel(gstate, choice, profile)
            state["game_state"] = new_g
            return DialogResult(
                text,
                state,
                profile,
                keyboard=None if finished else "quiz",
                quiz_options=None if finished else (
                    list(new_g["questions"][new_g["index"]]["options"]) if new_g else None
                ),
                duel_meta=meta,
            )
        if gstate.get("type") != "quiz":
            return DialogResult("Викторина не активна.", state, profile)
        new_g, text, profile, _, finished = QuizGame.answer(gstate, choice, profile)
        state["game_state"] = new_g
        return DialogResult(
            text,
            state,
            profile,
            keyboard="quiz_again" if finished else "quiz",
            quiz_options=None if finished else (QuizGame.options(new_g) if new_g else None),
            emoji_burst=reaction_emoji("win") if finished else None,
        )

    def start_duel_bot(self, state: dict, profile: dict) -> DialogResult:
        state = {**default_state(), **state}
        profile = ensure_inventory({**default_profile(), **profile})
        state["game_state"] = start_duel_vs_bot()
        text = "⚔️ Дуэль против бота!\n\n" + duel_question_text(state["game_state"])
        opts = list(state["game_state"]["questions"][0]["options"])
        return DialogResult(text, state, profile, keyboard="quiz", quiz_options=opts)
