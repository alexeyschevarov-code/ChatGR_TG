"""Общее ядро ChatGR: диалог, темы, игры, XP (консоль и Telegram)."""

from chatgr_core.core.content import ACHIEVEMENT_NAMES, QUIZ_QUESTIONS, VERSION
from chatgr_core.core.dialog import DialogEngine, DialogResult
from chatgr_core.core.games import GuessGame, QuizGame
from chatgr_core.core.topics import find_mood, find_topic
from chatgr_core.core.xp import add_xp, level_from_xp, unlock_achievement

__all__ = [
    "VERSION",
    "ACHIEVEMENT_NAMES",
    "QUIZ_QUESTIONS",
    "DialogEngine",
    "DialogResult",
    "GuessGame",
    "QuizGame",
    "find_mood",
    "find_topic",
    "add_xp",
    "level_from_xp",
    "unlock_achievement",
]
