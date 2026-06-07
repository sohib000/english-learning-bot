from database.db import get_db

async def save_progress(user_id: int, lesson_id: int, score: int):
    db = await get_db()
    await db.execute("""
        INSERT INTO progress (user_id, lesson_id, score, completed, completed_at)
        VALUES (?, ?, ?, TRUE, CURRENT_TIMESTAMP)
        ON CONFLICT DO NOTHING
    """, (user_id, lesson_id, score))
    await db.commit()
    await db.close()

async def mark_lesson_sent(user_id: int, lesson_id: int):
    db = await get_db()
    await db.execute("""
        INSERT OR IGNORE INTO progress (user_id, lesson_id, lesson_sent)
        VALUES (?, ?, TRUE)
    """, (user_id, lesson_id))
    await db.execute(
        "UPDATE progress SET lesson_sent=TRUE WHERE user_id=? AND lesson_id=?",
        (user_id, lesson_id)
    )
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
