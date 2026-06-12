from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_db


async def send_evening_test_prompt(bot: Bot):
    # ФИКС: раньше было условие r.evening_time <= strftime('%H:%M','now'),
    # но 'now' в SQLite — это UTC. В 20:00 по Ташкенту это 15:00 UTC,
    # условие никогда не выполнялось — тест не отправлялся НИКОМУ.
    # Job и так запускается ровно в 20:00 по Ташкенту (см. scheduler_service),
    # поэтому просто берём всех пользователей с включёнными напоминаниями.
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT u.telegram_id, u.language FROM users u "
        "JOIN reminders r ON r.user_id = u.id "
        "WHERE r.hourly_enabled = TRUE"
    )
    await db.close()

    for row in rows:
        if row["language"] == "uz":
            msg = "🌆 Kechki test tayyor! Bugun nima esladingizni tekshiring."
            btn = "📝 Testni boshlash"
        else:
            msg = "🌆 Вечерний тест готов! Проверь, что запомнил сегодня."
            btn = "📝 Пройти тест"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=btn, callback_data="evening_test")
        ]])
        try:
            await bot.send_message(row["telegram_id"], msg, reply_markup=kb)
        except Exception:
            pass
