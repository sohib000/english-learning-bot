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
        return "Статистика пока пуста. Пройди первый урок!"
    level = get_level_label(s["lessons_completed"])
    return (
        f"📊 *Твоя статистика*\n\n"
        f"🔥 Серия дней: *{s['current_streak']}*\n"
        f"📚 Слов изучено: *{s['words_learned']} / 1000*\n"
        f"📝 Уроков пройдено: *{s['lessons_completed']}*\n"
        f"🎯 Средний балл: *{s['average_score']:.0f}%*\n"
        f"🏅 Уровень: *{level}*"
    )
