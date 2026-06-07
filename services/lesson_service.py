from database.repository.lessons import load_lesson
from services.audio_service import get_or_generate_audio

async def get_lesson_message(level: int, lesson_number: int, language: str) -> dict:
    lesson = load_lesson(level, lesson_number)
    if not lesson:
        return None

    lang_key = "text_uz" if language == "uz" else "text_ru"
    translation = lesson.get(lang_key, "")

    words_lines = []
    for w in lesson["words"]:
        tr = w.get("uz" if language == "uz" else "ru", "")
        words_lines.append(f"• <b>{w['en']}</b> — {tr}")

    title_label = "Dars" if language == "uz" else "Урок"
    words_label = "Yangi so'zlar" if language == "uz" else "Новые слова"
    translate_label = "Tarjima" if language == "uz" else "Перевод"

    text = (
        f"📖 <b>{title_label} #{lesson_number}</b> — {lesson['title']}\n\n"
        f"<b>English:</b>\n{lesson['text_en']}\n\n"
        f"<b>{translate_label}:</b>\n{translation}\n\n"
        f"<b>{words_label}:</b>\n" + "\n".join(words_lines)
    )

    audio_path = await get_or_generate_audio(lesson["text_en"], lesson["id"])

    return {
        "text": text,
        "audio_path": audio_path,
        "lesson": lesson,
    }