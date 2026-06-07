from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from scheduler.morning_lessons import send_morning_lessons
from scheduler.hourly_reminders import send_hourly_reminders
from scheduler.evening_tests import send_evening_test_prompt

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

    # Утренний урок — каждый час в 00 минут
    scheduler.add_job(
        send_morning_lessons, "cron",
        hour="*", minute=0,
        args=[bot], id="morning_lessons",
    )

    # Напоминания — 4 раза в день, каждое своего типа
    for hour in [10, 13, 16, 19]:
        scheduler.add_job(
            send_hourly_reminders, "cron",
            hour=hour, minute=0,
            args=[bot, hour],
            id="reminder_" + str(hour),
        )

    # Вечерний тест — в 20:00
    scheduler.add_job(
        send_evening_test_prompt, "cron",
        hour=20, minute=0,
        args=[bot], id="evening_test",
    )

    scheduler.start()
    return scheduler