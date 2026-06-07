import random
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_db

# ══════════════════════════════════════════
#  Шаблоны напоминаний — 3 типа
# ══════════════════════════════════════════

REMINDERS_RU = {
    "read": [
        "📖 Прочитай сегодняшний текст ещё раз — это займёт 1 минуту!",
        "📖 Повтори текст урока. Каждое прочтение = лучшее запоминание!",
        "📖 Открой урок и прочитай текст вслух. Это очень помогает!",
        "📖 1 минута чтения сейчас = слова в памяти навсегда!",
    ],
    "word": [
        "❓ Как по-английски: *кофе*? Проверь себя!",
        "❓ Переведи: *early* — ты помнишь это слово?",
        "❓ Что значит *wake up*? Открой урок и проверь!",
        "❓ Знаешь все слова из сегодняшнего урока? Давай проверим!",
        "💡 Повторение — мать учения! Загляни в словарь урока.",
    ],
    "audio": [
        "🔊 Прослушай аудио урока ещё раз — привыкай к произношению!",
        "🔊 5 прослушиваний = правильное произношение. Ты на каком?",
        "🔊 Включи аудио и повтори слова вслух за диктором!",
        "🎧 Слушай английский каждый день — это работает!",
    ],
    "motivation": [
        "💪 Ты уже учишь английский! Многие только мечтают.",
        "🔥 Не прерывай серию! Открой урок прямо сейчас.",
        "🌍 Английский открывает двери. Ты уже идёшь к цели!",
        "⚡ 5 минут сейчас = большой прогресс через месяц!",
        "🏆 Каждый урок приближает тебя к 1000 словам!",
    ],
}

REMINDERS_UZ = {
    "read": [
        "📖 Bugungi matnni yana bir marta o'qi — bu 1 daqiqa!",
        "📖 Dars matnini takrorla. Har safar o'qish = yaxshi eslab qolish!",
        "📖 Matnni baland ovozda o'qi. Bu juda yordam beradi!",
        "📖 Hozir 1 daqiqa o'qish = so'zlar xotirada abadiy!",
    ],
    "word": [
        "❓ Inglizcha qanday: *qahva*? O'zingni sinab ko'r!",
        "❓ Tarjima qil: *early* — bu so'zni eslayman?",
        "❓ *Wake up* nima degani? Darsni ochib tekshir!",
        "❓ Bugungi darsning barcha so'zlarini bilasizmi? Tekshiraylik!",
        "💡 Takrorlash — bilimning onasi! Dars lug'atiga qarang.",
    ],
    "audio": [
        "🔊 Dars audiosini yana bir marta tinglang — talaffuzga ko'nik!",
        "🔊 5 marta tinglash = to'g'ri talaffuz. Siz nechanchidasiz?",
        "🔊 Audioni yoqib, so'zlarni diktor bilan birga takrorlang!",
        "🎧 Har kuni ingliz tilini tinglang — bu ishlaydi!",
    ],
    "motivation": [
        "💪 Siz allaqachon ingliz tilini o'rganmoqdasiz! Ko'pchilik faqat orzu qiladi.",
        "🔥 Seriani to'xtatmang! Hoziroq darsni oching.",
        "🌍 Ingliz tili eshiklarni ochadi. Siz maqsad sari borayapsiz!",
        "⚡ Hozir 5 daqiqa = bir oydan keyin katta natija!",
        "🏆 Har bir dars sizni 1000 so'zga yaqinlashtiradi!",
    ],
}

# Какой тип напоминания отправлять в какой час
HOUR_TYPE = {
    10: "read",
    13: "word",
    16: "audio",
    19: "motivation",
}

def get_reminder_keyboard(lang: str) -> InlineKeyboardMarkup:
    if lang == "uz":
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📖 Darsni ochish", callback_data="open_lesson")
        ]])
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📖 Открыть урок", callback_data="open_lesson")
    ]])

async def send_hourly_reminders(bot: Bot, hour: int):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT u.telegram_id, u.language, u.name "
        "FROM users u "
        "JOIN reminders r ON r.user_id = u.id "
        "WHERE r.hourly_enabled = TRUE"
    )
    await db.close()

    reminder_type = HOUR_TYPE.get(hour, "motivation")

    for row in rows:
        lang = row["language"]
        templates = REMINDERS_UZ if lang == "uz" else REMINDERS_RU
        text = random.choice(templates[reminder_type])
        kb = get_reminder_keyboard(lang)

        try:
            await bot.send_message(
                row["telegram_id"],
                text,
                parse_mode="Markdown",
                reply_markup=kb,
            )
        except Exception:
            pass