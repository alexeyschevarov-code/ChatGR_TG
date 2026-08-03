"""Дуэль-квиз: против бота или друга по коду (без нейросети)."""
from __future__ import annotations

import random
import string
from typing import Any

from chatgr_core.core.games import QuizGame, start_quiz
from chatgr_core.core.xp import add_xp, unlock_achievement

DUEL_QUESTIONS = 5
DUEL_WIN_COINS = 15
DUEL_WIN_XP = 20
DUEL_DRAW_COINS = 5


def _code(n: int = 5) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def start_duel_vs_bot() -> dict[str, Any]:
    quiz = start_quiz(n=DUEL_QUESTIONS, category="mixed")
    # бот «играет» заранее: случайный счёт 0..5 с лёгким уклоном к 2–3
    bot_score = min(DUEL_QUESTIONS, max(0, int(random.gauss(2.5, 1.2))))
    return {
        "type": "duel",
        "mode": "bot",
        "code": None,
        "questions": quiz["questions"],
        "index": 0,
        "score": 0,
        "bot_score": bot_score,
        "category": "mixed",
    }


def create_friend_duel(host_id: str) -> tuple[str, dict[str, Any]]:
    code = _code()
    quiz = start_quiz(n=DUEL_QUESTIONS, category="mixed")
    state = {
        "type": "duel",
        "mode": "friend",
        "code": code,
        "host_id": str(host_id),
        "guest_id": None,
        "questions": quiz["questions"],
        "index": 0,
        "score": 0,
        "host_score": None,
        "guest_score": None,
        "role": "host",
        "category": "mixed",
    }
    return code, state


def join_friend_duel(code: str, guest_id: str, host_payload: dict) -> dict[str, Any]:
    """guest_id получает свою копию вопросов из host_payload."""
    return {
        "type": "duel",
        "mode": "friend",
        "code": code,
        "host_id": host_payload.get("host_id"),
        "guest_id": str(guest_id),
        "questions": list(host_payload["questions"]),
        "index": 0,
        "score": 0,
        "host_score": host_payload.get("host_score"),
        "guest_score": None,
        "role": "guest",
        "category": host_payload.get("category", "mixed"),
    }


def duel_question_text(state: dict) -> str:
    n = state["index"] + 1
    total = len(state["questions"])
    mode = "бот" if state.get("mode") == "bot" else f"друг ({state.get('code')})"
    q = state["questions"][state["index"]]["q"]
    return f"⚔️ Дуэль vs {mode} — вопрос {n}/{total}\n\n{q}"


def answer_duel(
    state: dict, choice: int, profile: dict
) -> tuple[dict | None, str, dict, list[str], bool, dict | None]:
    """
    Returns:
      new_state, text, profile, notes, finished, finish_meta
    finish_meta for friend sync: {code, role, score} or None
    """
    notes: list[str] = []
    profile = dict(profile)
    state = dict(state)
    qdata = state["questions"][state["index"]]
    if choice < 0 or choice > 2:
        return state, "Выбери 1, 2 или 3.", profile, notes, False, None

    if choice == qdata["correct"]:
        state["score"] += 1
        feedback = "Верно! ✅"
    else:
        right = qdata["options"][qdata["correct"]]
        feedback = f"Неверно. Правильно: {right}."

    state["index"] += 1
    total = len(state["questions"])
    if state["index"] < total:
        next_q = duel_question_text(state)
        opts_note = ""
        return state, f"{feedback}\n\n{next_q}", profile, notes, False, None

    # finished
    my_score = state["score"]
    finish_meta = None

    if state.get("mode") == "bot":
        bot_score = int(state.get("bot_score") or 0)
        if my_score > bot_score:
            profile["coins"] = int(profile.get("coins") or 0) + DUEL_WIN_COINS
            profile, xp_notes = add_xp(profile, DUEL_WIN_XP)
            notes.extend(xp_notes)
            notes.append(f"+{DUEL_WIN_COINS} 🪙 за победу в дуэли")
            profile, title = unlock_achievement(profile, "first_duel")
            if title:
                notes.append(f"🏆 {title}")
            result = f"🏆 Ты победил бота! {my_score}:{bot_score}"
        elif my_score == bot_score:
            profile["coins"] = int(profile.get("coins") or 0) + DUEL_DRAW_COINS
            notes.append(f"Ничья {my_score}:{bot_score}. +{DUEL_DRAW_COINS} 🪙")
            result = f"🤝 Ничья с ботом {my_score}:{bot_score}"
        else:
            result = f"😔 Бот сильнее: {my_score}:{bot_score}. Ещё раз: «дуэль»"
        text = f"{feedback}\n\n⚔️ Дуэль окончена!\n{result}"
        if notes:
            text += "\n" + "\n".join(notes)
        return None, text, profile, notes, True, None

    # friend: report score, wait for opponent
    role = state.get("role", "host")
    finish_meta = {
        "code": state.get("code"),
        "role": role,
        "score": my_score,
        "host_id": state.get("host_id"),
        "guest_id": state.get("guest_id"),
    }
    text = (
        f"{feedback}\n\n⚔️ Ты закончил дуэль!\n"
        f"Твой счёт: {my_score}/{total}.\n"
        f"Ждём соперника (код {state.get('code')})…"
    )
    return None, text, profile, notes, True, finish_meta


def resolve_friend_result(
    host_score: int, guest_score: int, profile: dict, i_am_host: bool
) -> tuple[dict, str]:
    """Награждает текущего игрока по итогам."""
    notes: list[str] = []
    my = host_score if i_am_host else guest_score
    opp = guest_score if i_am_host else host_score
    if my > opp:
        profile["coins"] = int(profile.get("coins") or 0) + DUEL_WIN_COINS
        profile, xp_notes = add_xp(profile, DUEL_WIN_XP)
        notes.extend(xp_notes)
        notes.append(f"+{DUEL_WIN_COINS} 🪙")
        profile, title = unlock_achievement(profile, "first_duel")
        if title:
            notes.append(f"🏆 {title}")
        head = f"🏆 Победа! {my}:{opp}"
    elif my == opp:
        profile["coins"] = int(profile.get("coins") or 0) + DUEL_DRAW_COINS
        notes.append(f"+{DUEL_DRAW_COINS} 🪙")
        head = f"🤝 Ничья {my}:{opp}"
    else:
        head = f"😔 Поражение {my}:{opp}"
    text = f"⚔️ Итог дуэли\n{head}"
    if notes:
        text += "\n" + "\n".join(notes)
    return profile, text
