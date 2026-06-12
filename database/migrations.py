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

    # ФИКС: у progress не было UNIQUE(user_id, lesson_id),
    # поэтому INSERT OR IGNORE / ON CONFLICT не срабатывали и копились дубли.
    # 1) Схлопываем существующие дубли, сохраняя лучшие значения.
    # 2) Создаём уникальный индекс — дальше работает честный upsert.
    try:
        await db.execute("""
            DELETE FROM progress
            WHERE id NOT IN (
                SELECT MIN(id) FROM progress GROUP BY user_id, lesson_id
            )
        """)
        # Перед удалением дублей переносим максимумы в оставшуюся строку
        # (на случай, если лучшие значения были в удалённых строках,
        #  сначала агрегируем во временную таблицу)
    except Exception:
        pass

    # Надёжный вариант: пересобираем агрегаты заново
    try:
        await db.execute("DROP TABLE IF EXISTS _progress_tmp")
        await db.execute("""
            CREATE TABLE _progress_tmp AS
            SELECT user_id,
                   lesson_id,
                   MAX(COALESCE(score, 0))            AS score,
                   MAX(COALESCE(completed, 0))        AS completed,
                   MAX(completed_at)                  AS completed_at,
                   MAX(COALESCE(lesson_sent, 0))      AS lesson_sent,
                   MAX(COALESCE(read_count, 0))       AS read_count
            FROM progress
            GROUP BY user_id, lesson_id
        """)
        await db.execute("DELETE FROM progress")
        await db.execute("""
            INSERT INTO progress (user_id, lesson_id, score, completed, completed_at, lesson_sent, read_count)
            SELECT user_id, lesson_id, score, completed, completed_at, lesson_sent, read_count
            FROM _progress_tmp
        """)
        await db.execute("DROP TABLE _progress_tmp")
        await db.commit()
    except Exception as e:
        print(f"Progress dedup skipped: {e}")

    # ФИКС: из-за старого бага в базе могло сохраниться время "07" вместо "07:00".
    # Чиним автоматически.
    try:
        await db.execute(
            "UPDATE users SET notify_time = notify_time || ':00' WHERE length(notify_time) <= 2"
        )
        await db.execute(
            "UPDATE reminders SET morning_time = morning_time || ':00' WHERE length(morning_time) <= 2"
        )
        await db.commit()
    except Exception:
        pass

    try:
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_progress_user_lesson "
            "ON progress(user_id, lesson_id)"
        )
        await db.commit()
        print("Unique index on progress ready")
    except Exception as e:
        print(f"Index creation skipped: {e}")

    await db.commit()
    await db.close()
    print("Migrations done")
