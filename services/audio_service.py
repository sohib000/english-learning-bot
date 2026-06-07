import os
from config import AUDIO_DIR

async def get_or_generate_audio(text: str, lesson_id: int) -> str | None:
    """Returns path to MP3 or None if generation failed."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    path = os.path.join(AUDIO_DIR, f"lesson_{lesson_id:03d}.mp3")

    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path  # кэш

    # Используем gTTS — работает везде включая Railway
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(path)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    except Exception as e:
        print(f"gTTS error: {e}")

    return None
