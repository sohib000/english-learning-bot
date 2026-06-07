import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.migrations import run_migrations
from middlewares.language import LanguageMiddleware
from services.scheduler_service import setup_scheduler

from handlers import start, lessons, tests, profile, admin, settings, my_lessons

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

async def main():
    await run_migrations()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())

    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(lessons.router)
    dp.include_router(my_lessons.router)
    dp.include_router(tests.router)
    dp.include_router(profile.router)
    dp.include_router(settings.router)

    setup_scheduler(bot)
    logging.info("🤖 Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())