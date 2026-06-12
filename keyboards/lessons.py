from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def lesson_keyboard(lesson_id: int, read_count: int = 0) -> InlineKeyboardMarkup:
    # Счётчик прочтений (ФИКС: опечатка "Prочитал")
    if read_count == 0:
        read_label = "✅ Прочитал / O'qidim (0)"
    elif read_count == 1:
        read_label = f"✅ Прочитал / O'qidim ({read_count} раз)"
    elif read_count < 5:
        read_label = f"✅ Прочитал / O'qidim ({read_count} раз) 👍"
    else:
        read_label = f"✅ Прочитал / O'qidim ({read_count} раз) 🔥"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔊 Слушать аудио / Audio tinglash",
            callback_data=f"audio:{lesson_id}"
        )],
        [InlineKeyboardButton(
            text=read_label,
            callback_data=f"read:{lesson_id}"
        )],
        [InlineKeyboardButton(
            text="📝 Начать тест / Testni boshlash",
            callback_data=f"test:{lesson_id}"
        )],
    ])
