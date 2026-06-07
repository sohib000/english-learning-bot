import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
AUDIO_DIR = "data/audio/generated"
LESSONS_DIR = "data/levels"
