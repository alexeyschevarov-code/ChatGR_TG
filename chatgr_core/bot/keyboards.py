from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from chatgr_core.core.content import QUIZ_CATEGORIES
from chatgr_core.core.shop import SHOP_ITEMS


def main_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Помощь"), KeyboardButton(text="Квесты")],
            [KeyboardButton(text="Играть"), KeyboardButton(text="Магазин")],
            [KeyboardButton(text="Викторина"), KeyboardButton(text="Дуэль")],
            [KeyboardButton(text="Профиль"), KeyboardButton(text="Топ-10")],
            [KeyboardButton(text="Память"), KeyboardButton(text="Сессия")],
        ],
        resize_keyboard=True,
    )


def mode_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Обычный", callback_data="mode:обычный"),
                InlineKeyboardButton(text="Весёлый", callback_data="mode:весёлый"),
            ],
            [
                InlineKeyboardButton(text="Мемный", callback_data="mode:мемный"),
                InlineKeyboardButton(text="Сарказм", callback_data="mode:сарказм"),
            ],
        ]
    )


def play_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Угадай число 🎯", callback_data="play:guess")],
            [InlineKeyboardButton(text="Викторина 📚", callback_data="play:quiz")],
            [InlineKeyboardButton(text="Дуэль vs бот ⚔️", callback_data="play:duel")],
            [InlineKeyboardButton(text="Отмена", callback_data="play:cancel")],
        ]
    )


def quiz_category_kb() -> InlineKeyboardMarkup:
    rows = []
    for cat, label in QUIZ_CATEGORIES.items():
        rows.append([InlineKeyboardButton(text=label, callback_data=f"qcat:{cat}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quiz_inline_kb(options: list[str]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{i + 1}. {opt}", callback_data=f"quiz:{i}")]
        for i, opt in enumerate(options)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quiz_again_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ещё раз 🔄", callback_data="play:quiz")],
            [InlineKeyboardButton(text="Другая категория 📚", callback_data="play:quiz")],
            [InlineKeyboardButton(text="Дуэль ⚔️", callback_data="play:duel")],
        ]
    )


def shop_inline_kb() -> InlineKeyboardMarkup:
    rows = []
    for item_id, item in SHOP_ITEMS.items():
        rows.append([
            InlineKeyboardButton(
                text=f"{item['name']} — {item['price']}🪙",
                callback_data=f"buy:{item_id}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def markup_for_result(keyboard: str | None, quiz_options: list[str] | None):
    if keyboard == "mode":
        return mode_inline_kb()
    if keyboard == "play":
        return play_inline_kb()
    if keyboard == "quiz_cat":
        return quiz_category_kb()
    if keyboard == "quiz" and quiz_options:
        return quiz_inline_kb(quiz_options)
    if keyboard == "quiz_again":
        return quiz_again_kb()
    if keyboard == "shop":
        return shop_inline_kb()
    return None
