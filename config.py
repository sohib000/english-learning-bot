import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ADMIN_IDS может быть строкой "123,456" или просто "123"
_admin_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []
for x in _admin_raw.split(","):
    x = x.strip()
    if x.isdigit():
        ADMIN_IDS.append(int(x))

DB_PATH = os.getenv("DB_PATH", "data/bot.db")
AUDIO_DIR = "data/audio/generated"
LESSONS_DIR = "data/levels"
