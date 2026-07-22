from database.db import get_db

async def run_migrations():
    db = await get_db()

    # Основные таблицы
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id     INTEGER UNIQUE NOT NULL,
            name            TEXT,
            language        TEXT DEFAULT 'ru',
            current_level   INTEGER DEFAULT 1,
            current_lesson  INTEGER DEFAULT 1,
            notify_time     TEXT DEFAULT '07:00',
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER REFERENCES users(id),
            lesson_id    INTEGER NOT NULL,
            score        INTEGER DEFAULT 0,
            completed    BOOLEAN DEFAULT FALSE,
            completed_at DATETIME,
            lesson_sent  BOOLEAN DEFAULT FALSE,
            read_count   INTEGER DEFAULT 0
        )""")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS statistics (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id           INTEGER UNIQUE REFERENCES users(id),
            words_learned     INTEGER DEFAULT 0,
            lessons_completed INTEGER DEFAULT 0,
            current_streak    INTEGER DEFAULT 0,
            average_score     REAL DEFAULT 0.0,
            last_activity     DATETIME
        )""")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER UNIQUE REFERENCES users(id),
            hourly_enabled  BOOLEAN DEFAULT TRUE,
            morning_time    TEXT DEFAULT '07:00',
            evening_time    TEXT DEFAULT '20:00'
        )""")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_number INTEGER UNIQUE NOT NULL,
            text_en       TEXT,
            audio_path    TEXT
        )""")

    # Таблица кэша аудио (file_id из Telegram)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS audio_cache (
            lesson_id    INTEGER PRIMARY KEY,
            file_id      TEXT NOT NULL,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")

    # Миграция 1: read_count
    try:
        await db.execute("ALTER TABLE progress ADD COLUMN read_count INTEGER DEFAULT 0")
        print("Migration: added read_count")
    except Exception:
        pass

    # Миграция 2: удаляем дубли в progress (оставляем лучший результат)
    try:
        await db.execute("""
            DELETE FROM progress WHERE id NOT IN (
                SELECT MAX(id) FROM progress GROUP BY user_id, lesson_id
            )""")
        print("Migration: removed duplicate progress rows")
    except Exception:
        pass

    # Миграция 3: UNIQUE индекс на progress
    try:
        await db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_progress_user_lesson
            ON progress(user_id, lesson_id)""")
        print("Migration: UNIQUE index created on progress(user_id, lesson_id)")
    except Exception:
        pass

    await db.commit()
    await db.close()
    print("✅ All migrations done")
