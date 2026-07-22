import os
import asyncio
from config import AUDIO_DIR

async def get_or_generate_audio(text: str, lesson_id: int) -> str | None:
    """Returns path to MP3 or None if generation failed."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    path = os.path.join(AUDIO_DIR, f"lesson_{lesson_id:03d}.mp3")

    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path

    try:
        from gtts import gTTS
        # asyncio.to_thread — не блокируем event loop
        def generate():
            tts = gTTS(text=text, lang="en", slow=False)
            tts.save(path)
        await asyncio.to_thread(generate)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    except Exception as e:
        print(f"gTTS error: {e}")

    return None

async def get_cached_file_id(lesson_id: int) -> str | None:
    """Возвращает Telegram file_id если аудио уже отправлялось."""
    from database.db import get_db
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT file_id FROM audio_cache WHERE lesson_id=?", (lesson_id,)
    )
    await db.close()
    return rows[0]["file_id"] if rows else None

async def save_file_id(lesson_id: int, file_id: str):
    """Сохраняет Telegram file_id для переиспользования."""
    from database.db import get_db
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO audio_cache (lesson_id, file_id) VALUES (?,?)",
        (lesson_id, file_id)
    )
    await db.commit()
    await db.close()
