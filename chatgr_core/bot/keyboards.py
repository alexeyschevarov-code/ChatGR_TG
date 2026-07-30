from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def main_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Помощь"), KeyboardButton(text="Статистика")],
            [KeyboardButton(text="Играть"), KeyboardButton(text="Профиль")],
            [KeyboardButton(text="Режим"), KeyboardButton(text="Топ-10")],
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
            [InlineKeyboardButton(text="Угадай число", callback_data="play:guess")],
            [InlineKeyboardButton(text="Викторина", callback_data="play:quiz")],
            [InlineKeyboardButton(text="Отмена", callback_data="play:cancel")],
        ]
    )


def quiz_inline_kb(options: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i, opt in enumerate(options):
        rows.append([
            InlineKeyboardButton(text=f"{i + 1}. {opt}", callback_data=f"quiz:{i}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def markup_for_result(keyboard: str | None, quiz_options: list[str] | None):
    if keyboard == "mode":
        return mode_inline_kb()
    if keyboard == "play":
        return play_inline_kb()
    if keyboard == "quiz" and quiz_options:
        return quiz_inline_kb(quiz_options)
    return None
