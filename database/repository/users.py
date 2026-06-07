from database.db import get_db

async def get_user(telegram_id: int):
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    )
    await db.close()
    return row[0] if row else None

async def create_user(telegram_id: int, name: str, language: str, notify_time: str):
    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO users (telegram_id, name, language, notify_time) VALUES (?,?,?,?)",
        (telegram_id, name, language, notify_time)
    )
    # Init statistics row
    user = await db.execute_fetchall(
        "SELECT id FROM users WHERE telegram_id=?", (telegram_id,)
    )
    if user:
        await db.execute(
            "INSERT OR IGNORE INTO statistics (user_id) VALUES (?)", (user[0]["id"],)
        )
        await db.execute(
            "INSERT OR IGNORE INTO reminders (user_id, morning_time) VALUES (?,?)",
            (user[0]["id"], notify_time)
        )
    await db.commit()
    await db.close()

async def update_language(telegram_id: int, language: str):
    db = await get_db()
    await db.execute("UPDATE users SET language=? WHERE telegram_id=?", (language, telegram_id))
    await db.commit()
    await db.close()

async def advance_lesson(telegram_id: int):
    db = await get_db()
    await db.execute(
        "UPDATE users SET current_lesson = current_lesson + 1 WHERE telegram_id=?",
        (telegram_id,)
    )
    await db.commit()
    await db.close()

async def get_users_by_notify_time(notify_time: str):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT * FROM users WHERE notify_time=?", (notify_time,)
    )
    await db.close()
    return rows
