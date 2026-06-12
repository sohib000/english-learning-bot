from database.db import get_db


async def save_progress(user_id: int, lesson_id: int, score: int):
    # ФИКС: теперь есть UNIQUE(user_id, lesson_id) — честный upsert.
    # Раньше "ON CONFLICT DO NOTHING" не срабатывал (конфликта не было)
    # и при каждом тесте плодились дубли. Сохраняем лучший результат.
    db = await get_db()
    await db.execute("""
        INSERT INTO progress (user_id, lesson_id, score, completed, completed_at)
        VALUES (?, ?, ?, TRUE, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, lesson_id) DO UPDATE SET
            score        = MAX(COALESCE(progress.score, 0), excluded.score),
            completed    = TRUE,
            completed_at = CURRENT_TIMESTAMP
    """, (user_id, lesson_id, score))
    await db.commit()
    await db.close()


async def mark_lesson_sent(user_id: int, lesson_id: int):
    db = await get_db()
    await db.execute("""
        INSERT INTO progress (user_id, lesson_id, lesson_sent)
        VALUES (?, ?, TRUE)
        ON CONFLICT(user_id, lesson_id) DO UPDATE SET lesson_sent = TRUE
    """, (user_id, lesson_id))
    await db.commit()
    await db.close()


async def is_lesson_sent(user_id: int, lesson_id: int) -> bool:
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT lesson_sent FROM progress WHERE user_id=? AND lesson_id=?",
        (user_id, lesson_id)
    )
    await db.close()
    return bool(row and row[0]["lesson_sent"])
