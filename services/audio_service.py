import os, edge_tts
from config import AUDIO_DIR

async def get_or_generate_audio(text: str, lesson_id: int) -> str:
    """Returns path to MP3. Generates only if not cached."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    path = os.path.join(AUDIO_DIR, f"lesson_{lesson_id:03d}.mp3")
    if not os.path.exists(path):
        communicate = edge_tts.Communicate(
            text=text,
            voice="en-US-JennyNeural"  # Natural female voice, free
        )
        await communicate.save(path)
    return path
