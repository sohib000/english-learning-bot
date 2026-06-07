from database.db import get_db
from datetime import datetime, date

async def get_stats(user_id: int):
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT * FROM statistics WHERE user_id=?", (user_id,)
    )
    await db.close()
    return row[0] if row else None

async def update_after_test(user_id: int, score: int):
    db = await get_db()

    stats = await db.execute_fetchall(
        "SELECT lessons_completed, average_score, current_streak, last_activity FROM statistics WHERE user_id=?",
        (user_id,)
    )

    if stats:
        s = stats[0]
        n = s["lessons_completed"]
        new_avg = (s["average_score"] * n + score) / (n + 1)

        # Серия считается по дням — не по урокам
        today = date.today().isoformat()
        last  = str(s["last_activity"] or "")[:10]  # берём только дату

        if last == today:
            # Уже занимался сегодня — серию не трогаем
            new_streak = s["current_streak"]
        elif last == str(date.fromordinal(date.today().toordinal() - 1)):
            # Вчера занимался — продолжаем серию
            new_streak = s["current_streak"] + 1
        else:
            # Пропустил день — серия сбрасывается
            new_streak = 1

        await db.execute("""
            UPDATE statistics
            SET lessons_completed = lessons_completed + 1,
                words_learned     = words_learned + 10,
                average_score     = ?,
                current_streak    = ?,
                last_activity     = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (new_avg, new_streak, user_id))
    else:
        # Первый урок
        await db.execute("""
            INSERT INTO statistics (user_id, lessons_completed, words_learned, average_score, current_streak, last_activity)
            VALUES (?, 1, 10, ?, 1, CURRENT_TIMESTAMP)
        """, (user_id, score))

    await db.commit()
    await db.close()