"""Inline callback: режим, игры, ответы викторины."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from chatgr_core.bot.keyboards import markup_for_result
from chatgr_core.services.dialog_service import DialogService

router = Router(name="callbacks")


@router.callback_query(F.data.startswith("mode:"))
async def on_mode(call: CallbackQuery, dialog_service: DialogService) -> None:
    mode = (call.data or "").split(":", 1)[1]
    result = dialog_service.set_mode(str(call.from_user.id), mode)
    await call.answer(f"Режим: {mode}")
    if call.message:
        await call.message.edit_text(result.text)


@router.callback_query(F.data == "play:guess")
async def on_play_guess(call: CallbackQuery, dialog_service: DialogService) -> None:
    result = dialog_service.start_guess(str(call.from_user.id))
    await call.answer("Игра!")
    if call.message:
        await call.message.edit_text(result.text)


@router.callback_query(F.data == "play:quiz")
async def on_play_quiz(call: CallbackQuery, dialog_service: DialogService) -> None:
    result = dialog_service.start_quiz(str(call.from_user.id))
    await call.answer("Викторина!")
    if call.message:
        await call.message.edit_text(
            result.text,
            reply_markup=markup_for_result(result.keyboard, result.quiz_options),
        )


@router.callback_query(F.data == "play:cancel")
async def on_play_cancel(call: CallbackQuery) -> None:
    await call.answer("Ок")
    if call.message:
        await call.message.edit_text("Меню игр закрыто.")


@router.callback_query(F.data.startswith("quiz:"))
async def on_quiz_answer(call: CallbackQuery, dialog_service: DialogService) -> None:
    try:
        choice = int((call.data or "quiz:0").split(":")[1])
    except ValueError:
        await call.answer("Ошибка")
        return
    result = dialog_service.process_quiz_choice(str(call.from_user.id), choice)
    await call.answer("Ок")
    if call.message:
        await call.message.edit_text(
            result.text,
            reply_markup=markup_for_result(result.keyboard, result.quiz_options),
        )
