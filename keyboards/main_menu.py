from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu(language: str = "ru") -> ReplyKeyboardMarkup:
    if language == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📖 Bugungi dars")],
                [KeyboardButton(text="📚 Mening darslarim")],
                [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="⚙️ Sozlamalar")],
            ],
            resize_keyboard=True,
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📖 Урок дня")],
            [KeyboardButton(text="📚 Мои уроки")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚙️ Настройки")],
        ],
        resize_keyboard=True,
    )