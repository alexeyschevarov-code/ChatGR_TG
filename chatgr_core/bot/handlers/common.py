"""Основные текстовые команды и диалог через core."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from chatgr_core.bot.keyboards import main_reply_kb, markup_for_result
from chatgr_core.config import VERSION
from chatgr_core.services.dialog_service import DialogService

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, dialog_service: DialogService) -> None:
    uid = str(message.from_user.id)
    text = (
        f"=== ChatGR v{VERSION} ===\n"
        "Привет! Я адаптивный бот с XP, играми и викториной.\n\n"
        "Команды: /help /profile /play /quiz /leaderboard /mode"
    )
    dialog_service.repo.ensure_user(uid)
    await message.answer(text, reply_markup=main_reply_kb())


@router.message(Command("help"))
@router.message(F.text.lower() == "помощь")
async def cmd_help(message: Message, dialog_service: DialogService) -> None:
    result = dialog_service.process_text(str(message.from_user.id), "помощь")
    await message.answer(result.text)


@router.message(Command("profile"))
@router.message(F.text.lower().in_({"профиль", "мой профиль"}))
async def cmd_profile(message: Message, dialog_service: DialogService) -> None:
    result = dialog_service.process_text(str(message.from_user.id), "мой профиль")
    await message.answer(result.text)


@router.message(Command("leaderboard", "top"))
@router.message(F.text.lower().in_({"топ-10", "топ", "рекорды", "лидерборд"}))
async def cmd_leaderboard(message: Message, dialog_service: DialogService) -> None:
    text = dialog_service.leaderboard_text(10)
    await message.answer(text)


@router.message(Command("play"))
@router.message(F.text.lower().in_({"играть", "игры"}))
async def cmd_play(message: Message, dialog_service: DialogService) -> None:
    result = dialog_service.process_text(str(message.from_user.id), "играть")
    await message.answer(
        result.text,
        reply_markup=markup_for_result(result.keyboard, result.quiz_options),
    )


@router.message(Command("quiz"))
@router.message(F.text.lower().in_({"викторина", "квиз"}))
async def cmd_quiz(message: Message, dialog_service: DialogService) -> None:
    result = dialog_service.start_quiz(str(message.from_user.id))
    await message.answer(
        result.text,
        reply_markup=markup_for_result(result.keyboard, result.quiz_options),
    )


@router.message(Command("mode"))
@router.message(F.text.lower() == "режим")
async def cmd_mode(message: Message, dialog_service: DialogService) -> None:
    result = dialog_service.process_text(str(message.from_user.id), "режим")
    await message.answer(
        result.text,
        reply_markup=markup_for_result(result.keyboard, result.quiz_options),
    )


@router.message(F.text)
async def on_text(message: Message, dialog_service: DialogService) -> None:
    """Все остальные тексты → DialogEngine (core)."""
    if not message.text:
        return
    result = dialog_service.process_text(str(message.from_user.id), message.text)
    await message.answer(
        result.text,
        reply_markup=markup_for_result(result.keyboard, result.quiz_options),
    )
