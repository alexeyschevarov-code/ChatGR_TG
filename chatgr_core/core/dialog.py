"""Движок диалога — без Telegram и без файлов (только dict-состояние)."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
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
    QUIZ_START_EXACT,
    QUIZ_START_PHRASES,
    RESPONSES,
    TOPIC_GROUPS,
    TOPIC_NAMES,
    VERSION,
    XP_CONTINUE,
    XP_MOOD,
    XP_TOPIC,
)
from chatgr_core.core.games import GuessGame, QuizGame, start_guess, start_quiz
from chatgr_core.core.topics import find_mood, find_topic
from chatgr_core.core.xp import add_xp, level_from_xp, xp_to_next


@dataclass
class DialogResult:
    text: str
    state: dict[str, Any]
    profile: dict[str, Any]
    topic: str | None = None
    keyboard: str | None = None  # "mode" | "play" | "quiz" | None
    quiz_options: list[str] | None = None
    save: bool = True


def default_state() -> dict[str, Any]:
    return {
        "character": "обычный",
        "last_topic": None,
        "game_state": None,
        "name": None,
        "recent_msgs": [],
        "topic_counts": {},
    }


def default_profile() -> dict[str, Any]:
    return {
        "favorite_game": None,
        "hobby": None,
        "favorite_topic": None,
        "age": None,
        "profile_complete": False,
        "xp": 0,
        "level": 1,
        "achievements": [],
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


def format_profile(state: dict, profile: dict) -> str:
    lines = ["── Твой профиль ──", ""]
    if state.get("name"):
        lines.append(f"Имя: {state['name']}")
    xp = int(profile.get("xp") or 0)
    level = level_from_xp(xp)
    lines.append(f"Уровень: {level}")
    lines.append(f"XP: {xp} (до следующего: {xp_to_next(xp, level)})")
    lines.append(f"Любимая игра: {profile.get('favorite_game') or '—'}")
    lines.append(f"Хобби: {profile.get('hobby') or '—'}")
    fav = profile.get("favorite_topic")
    lines.append(f"Любимая тема: {TOPIC_NAMES.get(fav, fav) if fav else '—'}")
    ach = profile.get("achievements") or []
    lines.append("")
    lines.append("── Ачивки ──")
    if ach:
        from chatgr_core.core.content import ACHIEVEMENT_NAMES

        for a in ach:
            lines.append(f"  🏆 {ACHIEVEMENT_NAMES.get(a, a)}")
    else:
        lines.append("  Пока пусто. Сыграй в викторину!")
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
        "Команды: помощь, статистика, профиль, режим, играть, викторина, рекорды",
        "XP за общение, игры и викторину.",
    ]
    return "\n".join(lines)


class DialogEngine:
    """Обрабатывает одно текстовое сообщение пользователя."""

    def handle(
        self,
        user_input: str,
        state: dict | None = None,
        profile: dict | None = None,
        last_answers: dict | None = None,
    ) -> DialogResult:
        state = {**default_state(), **(state or {})}
        profile = {**default_profile(), **(profile or {})}
        last_answers = last_answers if last_answers is not None else {}
        user_input = (user_input or "").lower().strip()
        words = user_input.split()

        recent = list(state.get("recent_msgs") or [])
        recent.append(user_input)
        if len(recent) > 10:
            recent = recent[-10:]
        state["recent_msgs"] = recent

        if not user_input:
            return DialogResult("Напиши хоть что-нибудь!", state, profile)

        # parrot
        if (
            user_input not in ("помощь", "статистика", "история")
            and len(recent) >= PARROT_LIMIT
            and all(m == user_input for m in recent[-PARROT_LIMIT:])
        ):
            return DialogResult(random.choice(PARROT_REPLIES), state, profile)

        # active game
        gstate = state.get("game_state")
        if gstate:
            if user_input in ("стоп", "выход", "хватит"):
                state["game_state"] = None
                return DialogResult("Игра окончена.", state, profile)
            if gstate.get("type") == "quiz":
                opts = QuizGame.options(gstate)
                choice = QuizGame.parse_choice(user_input, opts)
                if choice is None:
                    return DialogResult(
                        "Ответь цифрой 1–3 или кнопкой. «стоп» — выход.",
                        state,
                        profile,
                        keyboard="quiz",
                        quiz_options=opts,
                    )
                new_g, text, profile, _, finished = QuizGame.answer(gstate, choice, profile)
                state["game_state"] = new_g
                return DialogResult(
                    text,
                    state,
                    profile,
                    keyboard=None if finished else "quiz",
                    quiz_options=None if finished else QuizGame.options(new_g) if new_g else None,
                )
            new_g, text, profile, _ = GuessGame.handle(gstate, user_input, profile)
            state["game_state"] = new_g
            return DialogResult(text, state, profile)

        if user_input in ("помощь", "команды", "что ты умеешь"):
            return DialogResult(format_help(state), state, profile)

        if user_input in ("мой профиль", "профиль", "покажи профиль"):
            return DialogResult(format_profile(state, profile), state, profile)

        if user_input.startswith("режим"):
            parts = user_input.split()
            if len(parts) == 1:
                return DialogResult(
                    f"Сейчас: {CHARACTER_LABELS.get(state['character'], state['character'])}. Выбери кнопку:",
                    state,
                    profile,
                    keyboard="mode",
                )
            mode = CHARACTER_ALIASES.get(parts[-1])
            if mode:
                state["character"] = mode
                return DialogResult(
                    f"Режим: {CHARACTER_LABELS[mode]}.",
                    state,
                    profile,
                )
            return DialogResult("Неизвестный режим. Кнопки: обычный / весёлый / мемный / сарказм", state, profile, keyboard="mode")

        if user_input in ("играть", "мини-игра", "игры"):
            return DialogResult("Выбери игру:", state, profile, keyboard="play")

        if user_input in ("угадай число", "угадай"):
            state["game_state"] = start_guess()
            return DialogResult(
                "Загадал число 1–100. 10 попыток. Пиши число. «стоп» — выход.",
                state,
                profile,
            )

        if user_input in QUIZ_START_EXACT or any(p in user_input for p in QUIZ_START_PHRASES):
            state["game_state"] = start_quiz()
            text = QuizGame.current_question(state["game_state"])
            opts = QuizGame.options(state["game_state"])
            return DialogResult(text + "\n\nЖми кнопку:", state, profile, keyboard="quiz", quiz_options=opts)

        if "меня зовут" in user_input:
            rest = user_input.split("меня зовут", 1)[1].strip(" .,!?")
            if rest:
                state["name"] = rest.split()[0].capitalize()
                return DialogResult(f"Приятно, {state['name']}! Запомнил.", state, profile)

        if any(p in user_input for p in CONTINUE_PHRASES) and state.get("last_topic"):
            lt = state["last_topic"]
            pool = _active_pool(state["character"])
            if lt in pool:
                extra = _pick(pool, lt, last_answers)
                hint = CONTINUE_HINTS.get(lt, "")
                profile, notes = add_xp(profile, XP_CONTINUE)
                text = f"Продолжаем про {TOPIC_NAMES.get(lt, lt)}. {extra}\n{hint}"
                if notes:
                    text += "\n" + "\n".join(notes)
                return DialogResult(text, state, profile, topic=lt)

        mood = find_mood(words)
        if mood:
            ans = _pick(MOOD_RESPONSES, mood, last_answers)
            profile, notes = add_xp(profile, XP_MOOD)
            state["last_topic"] = "настроение"
            text = ans
            if notes:
                text += "\n" + "\n".join(notes)
            return DialogResult(text, state, profile, topic="настроение")

        topic = find_topic(user_input, words)
        if topic:
            state["last_topic"] = topic
            counts = dict(state.get("topic_counts") or {})
            counts[topic] = counts.get(topic, 0) + 1
            state["topic_counts"] = counts
            pool = _active_pool(state["character"])
            ans = _pick(pool, topic, last_answers) if topic in pool else MODE_FALLBACKS["обычный"]
            profile, notes = add_xp(profile, XP_TOPIC)
            from chatgr_core.core.xp import check_progress_achievements

            more = check_progress_achievements(profile, topic_count=len(counts))
            notes.extend(more)
            if state.get("name") and random.random() < 0.3:
                ans = f"{state['name']}, {ans[0].lower()}{ans[1:]}"
            text = ans
            if notes:
                text += "\n" + "\n".join(notes)
            return DialogResult(text, state, profile, topic=topic)

        char = state.get("character", "обычный")
        lt = state.get("last_topic")
        if lt:
            label = TOPIC_NAMES.get(lt, lt)
            return DialogResult(
                f"Не совсем понял. Говорили про {label} — «продолжи» или «помощь».",
                state,
                profile,
            )
        return DialogResult(MODE_FALLBACKS.get(char, MODE_FALLBACKS["обычный"]), state, profile)

    def set_mode(self, state: dict, mode: str) -> DialogResult:
        state = {**default_state(), **state}
        if mode not in CHARACTER_LABELS:
            return DialogResult("Неизвестный режим.", state, default_profile())
        state["character"] = mode
        return DialogResult(f"Режим: {CHARACTER_LABELS[mode]}.", state, default_profile())

    def start_quiz_session(self, state: dict, profile: dict) -> DialogResult:
        state = {**default_state(), **state}
        profile = {**default_profile(), **profile}
        state["game_state"] = start_quiz()
        text = QuizGame.current_question(state["game_state"])
        opts = QuizGame.options(state["game_state"])
        return DialogResult(text + "\n\nЖми кнопку:", state, profile, keyboard="quiz", quiz_options=opts)

    def quiz_callback(self, state: dict, profile: dict, choice: int) -> DialogResult:
        state = {**default_state(), **state}
        profile = {**default_profile(), **profile}
        gstate = state.get("game_state")
        if not gstate or gstate.get("type") != "quiz":
            return DialogResult("Викторина не активна. Напиши «викторина».", state, profile)
        new_g, text, profile, _, finished = QuizGame.answer(gstate, choice, profile)
        state["game_state"] = new_g
        return DialogResult(
            text,
            state,
            profile,
            keyboard=None if finished else "quiz",
            quiz_options=None if finished else (QuizGame.options(new_g) if new_g else None),
        )
