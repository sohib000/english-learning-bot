from database.db import get_db
from database.models import (
    CREATE_USERS, CREATE_PROGRESS,
    CREATE_STATISTICS, CREATE_REMINDERS
)

CREATE_LESSONS_TABLE = """
CREATE TABLE IF NOT EXISTS lessons (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_number INTEGER UNIQUE NOT NULL,
    text_en       TEXT,
    audio_path    TEXT
);"""

async def run_migrations():
    db = await get_db()
    for sql in [CREATE_USERS, CREATE_PROGRESS, CREATE_STATISTICS, CREATE_REMINDERS, CREATE_LESSONS_TABLE]:
        await db.execute(sql)

    # Добавляем read_count если его нет (для существующих БД)
    try:
        await db.execute("ALTER TABLE progress ADD COLUMN read_count INTEGER DEFAULT 0")
        await db.commit()
        print("Added read_count column")
    except Exception:
        pass  # Колонка уже есть

    await db.commit()
    await db.close()
    print("Migrations done")