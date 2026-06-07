from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_db

router = Router()

LEVELS = [
    (0,  "Beginner",           "🌱"),
    (5,  "Elementary",         "📗"),
    (15, "Pre-Intermediate",   "📘"),
    (30, "Intermediate",       "📙"),
    (50, "Upper-Intermediate", "🏆"),
]

def get_level(lessons_done: int):
    result = LEVELS[0]
    for item in LEVELS:
        if lessons_done >= item[0]:
            result = item
    return result

def progress_bar(current: int, total: int, length: int = 8) -> str:
    filled = int(length * current / total) if total > 0 else 0
    filled = min(filled, length)
    return "[" + "=" * filled + "-" * (length - filled) + "]"

async def build_stats(db_user: dict) -> dict:
    db = await get_db()
    stats = await db.execute_fetchall(
        "SELECT * FROM statistics WHERE user_id=?", (db_user["id"],)
    )
    # Берём последние уроки с номером из users.current_lesson
    recent = await db.execute_fetchall(
        """SELECT p.score, p.completed_at, p.lesson_id
           FROM progress p
           WHERE p.user_id=? AND p.completed=TRUE
           ORDER BY p.completed_at DESC LIMIT 5""",
        (db_user["id"],)
    )
    await db.close()

    s = stats[0] if stats else None
    return {
        "words":   s["words_learned"]     if s else 0,
        "lessons": s["lessons_completed"] if s else 0,
        "streak":  s["current_streak"]    if s else 0,
        "avg":     s["average_score"]     if s else 0.0,
        "recent":  recent,
    }

def format_stats(data: dict, lang: str) -> str:
    _, level_name, level_emoji = get_level(data["lessons"])
    bar_words   = progress_bar(data["words"],   1000)
    bar_lessons = progress_bar(data["lessons"], 100)

    if lang == "uz":
        if data["streak"] >= 7:
            streak_msg = "Haftalik seria! Ajoyib!"
        elif data["streak"] >= 3:
            streak_msg = "Yaxshi ketmoqda!"
        elif data["streak"] == 0:
            streak_msg = "Bugun birinchi darsni oching!"
        else:
            streak_msg = "Davom eting!"

        recent_text = ""
        if data["recent"]:
            recent_text = "\nSo'nggi darslar:\n"
            for i, r in enumerate(data["recent"], 1):
                score = r["score"]
                icon = "+" if score >= 70 else "~"
                recent_text += f"  {icon} Dars {i}: {score}%\n"

        return (
            f"{level_emoji} <b>Mening statistikam</b>\n\n"
            f"  Daraja: <b>{level_name}</b>\n\n"
            f"  Kunlik seria: <b>{data['streak']} kun</b>\n"
            f"  {streak_msg}\n\n"
            f"  So'zlar: <b>{data['words']} / 1000</b>\n"
            f"  {bar_words}\n\n"
            f"  Darslar: <b>{data['lessons']} / 100</b>\n"
            f"  {bar_lessons}\n\n"
            f"  O'rtacha ball: <b>{data['avg']:.0f}%</b>"
            f"{recent_text}"
        )
    else:
        if data["streak"] >= 7:
            streak_msg = "Недельная серия! Невероятно!"
        elif data["streak"] >= 3:
            streak_msg = "Хорошая динамика!"
        elif data["streak"] == 0:
            streak_msg = "Открой первый урок сегодня!"
        else:
            streak_msg = "Продолжай в том же духе!"

        recent_text = ""
        if data["recent"]:
            recent_text = "\nПоследние уроки:\n"
            for i, r in enumerate(data["recent"], 1):
                score = r["score"]
                icon = "+" if score >= 70 else "~"
                recent_text += f"  {icon} Урок {i}: {score}%\n"

        return (
            f"{level_emoji} <b>Моя статистика</b>\n\n"
            f"  Уровень: <b>{level_name}</b>\n\n"
            f"  Серия дней: <b>{data['streak']} дн.</b>\n"
            f"  {streak_msg}\n\n"
            f"  Слова: <b>{data['words']} / 1000</b>\n"
            f"  {bar_words}\n\n"
            f"  Уроки: <b>{data['lessons']} / 100</b>\n"
            f"  {bar_lessons}\n\n"
            f"  Средний балл: <b>{data['avg']:.0f}%</b>"
            f"{recent_text}"
        )

def stats_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔄 Yangilash" if lang == "uz" else "🔄 Обновить",
            callback_data="stats:refresh"
        )
    ]])

@router.message(F.text.in_(["📊 Статистика", "📊 Statistika"]))
async def show_stats(message: Message, db_user: dict):
    if not db_user:
        await message.answer("Сначала нажми /start")
        return
    lang = db_user["language"]
    data = await build_stats(db_user)
    text = format_stats(data, lang)
    await message.answer(text, parse_mode="HTML", reply_markup=stats_keyboard(lang))

@router.callback_query(F.data == "stats:refresh")
async def refresh_stats(call: CallbackQuery, db_user: dict):
    lang = db_user["language"]
    data = await build_stats(db_user)
    text = format_stats(data, lang)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=stats_keyboard(lang))
    except Exception:
        pass
    await call.answer("Yangilandi!" if lang == "uz" else "Обновлено!")