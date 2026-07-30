"""Сервис: core DialogEngine + UserRepository."""
from __future__ import annotations

from chatgr_core.core.dialog import DialogEngine, DialogResult
from chatgr_core.repositories.users import UserRepository


class DialogService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
        self.engine = DialogEngine()

    def process_text(self, tg_user_id: str, text: str) -> DialogResult:
        if self.repo.is_banned(tg_user_id):
            return DialogResult(
                "⛔ Ты заблокирован администратором.",
                {},
                {},
                save=False,
            )
        state, profile = self.repo.load_dialog_context(tg_user_id)
        # game_state is in state from DB
        result = self.engine.handle(text, state=state, profile=profile, last_answers={})
        if result.save:
            self.repo.save_dialog_context(
                tg_user_id,
                result.state,
                result.profile,
                user_text=text,
                bot_text=result.text,
                topic=result.topic,
            )
        return result

    def process_quiz_choice(self, tg_user_id: str, choice: int) -> DialogResult:
        if self.repo.is_banned(tg_user_id):
            return DialogResult("⛔ Ты заблокирован.", {}, {}, save=False)
        state, profile = self.repo.load_dialog_context(tg_user_id)
        result = self.engine.quiz_callback(state, profile, choice)
        if result.save:
            self.repo.save_dialog_context(
                tg_user_id,
                result.state,
                result.profile,
                user_text=f"[quiz:{choice}]",
                bot_text=result.text,
                topic="quiz",
            )
        return result

    def set_mode(self, tg_user_id: str, mode: str) -> DialogResult:
        state, profile = self.repo.load_dialog_context(tg_user_id)
        state["character"] = mode
        self.repo.save_dialog_context(tg_user_id, state, profile, user_text="[mode]", bot_text=mode)
        from chatgr_core.core.content import CHARACTER_LABELS

        return DialogResult(
            f"Режим: {CHARACTER_LABELS.get(mode, mode)}.",
            state,
            profile,
            save=False,
        )

    def start_quiz(self, tg_user_id: str) -> DialogResult:
        state, profile = self.repo.load_dialog_context(tg_user_id)
        result = self.engine.start_quiz_session(state, profile)
        self.repo.save_dialog_context(
            tg_user_id, result.state, result.profile,
            user_text="[quiz_start]", bot_text=result.text, topic="quiz",
        )
        return result

    def start_guess(self, tg_user_id: str) -> DialogResult:
        return self.process_text(tg_user_id, "угадай число")

    def leaderboard_text(self, limit: int = 10) -> str:
        top = self.repo.leaderboard(limit)
        lines = [f"── Топ-{limit} ChatGR (XP) ──", ""]
        if not top:
            lines.append("Пока пусто. Поболтай или сыграй!")
            return "\n".join(lines)
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, p in enumerate(top, 1):
            m = medals.get(i, f"{i}.")
            lines.append(f"{m} {p['name']} — ур. {p['level']} · {p['xp']} XP")
        return "\n".join(lines)
