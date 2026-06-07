from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_db

async def send_evening_test_prompt(bot: Bot):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT u.telegram_id, u.language FROM users u "
        "JOIN reminders r ON r.user_id = u.id WHERE r.evening_time <= strftime('%H:%M','now')"
    )
    await db.close()

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📝 Пройти тест", callback_data="evening_test")
    ]])
    for row in rows:
        msg = "🌆 Вечерний тест готов! Проверь, что запомнил сегодня." if row["language"] == "ru" \
              else "🌆 Kechki test tayyor! Bugun nima esladingizni tekshiring."
        try:
            await bot.send_message(row["telegram_id"], msg, reply_markup=kb)
        except Exception:
            pass
