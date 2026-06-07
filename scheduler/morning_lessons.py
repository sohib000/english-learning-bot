from datetime import datetime
from aiogram import Bot
from aiogram.types import FSInputFile

from database.repository.users import get_users_by_notify_time
from database.repository.tests import mark_lesson_sent
from services.lesson_service import get_lesson_message
from keyboards.lessons import lesson_keyboard

async def send_morning_lessons(bot: Bot):
    now = datetime.now().strftime("%H:%M")
    users = await get_users_by_notify_time(now)
    for user in users:
        result = await get_lesson_message(
            level=user["current_level"],
            lesson_number=user["current_lesson"],
            language=user["language"],
        )
        if not result:
            continue
        lesson_id = result["lesson"]["id"]
        try:
            await bot.send_message(
                chat_id=user["telegram_id"],
                text=result["text"],
                parse_mode="Markdown",
                reply_markup=lesson_keyboard(lesson_id),
            )
            await mark_lesson_sent(user["id"], lesson_id)
        except Exception:
            pass  # User blocked bot
