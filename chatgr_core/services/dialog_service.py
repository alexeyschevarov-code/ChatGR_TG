"""Сервис: DialogEngine + UserRepository (0.8.0 beta)."""
from __future__ import annotations

import json

from chatgr_core.core.dialog import DialogEngine, DialogResult
from chatgr_core.core.duel import duel_question_text, join_friend_duel, resolve_friend_result
from chatgr_core.core.quests import format_quests_text
from chatgr_core.repositories.users import UserRepository


class DialogService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
        self.engine = DialogEngine()

    def process_text(self, tg_user_id: str, text: str) -> DialogResult:
        if self.repo.is_banned(tg_user_id):
            return DialogResult("⛔ Ты заблокирован администратором.", {}, {}, save=False)

        state, profile = self.repo.load_dialog_context(tg_user_id)
        result = self.engine.handle(text, state=state, profile=profile, last_answers={})

        # friend duel create/join hooks
        meta = result.duel_meta or {}
        if meta.get("action") == "create":
            code = meta["code"]
            payload = meta["payload"]
            payload["host_id"] = str(tg_user_id)
            self.repo.create_duel(code, tg_user_id, payload["questions"])
            result.state["game_state"] = payload
            # host starts answering immediately
            result.state["game_state"]["role"] = "host"
            qtext = duel_question_text(result.state["game_state"])
            opts = list(result.state["game_state"]["questions"][0]["options"])
            result = DialogResult(
                f"⚔️ Дуэль создана! Код: <b>{code}</b>\n"
                f"Друг пишет: <code>дуэль {code}</code>\n\n{qtext}",
                result.state,
                result.profile,
                keyboard="quiz",
                quiz_options=opts,
            )

        elif meta.get("action") == "join":
            code = meta["code"]
            d = self.repo.join_duel(code, tg_user_id)
            if not d:
                result = DialogResult(
                    f"Дуэль {code} не найдена или занята.",
                    result.state,
                    result.profile,
                )
            elif d["host_id"] == str(tg_user_id):
                result = DialogResult("Это твой код. Жди друга.", result.state, result.profile)
            else:
                questions = json.loads(d["questions"])
                host_payload = {
                    "host_id": d["host_id"],
                    "questions": questions,
                    "host_score": d["host_score"],
                    "category": "mixed",
                }
                gstate = join_friend_duel(code, tg_user_id, host_payload)
                result.state["game_state"] = gstate
                qtext = duel_question_text(gstate)
                opts = list(gstate["questions"][0]["options"])
                result = DialogResult(
                    f"⚔️ Ты в дуэли {code}!\n\n{qtext}",
                    result.state,
                    result.profile,
                    keyboard="quiz",
                    quiz_options=opts,
                )

        # friend duel finish scores
        if result.duel_meta and result.duel_meta.get("code") and result.duel_meta.get("score") is not None:
            m = result.duel_meta
            d = self.repo.set_duel_score(m["code"], m["role"], m["score"])
            if d and d.get("status") == "done":
                i_am_host = m["role"] == "host"
                result.profile, extra = resolve_friend_result(
                    int(d["host_score"]),
                    int(d["guest_score"]),
                    result.profile,
                    i_am_host=i_am_host,
                )
                result.text = result.text + "\n\n" + extra

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

        if result.duel_meta and result.duel_meta.get("code") is not None and result.duel_meta.get("score") is not None:
            m = result.duel_meta
            d = self.repo.set_duel_score(m["code"], m["role"], m["score"])
            if d and d.get("status") == "done":
                i_am_host = m["role"] == "host"
                result.profile, extra = resolve_friend_result(
                    int(d["host_score"]),
                    int(d["guest_score"]),
                    result.profile,
                    i_am_host=i_am_host,
                )
                result.text = result.text + "\n\n" + extra

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
            f"Режим: {CHARACTER_LABELS.get(mode, mode)}. ✨",
            state,
            profile,
            save=False,
        )

    def start_quiz(self, tg_user_id: str, category: str = "mixed") -> DialogResult:
        state, profile = self.repo.load_dialog_context(tg_user_id)
        result = self.engine.start_quiz_session(state, profile, category=category)
        self.repo.save_dialog_context(
            tg_user_id, result.state, result.profile,
            user_text=f"[quiz_start:{category}]", bot_text=result.text, topic="quiz",
        )
        return result

    def quiz_menu(self, tg_user_id: str) -> DialogResult:
        return self.process_text(tg_user_id, "викторина")

    def start_guess(self, tg_user_id: str) -> DialogResult:
        return self.process_text(tg_user_id, "угадай число")

    def start_duel_bot(self, tg_user_id: str) -> DialogResult:
        return self.process_text(tg_user_id, "дуэль")

    def shop_text(self, tg_user_id: str) -> DialogResult:
        return self.process_text(tg_user_id, "магазин")

    def buy(self, tg_user_id: str, item_id: str) -> DialogResult:
        return self.process_text(tg_user_id, f"купить {item_id}")

    def quests_text(self, tg_user_id: str) -> str:
        _, profile = self.repo.load_dialog_context(tg_user_id)
        return format_quests_text(profile)

    def leaderboard_text(self, limit: int = 10) -> str:
        top = self.repo.leaderboard(limit)
        lines = [f"── Топ-{limit} ChatGR (XP) ──", ""]
        if not top:
            lines.append("Пока пусто. Поболтай или сыграй!")
            return "\n".join(lines)
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, p in enumerate(top, 1):
            m = medals.get(i, f"{i}.")
            coins = p.get("coins") or 0
            lines.append(f"{m} {p['name']} — ур. {p['level']} · {p['xp']} XP · {coins} 🪙")
        return "\n".join(lines)
