from database.repository.statistics import get_stats

LEVELS = {
    0:  ("🌱", "Beginner"),
    3:  ("📗", "Elementary"),
    10: ("📘", "Pre-Intermediate"),
    20: ("📙", "Intermediate"),
    40: ("🏆", "Upper-Intermediate"),
}


def get_level_label(lessons_done: int) -> str:
    label = ("🌱", "Beginner")
    for threshold, lbl in sorted(LEVELS.items()):
        if lessons_done >= threshold:
            label = lbl
    return f"{label[0]} {label[1]}"


async def format_stats_message(user_id: int, language: str) -> str:
    s = await get_stats(user_id)
    if not s:
        if language == "uz":
            return "Statistika hozircha bo'sh. Birinchi darsni o'ting!"
        return "Статистика пока пуста. Пройди первый урок!"
    level = get_level_label(s["lessons_completed"])

    # ФИКС: было *Markdown*, а отправляется с parse_mode="HTML" —
    # звёздочки показывались как текст. Теперь честный HTML + перевод для uz.
    if language == "uz":
        return (
            f"📊 <b>Mening statistikam</b>\n\n"
            f"🔥 Kunlik seria: <b>{s['current_streak']}</b>\n"
            f"📚 O'rganilgan so'zlar: <b>{s['words_learned']} / 1000</b>\n"
            f"📝 O'tilgan darslar: <b>{s['lessons_completed']}</b>\n"
            f"🎯 O'rtacha ball: <b>{s['average_score']:.0f}%</b>\n"
            f"🏅 Daraja: <b>{level}</b>"
        )
    return (
        f"📊 <b>Твоя статистика</b>\n\n"
        f"🔥 Серия дней: <b>{s['current_streak']}</b>\n"
        f"📚 Слов изучено: <b>{s['words_learned']} / 1000</b>\n"
        f"📝 Уроков пройдено: <b>{s['lessons_completed']}</b>\n"
        f"🎯 Средний балл: <b>{s['average_score']:.0f}%</b>\n"
        f"🏅 Уровень: <b>{level}</b>"
    )
