"""Мини-игры: угадай число и викторина (состояние в dict, без Telegram)."""
from __future__ import annotations

import random
from typing import Any

from chatgr_core.core.content import (
    QUIZ_QUESTIONS,
    XP_GAME_WIN,
    XP_QUIZ_CORRECT,
    XP_QUIZ_FINISH_PER,
)
from chatgr_core.core.quests import complete_quest
from chatgr_core.core.xp import add_xp, unlock_achievement


def start_guess(max_attempts: int = 10) -> dict[str, Any]:
    return {
        "type": "guess",
        "secret": random.randint(1, 100),
        "attempts": 0,
        "max_attempts": max_attempts,
    }


def _pool_for_category(category: str | None) -> list[dict]:
    if not category or category == "mixed":
        return list(QUIZ_QUESTIONS)
    pool = [q for q in QUIZ_QUESTIONS if q.get("cat") == category]
    return pool or list(QUIZ_QUESTIONS)


def start_quiz(n: int = 5, category: str | None = "mixed") -> dict[str, Any]:
    pool = _pool_for_category(category)
    sample = random.sample(pool, min(n, len(pool)))
    questions = [
        {
            "q": q["q"],
            "options": list(q["options"]),
            "correct": q["correct"],
            "cat": q.get("cat", "mixed"),
        }
        for q in sample
    ]
    return {
        "type": "quiz",
        "category": category or "mixed",
        "questions": questions,
        "index": 0,
        "score": 0,
    }


class GuessGame:
    @staticmethod
    def handle(state: dict, user_input: str, profile: dict) -> tuple[dict | None, str, dict, list[str]]:
        notes: list[str] = []
        profile = dict(profile)
        if user_input in ("стоп", "выход", "хватит"):
            return None, "Игра окончена. Возвращаемся в чат!", profile, notes
        if not user_input.isdigit():
            return state, "Нужно число от 1 до 100. Или «стоп».", profile, notes
        guess = int(user_input)
        state = dict(state)
        state["attempts"] += 1
        left = state["max_attempts"] - state["attempts"]
        secret = state["secret"]
        if guess == secret:
            tries = state["attempts"]
            profile, xp_notes = add_xp(profile, XP_GAME_WIN)
            notes.extend(xp_notes)
            profile, title = unlock_achievement(profile, "first_guess")
            if title:
                notes.append(f"🏆 {title}")
            if tries <= 3:
                profile, title = unlock_achievement(profile, "guess_master")
                if title:
                    notes.append(f"🏆 {title}")
            profile, qnotes = complete_quest(profile, "guess_win")
            notes.extend(qnotes)
            text = f"Верно! Это {secret}. Угадал за {tries} попыток. 🎉"
            if notes:
                text += "\n" + "\n".join(notes)
            return None, text, profile, notes
        if left <= 0:
            return None, f"Попытки кончились. Было загадано: {secret}.", profile, notes
        hint = "меньше" if guess > secret else "больше"
        return state, f"Моё число {hint}! Осталось попыток: {left}.", profile, notes


class QuizGame:
    @staticmethod
    def current_question(state: dict) -> str:
        n = state["index"] + 1
        total = len(state["questions"])
        cat = state.get("category", "mixed")
        q = state["questions"][state["index"]]["q"]
        return f"Викторина [{cat}] — вопрос {n}/{total}\n\n{q}"

    @staticmethod
    def options(state: dict) -> list[str]:
        return list(state["questions"][state["index"]]["options"])

    @staticmethod
    def parse_choice(user_input: str, options: list[str]) -> int | None:
        if user_input in ("1", "2", "3"):
            return int(user_input) - 1
        low = user_input.lower()
        for i, opt in enumerate(options):
            if low == opt.lower() or opt.lower() in low:
                return i
        return None

    @staticmethod
    def answer(
        state: dict, choice: int, profile: dict
    ) -> tuple[dict | None, str, dict, list[str], bool]:
        notes: list[str] = []
        profile = dict(profile)
        state = dict(state)
        qdata = state["questions"][state["index"]]
        if choice < 0 or choice > 2:
            return state, "Выбери 1, 2 или 3.", profile, notes, False

        if choice == qdata["correct"]:
            state["score"] += 1
            feedback = "Верно! ✅"
            profile, xp_notes = add_xp(profile, XP_QUIZ_CORRECT)
            notes.extend(xp_notes or [f"+{XP_QUIZ_CORRECT} XP"])
        else:
            right = qdata["options"][qdata["correct"]]
            feedback = f"Неверно. Правильно: {right}."

        state["index"] += 1
        total = len(state["questions"])
        if state["index"] >= total:
            score = state["score"]
            finish_xp = XP_QUIZ_FINISH_PER * score
            if finish_xp:
                profile, xp_notes = add_xp(profile, finish_xp)
                notes.extend(xp_notes or [f"+{finish_xp} XP за итог"])
            profile, title = unlock_achievement(profile, "first_quiz")
            if title:
                notes.append(f"🏆 {title}")
            if score == total:
                profile, title = unlock_achievement(profile, "perfect_quiz")
                if title:
                    notes.append(f"🏆 {title}")
            won = total > 0 and score > total // 2
            if won:
                profile, qnotes = complete_quest(profile, "quiz_win")
                notes.extend(qnotes)
                wins = int(profile.get("quiz_wins") or 0) + 1
                profile["quiz_wins"] = wins
                if wins >= 10:
                    profile, title = unlock_achievement(profile, "quiz_master")
                    if title:
                        notes.append(f"🏆 {title}")
            text = f"{feedback}\n\nВикторина окончена! Счёт: {score} из {total}. 🎉"
            if notes:
                text += "\n" + "\n".join(notes)
            return None, text, profile, notes, True

        next_q = QuizGame.current_question(state)
        body = feedback
        if notes:
            body += "\n" + "\n".join(notes)
        return state, f"{body}\n\n{next_q}", profile, notes, False
