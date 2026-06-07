from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def choices_keyboard(options: list, q_index: int) -> InlineKeyboardMarkup:
    """5 кнопок — каждая на своей строке."""
    rows = [
        [InlineKeyboardButton(text=opt, callback_data=f"ans:{q_index}:{opt}")]
        for opt in options
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)