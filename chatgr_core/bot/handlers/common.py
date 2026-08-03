"""Команды и диалог (0.8.0 beta)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from chatgr_core.bot.keyboards import main_reply_kb, markup_for_result
from chatgr_core.config import VERSION
from chatgr_core.services.dialog_service import DialogService

router = Router(name="common")


async def _reply(message: Message, result) -> None:
    await message.answer(
        result.text,
        reply_markup=markup_for_result(result.keyboard, result.quiz_options),
        parse_mode="HTML",
    )
    if getattr(result, "emoji_burst", None):
        try:
            await message.answer(result.emoji_burst)
        except Exception:
            pass


@router.message(CommandStart())
async def cmd_start(message: Message, dialog_service: DialogService) -> None:
    uid = str(message.from_user.id)
    dialog_service.repo.ensure_user(uid)
    text = (
        f"🐯 <b>ChatGR v{VERSION}</b>\n\n"
        "Бот <b>без нейросети</b>: темы, XP, монеты, квесты, викторина, дуэль, магазин.\n\n"
        "📌 /help · /profile · /quests · /shop\n"
        "🎮 /play · /quiz · /duel · /leaderboard\n"
        "🧠 /memory · /session\n\n"
        "Нажми кнопки внизу 👇"
    )
    await message.answer(text, reply_markup=main_reply_kb(), parse_mode="HTML")


@router.message(Command("help"))
@router.message(F.text.lower() == "помощь")
async def cmd_help(message: Message, dialog_service: DialogService) -> None:
    await _reply(message, dialog_service.process_text(str(message.from_user.id), "помощь"))


@router.message(Command("profile"))
@router.message(F.text.lower().in_({"профиль", "мой профиль"}))
async def cmd_profile(message: Message, dialog_service: DialogService) -> None:
    await _reply(message, dialog_service.process_text(str(message.from_user.id), "мой профиль"))


@router.message(Command("quests"))
@router.message(F.text.lower().in_({"квесты", "квест", "задания"}))
async def cmd_quests(message: Message, dialog_service: DialogService) -> None:
    await message.answer(dialog_service.quests_text(str(message.from_user.id)))


@router.message(Command("shop"))
@router.message(F.text.lower().in_({"магазин", "shop", "магаз"}))
async def cmd_shop(message: Message, dialog_service: DialogService) -> None:
    await _reply(message, dialog_service.shop_text(str(message.from_user.id)))


@router.message(Command("duel"))
@router.message(F.text.lower().in_({"дуэль", "дуель"}))
async def cmd_duel(message: Message, dialog_service: DialogService) -> None:
    await _reply(message, dialog_service.start_duel_bot(str(message.from_user.id)))


@router.message(Command("memory"))
@router.message(F.text.lower().in_({"память"}))
async def cmd_memory(message: Message, dialog_service: DialogService) -> None:
    await _reply(message, dialog_service.process_text(str(message.from_user.id), "память"))


@router.message(Command("session"))
@router.message(F.text.lower().in_({"сессия", "статистика"}))
async def cmd_session(message: Message, dialog_service: DialogService) -> None:
    await _reply(message, dialog_service.process_text(str(message.from_user.id), "сессия"))


@router.message(Command("leaderboard", "top"))
@router.message(F.text.lower().in_({"топ-10", "топ", "рекорды", "лидерборд"}))
async def cmd_leaderboard(message: Message, dialog_service: DialogService) -> None:
    await message.answer(dialog_service.leaderboard_text(10))


@router.message(Command("play"))
@router.message(F.text.lower().in_({"играть", "игры"}))
async def cmd_play(message: Message, dialog_service: DialogService) -> None:
    await _reply(message, dialog_service.process_text(str(message.from_user.id), "играть"))


@router.message(Command("quiz"))
@router.message(F.text.lower().in_({"викторина", "квиз"}))
async def cmd_quiz(message: Message, dialog_service: DialogService) -> None:
    await _reply(message, dialog_service.quiz_menu(str(message.from_user.id)))


@router.message(Command("mode"))
@router.message(F.text.lower() == "режим")
async def cmd_mode(message: Message, dialog_service: DialogService) -> None:
    await _reply(message, dialog_service.process_text(str(message.from_user.id), "режим"))


@router.message(F.text)
async def on_text(message: Message, dialog_service: DialogService) -> None:
    if not message.text:
        return
    await _reply(message, dialog_service.process_text(str(message.from_user.id), message.text))
