"""Inline callbacks 0.8.0 beta."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from chatgr_core.bot.keyboards import markup_for_result
from chatgr_core.services.dialog_service import DialogService

router = Router(name="callbacks")


async def _edit(call: CallbackQuery, result) -> None:
    if call.message:
        await call.message.edit_text(
            result.text,
            reply_markup=markup_for_result(result.keyboard, result.quiz_options),
            parse_mode="HTML",
        )
    if getattr(result, "emoji_burst", None) and call.message:
        try:
            await call.message.answer(result.emoji_burst)
        except Exception:
            pass


@router.callback_query(F.data.startswith("mode:"))
async def on_mode(call: CallbackQuery, dialog_service: DialogService) -> None:
    mode = (call.data or "").split(":", 1)[1]
    result = dialog_service.set_mode(str(call.from_user.id), mode)
    await call.answer(f"Режим: {mode}")
    await _edit(call, result)


@router.callback_query(F.data == "play:guess")
async def on_play_guess(call: CallbackQuery, dialog_service: DialogService) -> None:
    result = dialog_service.start_guess(str(call.from_user.id))
    await call.answer("🎯")
    await _edit(call, result)


@router.callback_query(F.data == "play:quiz")
async def on_play_quiz(call: CallbackQuery, dialog_service: DialogService) -> None:
    result = dialog_service.quiz_menu(str(call.from_user.id))
    await call.answer("📚")
    await _edit(call, result)


@router.callback_query(F.data == "play:duel")
async def on_play_duel(call: CallbackQuery, dialog_service: DialogService) -> None:
    result = dialog_service.start_duel_bot(str(call.from_user.id))
    await call.answer("⚔️")
    await _edit(call, result)


@router.callback_query(F.data == "play:cancel")
async def on_play_cancel(call: CallbackQuery) -> None:
    await call.answer("Ок")
    if call.message:
        await call.message.edit_text("Меню закрыто. 👋")


@router.callback_query(F.data.startswith("qcat:"))
async def on_quiz_category(call: CallbackQuery, dialog_service: DialogService) -> None:
    cat = (call.data or "qcat:mixed").split(":", 1)[1]
    result = dialog_service.start_quiz(str(call.from_user.id), category=cat)
    await call.answer("Старт!")
    await _edit(call, result)


@router.callback_query(F.data.startswith("quiz:"))
async def on_quiz_answer(call: CallbackQuery, dialog_service: DialogService) -> None:
    try:
        choice = int((call.data or "quiz:0").split(":")[1])
    except ValueError:
        await call.answer("Ошибка")
        return
    result = dialog_service.process_quiz_choice(str(call.from_user.id), choice)
    await call.answer("Ок")
    await _edit(call, result)


@router.callback_query(F.data.startswith("buy:"))
async def on_buy(call: CallbackQuery, dialog_service: DialogService) -> None:
    item_id = (call.data or "buy:").split(":", 1)[1]
    result = dialog_service.buy(str(call.from_user.id), item_id)
    await call.answer("🛒")
    await _edit(call, result)
